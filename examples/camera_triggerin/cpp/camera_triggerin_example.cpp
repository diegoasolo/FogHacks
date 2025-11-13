#include <ajile/aj_constants.h>
#include <ajile/camera_constants.h>
#include <ajile/AJObjects.h>

#include <vector>

#include "example_helper.h"

// creates an Ajile project and returns it
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1,
                          unsigned int bitDepth=CMV4000_BIT_DEPTH, unsigned int roiFirstRow=0, unsigned int roiNumRows=CMV4000_IMAGE_HEIGHT_MAX, unsigned int subsampleRowSkip=0,
                          std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "camera_triggerin_example";
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
        Component cameraComponent;
        cameraComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::CMV_4000_MONO_DEVICE_TYPE));
        project.AddComponent(controllerComponent);
        project.AddComponent(Component()); // the camera component is at index 2, so add an empty component
        project.AddComponent(cameraComponent);
    }
    
    // get the component indices
    int controllerIndex = 0, cameraIndex = 0;
    for (int index=0; index<project.Components().size(); index++) {
        DeviceType_e deviceType = project.Components()[index].DeviceType().HardwareType();
        if (deviceType == aj::AJILE_CONTROLLER_DEVICE_TYPE ||
            deviceType == aj::AJILE_2PORT_CONTROLLER_DEVICE_TYPE ||
            deviceType == aj::AJILE_3PORT_CONTROLLER_DEVICE_TYPE ||
            deviceType == aj::DMD_CAMERA_CONTROLLER_DEVICE_TYPE)
            controllerIndex = index;
        if (deviceType == aj::CMV_4000_MONO_DEVICE_TYPE ||
            deviceType == aj::CMV_2000_MONO_DEVICE_TYPE)
            cameraIndex = index;
    }

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

    // configure the external input triggers of the Ajile controller component to be rising edge
    // (Note that the default is rising edge. This step can therefore be skipped but is here for demonstration purposes only).
    vector<aj::ExternalTriggerSetting> inputTriggerSettings = project.Components()[controllerIndex].InputTriggerSettings();
    vector<aj::ExternalTriggerSetting> outputTriggerSettings = project.Components()[controllerIndex].OutputTriggerSettings();
    for (int index=0; index<inputTriggerSettings.size(); index++)
        inputTriggerSettings[index] = aj::ExternalTriggerSetting(aj::RISING_EDGE);
    project.SetTriggerSettings(controllerIndex, inputTriggerSettings, outputTriggerSettings);

    // create a trigger rule to connect external input trigger 1 to camera start frame
    aj::TriggerRule extTrigInToCameraStartFrame;
    extTrigInToCameraStartFrame.AddTriggerFromDevice(aj::TriggerRulePair(controllerIndex, aj::EXT_TRIGGER_INPUT_1));
    extTrigInToCameraStartFrame.SetTriggerToDevice(aj::TriggerRulePair(cameraIndex, aj::START_FRAME));
    // add the trigger rule to the project
    project.AddTriggerRule(extTrigInToCameraStartFrame);
    
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
        // For this example we only enable the trigger setting for the first frame which has the
        // effect of triggering the entire sequence of images when a single trigger input signal
        // is detected. Comment out the following lines to go to the default behavior of
        // input triggers on each frame, so an input trigger signal must be detected to capture each frame.
        if (i == 0)
            frame.AddControlInputSetting(aj::FrameTriggerSetting(aj::START_FRAME, true));
        else
            frame.AddControlInputSetting(aj::FrameTriggerSetting(aj::START_FRAME, false));
        project.AddFrame(frame);
    }

    return project;
}


int main(int argc, char **argv) {

    return RunCameraExample(&CreateProject, argc, argv);

}
