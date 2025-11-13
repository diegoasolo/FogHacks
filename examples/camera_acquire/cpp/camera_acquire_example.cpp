#include <ajile/aj_constants.h>
#include <ajile/camera_constants.h>
#include <ajile/AJObjects.h>
#include <ajile/HostSystem.h>
#include <ajile/ControllerDriver.h>

#include <vector>

#include "example_helper.h"

// creates an Ajile project and returns it
aj::Project CreateProject(unsigned short sequenceID=1, float frameTime_ms=-1,
                          unsigned int bitDepth=CMV4000_BIT_DEPTH, unsigned int roiFirstRow=0, unsigned int roiNumRows=CMV4000_IMAGE_HEIGHT_MAX, unsigned int subsampleRowSkip=0,
                          std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "camera_acquire_example";
    if (frameTime_ms < 0)
        frameTime_ms = 10;
    int numImages = 100;
    int firstImageID = 1;
    int sequenceRepeatCount = 1;
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0) {
        project.SetComponents(components);
    } else {
        // create default components if none are passed in
        Component controllerComponent;
        controllerComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::DMD_CAMERA_CONTROLLER_DEVICE_TYPE));
        Component cameraComponent;
        cameraComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::CMV_4000_MONO_DEVICE_TYPE));
        project.AddComponent(controllerComponent);
        project.AddComponent(Component()); // the camera component is at index 2, so add an empty component
        project.AddComponent(cameraComponent);
    }

    int cameraIndex = project.GetComponentIndexWithDeviceType(aj::CMV_4000_MONO_DEVICE_TYPE);
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
    project.AddSequence(aj::Sequence(sequenceID, projectName, deviceType, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

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

    return project;
}

int RunCameraAcquireExample(int argc, char *argv[]) {

    // read the input command line arguments
    Parameters parameters;
    ParseCommandArguments(parameters, argc, argv);

    // connect to the device
    aj::HostSystem ajileSystem;
    ConnectToDevice(ajileSystem, parameters);

    // create the project
    aj::Project project = CreateProject(parameters.sequenceID, parameters.frameTime_ms,
                                        parameters.bitDepth, parameters.roiFirstRow, parameters.roiNumRows, parameters.subsampleRowSkip,
                                        ajileSystem.GetProject()->Components());
    
    // get the first valid component index which will run the sequence
    bool wasFound = false;
    const aj::Sequence& sequence = project.FindSequence(parameters.sequenceID, wasFound);
    if (!wasFound) exit(-1);
    int cameraIndex = ajileSystem.GetProject()->GetComponentIndexWithDeviceType(sequence.HardwareType());

    // stop any existing project from running on the device
    ajileSystem.GetDriver()->StopSequence(cameraIndex);

    // load the project to the device
    ajileSystem.GetDriver()->LoadProject(project);
    ajileSystem.GetDriver()->WaitForLoadComplete(-1);

    // acquire all images from the camera, which means numImages will automatically be sent to the host when they are captured
    int numImages = project.Images().size();
    ajileSystem.GetDriver()->AcquireImages(numImages, cameraIndex);
    
    // start the sequence and wait for it to start
    ajileSystem.GetDriver()->StartSequence(sequence.ID(), cameraIndex);
    printf("Waiting for sequence %d to start\n", sequence.ID());
    while (ajileSystem.GetDeviceState(cameraIndex)->RunState() != aj::RUN_STATE_RUNNING) ;    

    printf ("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(cameraIndex)->RunState() == aj::RUN_STATE_RUNNING) ;

    // get the acquired images from the acquired image (FIFO) queue, and save them to file
    int imagesRead = 0;
    while (imagesRead < numImages) {
        if (!ajileSystem.GetDriver()->IsAcquiredImageQueueEmpty(cameraIndex)) {
            const aj::Image& ajileImage = ajileSystem.GetDriver()->GetNextAcquiredImage(cameraIndex);
            printf("Read image %d with ID %d\n", imagesRead, ajileImage.ID());
            if (ajileImage.Size() == ajileImage.Width() * ajileImage.Height() * ajileImage.BitDepth() / 8) {
                int outputBitDepth = ajileImage.BitDepth();
                if (ajileImage.BitDepth() > 8)
                    outputBitDepth = 16; // saving 10-bit images as 16-bit files
                char filename[32];
                sprintf(filename, "image_%d.png", imagesRead);
                ajileImage.WriteToFile(filename, outputBitDepth);
            } else {
                printf("Timeout waiting for camera image.\n");
            }
            ajileSystem.GetDriver()->PopNextAcquiredImage(cameraIndex);
            imagesRead += 1;
        }
    }
}


int main(int argc, char **argv) {

    return RunCameraAcquireExample(argc, argv);

}
