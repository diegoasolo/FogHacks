#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>
#include <ajile/camera_constants.h>

#include <vector>
#include <opencv2/opencv.hpp>

#include "example_helper.h"

// helper function which creates a set of binary gray code pattern images
std::vector<cv::Mat> GenerateGrayCodes(int width, int height) {

    // Determine number of required codes and row/column offsets.
    int numColumns = int(ceil(log2(width)));
    int columnShift = int(floor((pow(2.0,numColumns)-width)/2));

    int numRows = int(ceil(log2(height)));
    int rowShift = int(floor((pow(2.0,numRows)-height)/2));

    // Allocate Gray codes.
    std::vector<cv::Mat> grayCodeImages;
    for (int i=0; i<numColumns+numRows+1; i++)
        grayCodeImages.push_back(cv::Mat::zeros(height, width, CV_8UC1));
    
    // Define first code as a white image.
    grayCodeImages[0].setTo(255);

    // Define Gray codes for projector columns.
    for (int c=0; c<width; c++) {
        for (int i=0; i<numColumns; i++) {
            int imageIndex = i+1;
            unsigned char value = 0;
            if ( i > 0 )
                value = (((c+columnShift) >> (numColumns-i-1)) & 1) ^ (((c+columnShift) >> (numColumns-i)) & 1);
            else
                value = (((c+columnShift) >> (numColumns-i-1)) & 1);
            value *= 255;
            cv::rectangle(grayCodeImages[imageIndex], cv::Point(c,0), cv::Point(c,height), value, -1);
        }
    }
            
    // Define Gray codes for projector rows.
    for (int r=0; r<height; r++) {
        for (int i=0; i<numRows; i++) {
            int imageIndex = i+numColumns+1;
            unsigned char value = 0;
            if (i > 0) 
                value = (((r+rowShift) >> (numRows-i-1)) & 1)^(((r+rowShift) >> (numRows-i)) & 1);
            else
                value = (((r+rowShift) >> (numRows-i-1)) & 1);
            value *= 255;
            cv::rectangle(grayCodeImages[imageIndex], cv::Point(0,r), cv::Point(width,r), value, -1);
        }
    }

    return grayCodeImages;
}

// creates the DMD sequence
void CreateDmdSequence(aj::Project& project, unsigned short sequenceID, unsigned int sequenceRepeatCount, float frameTime_ms) {

    // generate a list of gray code images (which are opencv matrices)
    std::vector<cv::Mat> grayCodeImages = GenerateGrayCodes(DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
    
    // create the images from the numpy gray code images and add them to our project
    int imageCount = 1;
    for (int i=0; i<grayCodeImages.size(); i++) {
        aj::Image image(imageCount);
        imageCount += 1;
        image.ReadFromMemory((unsigned char*)grayCodeImages[i].data, grayCodeImages[i].rows, grayCodeImages[i].cols, 1, 8, aj::ROW_MAJOR_ORDER, aj::DMD_4500_DEVICE_TYPE);
        project.AddImage(image);
    }

    int numImages = grayCodeImages.size();
    
    // create the sequence
    project.AddSequence(aj::Sequence(sequenceID, project.Name().c_str(), aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create a single sequence item, which all the frames will be added to
    project.AddSequenceItem(aj::SequenceItem(sequenceID, 1));

    // create the frames and add them to the project, which adds them to the last sequence item
    for (int i=0; i<numImages; i++) {
        aj::Frame frame;
        frame.SetSequenceID(sequenceID);
        frame.SetImageID(i+1);
        frame.SetFrameTimeMSec(frameTime_ms);
        project.AddFrame(frame);
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

    const char* projectName = "camera_dmd_binary_example";
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
    cameraFrameStartedToDmdFrameBegin.SetTriggerToDevice(aj::TriggerRulePair(dmdIndex, aj::START_FRAME));
    // add the trigger rule to the project
    project.AddTriggerRule(cameraFrameStartedToDmdFrameBegin);
        
    // create the DMD sequence
    CreateDmdSequence(project, sequenceID, sequenceRepeatCount, frameTime_ms);

    // get the number of images and the starting image ID for the camera based on the DMD images
    numImages = project.Images().size();
    firstImageID = numImages + 2;

    // create the camera sequence
    CreateCameraSequence(project, firstImageID, numImages, sequenceID+1, sequenceRepeatCount, frameTime_ms, bitDepth, roiFirstRow, roiNumRows, subsampleRowSkip);
        
    return project;
}

int main(int argc, char **argv) {

    return RunCameraDmdExample(&CreateProject, argc, argv);

}
