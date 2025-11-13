#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>
#include <ajile/camera_constants.h>

#include <vector>
#include <opencv2/opencv.hpp>

#include "example_helper.h"

// creates the DMD sequence
void CreateDmdSequence(aj::Project& project, unsigned short sequenceID, unsigned int sequenceRepeatCount, float frameTime_ms) {

    const int numImages = 2;
    const char* filenames[2] = {"../../images/dog.jpg", "../../images/plants.jpg"};

    // create the sequence
    project.AddSequence(aj::Sequence(sequenceID, project.Name().c_str(), aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create the images and frames
    u16 nextImageID = 1;
    for (int i=0; i<numImages; i++) {

        // create a sequence item to display the 24 bitplanes of the color image with the default minimum timing
        SequenceItem sequenceItem(sequenceID, 1);
        std::vector<aj::Image> imageBitplanes;
        // we subtract the DMD inter-frame overhead time from the color display timing so that the projected image will not be slower than the camera exposure
        u32 colorDisplayTime = aj::FromMSec(frameTime_ms) - 24 * aj::FromSec(DMD_FOT_TIME_CONST);
        project.CreateColorSequenceItemWithTime_FromFile(sequenceItem, imageBitplanes, filenames[i], nextImageID, colorDisplayTime);
        // add the image bitplanes to the project
        project.AddImages(imageBitplanes);
        // add the sequence item to the project
        project.AddSequenceItem(sequenceItem);
        // update the image ID for the next set of images
        nextImageID += imageBitplanes.size();
    }
}

// creates the camera sequence
void CreateCameraSequence(Project& project, int firstImageID, int numImages, unsigned short sequenceID, unsigned int sequenceRepeatCount, float frameTime_ms,
                          unsigned int bitDepth, unsigned int roiFirstRow, unsigned int roiNumRows, unsigned int subsampleRowSkip) {

    int cameraIndex = project.GetComponentIndexWithDeviceType(aj::CMV_4000_MONO_DEVICE_TYPE);
    if (cameraIndex < 0) cameraIndex = project.GetComponentIndexWithDeviceType(aj::CMV_2000_MONO_DEVICE_TYPE);
    unsigned int imageWidth = project.Components()[cameraIndex].NumColumns();
    unsigned int imageHeight = project.Components()[cameraIndex].NumRows();
    DeviceType_e deviceType = project.Components()[cameraIndex].DeviceType().HardwareType();

    // check the bit depth parameter
    if (bitDepth != 10 && bitDepth != 8) {
        printf("Invalid bit depth selected.");
        bitDepth = CMV4000_BIT_DEPTH;
    }
    // check to make sure the region of interest arguments are acceptable
    if (roiFirstRow >= imageHeight) {
        printf("Invalid ROI start row selected.");
        roiFirstRow = 0;
    }
    if (roiFirstRow + roiNumRows > imageHeight) {
        printf("Invalid ROI number of rows selected.");
        roiNumRows = imageHeight - roiFirstRow;
    }
    // check the subsample row skip parameter
    if (subsampleRowSkip >= roiNumRows) {
        printf("Invalid subsample rows selected.");
        subsampleRowSkip = 0;
    }
    if (subsampleRowSkip > 0) {
        // total number of rows in the image is reduced by the number of rows skipped
        roiNumRows = roiNumRows / (subsampleRowSkip+1);
    }

    // create an image buffer for each of the images that we want to capture in the sequence
    for (int i=0; i<numImages; i++) {
        aj::Image image(firstImageID + i);
        image.SetImagePropertiesForDevice(deviceType);
        image.SetBitDepth(bitDepth);
        image.SetHeight(roiNumRows);
        project.AddImage(image);
    }
    
    // create the sequence
    project.AddSequence(aj::Sequence(sequenceID, project.Name().c_str(), deviceType, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create a single sequence item, which all the frames will be added to
    project.AddSequenceItem(aj::SequenceItem(sequenceID, 1));

    // create the frames and add them to the project, which adds them to the last sequence item
    for (int i=0; i<numImages; i++) {
        aj::Frame frame;
        frame.SetSequenceID(sequenceID);
        frame.SetImageID(firstImageID + i);
        frame.SetFrameTimeMSec(frameTime_ms);
        frame.SetRoiOffsetRows(roiFirstRow);
        frame.SetRoiHeightRows(roiNumRows);
        if (subsampleRowSkip > 0)
            frame.AddImagingParameter(aj::KeyValuePair(aj::IMAGING_PARAM_SUBSAMPLE_NUMROWS, subsampleRowSkip));
        project.AddFrame(frame);
    }

}

// creates an Ajile project and returns it
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1,
                          unsigned int bitDepth=CMV4000_BIT_DEPTH, unsigned int roiFirstRow=0, unsigned int roiNumRows=CMV4000_IMAGE_HEIGHT_MAX, unsigned int subsampleRowSkip=0,
                          std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "camera_dmd_color_example";
    if (frameTime_ms < 0)
        frameTime_ms = 100;
    int numImages = 10;
    int firstImageID = 1;
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0) {
        project.SetComponents(components);
    } else {
        // create default components if none are passed in
        Component controllerComponent;
        controllerComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::DMD_CAMERA_CONTROLLER_DEVICE_TYPE));
        Component dmdComponent;
        dmdComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::DMD_4500_DEVICE_TYPE));
        Component cameraComponent;
        cameraComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::CMV_4000_MONO_DEVICE_TYPE));
        project.AddComponent(controllerComponent);
        project.AddComponent(dmdComponent);
        project.AddComponent(cameraComponent);
    }

    int cameraIndex = project.GetComponentIndexWithDeviceType(aj::CMV_4000_MONO_DEVICE_TYPE);
    if (cameraIndex < 0) cameraIndex = project.GetComponentIndexWithDeviceType(aj::CMV_2000_MONO_DEVICE_TYPE);
    int dmdIndex = project.GetComponentIndexWithDeviceType(aj::DMD_4500_DEVICE_TYPE);
    if (dmdIndex < 0) dmdIndex = project.GetComponentIndexWithDeviceType(aj::DMD_3000_DEVICE_TYPE);

    // add a trigger rule between the camera and DMD
    aj::TriggerRule cameraFrameStartedToDmdFrameBegin;
    cameraFrameStartedToDmdFrameBegin.AddTriggerFromDevice(aj::TriggerRulePair(cameraIndex, aj::FRAME_STARTED));
    cameraFrameStartedToDmdFrameBegin.SetTriggerToDevice(aj::TriggerRulePair(dmdIndex, aj::START_SEQUENCE_ITEM));
    // add the trigger rule to the project
    project.AddTriggerRule(cameraFrameStartedToDmdFrameBegin);
        
    // create the DMD sequence
    CreateDmdSequence(project, sequenceID, sequenceRepeatCount, frameTime_ms);

    // get the number of images and the starting image ID for the camera based on the DMD sequence items
    // (remember each grayscale image consists of 8 1-bit images, so we much count the number of sequence items not the number of images)
    numImages = project.Sequences().at(sequenceID).SequenceItems().size();
    firstImageID = numImages * 24 + 2; // N x 24-bit color images, starting at index 1

    // create the camera sequence
    CreateCameraSequence(project, firstImageID, numImages, sequenceID+1, sequenceRepeatCount, frameTime_ms, bitDepth, roiFirstRow, roiNumRows, subsampleRowSkip);
        
    return project;
}

int main(int argc, char **argv) {

    return RunCameraDmdExample(&CreateProject, argc, argv);

}
