#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>

#include <vector>
#include <opencv2/opencv.hpp>

#include "example_helper.h"

// helper function which creates a set of binary gray code pattern images
std::vector<cv::Mat> GenerateCheckerboards(int width, int height) {

    // width and height of each checkerboard square
    int squareWidth = 50;
    int squareHeight = 100;

    // Allocate Gray codes.
    std::vector<cv::Mat> boardImages;
    for (int i=0; i<2; i++)
        boardImages.push_back(cv::Mat::zeros(height, width, CV_8UC1));    
    
    // draw the checkerboard pattern
    u8 value = 0;
    u8 firstValue = 0;
    for (int i=0; i<width; i+=squareWidth) {
        value = firstValue;
        for (int j=0; j<height; j+= squareHeight) {
            cv::rectangle(boardImages[0], cv::Point(i, j), cv::Point(i+squareWidth, j+squareHeight), value, -1);
            value = value == 0 ? 255 : 0;
        }
        firstValue = firstValue == 0 ? 255 : 0;
    }

    // the second board is the inverse of the first
    boardImages[1] = 255 - boardImages[0];

    return boardImages;
}

// creates an Ajile project and returns in
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_binary_triggerout_example";
    if (frameTime_ms < 0)
        frameTime_ms = 100;
    
    // create a new project
    aj::Project project(projectName);

    // set the components for the project if they were provided, or create default ones if not
    if (components.size() > 0)
        project.SetComponents(components);
    else {
        // these defaults are for a DMD_4500 device on a standalone board. 
        // Either pass in the proper components or modify if they are different from your setup.
        aj::Component controllerComponent;
        controllerComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::AJILE_CONTROLLER_DEVICE_TYPE));
        project.AddComponent(controllerComponent);
        aj::Component dmdComponent;
        dmdComponent.CreateComponentForDevice(aj::DeviceDescriptor(aj::DMD_4500_DEVICE_TYPE));
        project.AddComponent(dmdComponent);
    }

    // get the component indices
    int controllerIndex = 0;
    for (int index=0; index<project.Components().size(); index++) {
        DeviceType_e deviceType = project.Components()[index].DeviceType().HardwareType();
        if (deviceType == aj::AJILE_CONTROLLER_DEVICE_TYPE ||
            deviceType == aj::AJILE_2PORT_CONTROLLER_DEVICE_TYPE ||
            deviceType == aj::AJILE_3PORT_CONTROLLER_DEVICE_TYPE ||
            deviceType == aj::DMD_CAMERA_CONTROLLER_DEVICE_TYPE)
            controllerIndex = index;
    }
    int dmdIndex = project.GetComponentIndexWithDeviceType(aj::DMD_4500_DEVICE_TYPE);

    // configure the external output triggers of the Ajile controller component to be rising edge, with a hold time of half the frame time
    // (Note that the default trigger hold time is defined by TRIGGER_DEFAULT_HOLD_TIME. 
    //  This step can be skipped if the default hold time and rising edge is sufficient.)
    vector<aj::ExternalTriggerSetting> inputTriggerSettings = project.Components()[controllerIndex].InputTriggerSettings();
    vector<aj::ExternalTriggerSetting> outputTriggerSettings = project.Components()[controllerIndex].OutputTriggerSettings();
    for (int index=0; index<outputTriggerSettings.size(); index++)        
        outputTriggerSettings[index] = aj::ExternalTriggerSetting(aj::RISING_EDGE, aj::FromMSec(frameTime_ms/2));
    project.SetTriggerSettings(controllerIndex, inputTriggerSettings, outputTriggerSettings);

    // create a trigger rule to connect the DMD frame started to the external output trigger 0
    aj::TriggerRule dmdFrameStartedToExtTrigOut;
    dmdFrameStartedToExtTrigOut.AddTriggerFromDevice(aj::TriggerRulePair(dmdIndex, aj::FRAME_STARTED));
    dmdFrameStartedToExtTrigOut.SetTriggerToDevice(aj::TriggerRulePair(controllerIndex, aj::EXT_TRIGGER_OUTPUT_1));
    // add the trigger rule to the project
    project.AddTriggerRule(dmdFrameStartedToExtTrigOut);

    // generate a list of gray code images (which are opencv matrices)
    std::vector<cv::Mat> boardImages = GenerateCheckerboards(DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
    
    // create the images from the numpy gray code images and add them to our project
    int imageCount = 1;
    for (int i=0; i<boardImages.size(); i++) {
        aj::Image image(imageCount);
        imageCount += 1;
        image.ReadFromMemory((unsigned char*)boardImages[i].data, boardImages[i].rows, boardImages[i].cols, 1, 8, aj::ROW_MAJOR_ORDER, aj::DMD_4500_DEVICE_TYPE);
        project.AddImage(image);
    }

    int numImages = boardImages.size();
    
    // create the sequence
    project.AddSequence(aj::Sequence(sequenceID, projectName, aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

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

    return project;
}


int main(int argc, char **argv) {

    return RunExample(&CreateProject, argc, argv);

}
