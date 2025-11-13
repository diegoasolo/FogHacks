#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>

#include <vector>

#define _USE_MATH_DEFINES
#include <math.h>

#include <opencv2/opencv.hpp>

#include "example_helper.h"

// helper function which create a set of horizontal and vertical sinusoid images with difference phases
std::vector<cv::Mat> GenerateSinusoidImages(int width, int height) {
    
    const int numPhases = 3;
    const float wavelength = 100; // wavelength (number of pixels per cycle)

    // allocate the images
    std::vector<cv::Mat> sineImages;
    for (int i=0; i<numPhases*2; i++)
        sineImages.push_back(cv::Mat::zeros(height, width, CV_8UC1));

    for (int i=0; i<numPhases; i++) {
        float phase = i * 1.0 / (float)numPhases;
        float sineValue = 0.0;
        for (int c=0; c<width; c++) {
            // compute the 1-D sine value
            sineValue = sin((float)c / wavelength * 2*M_PI + phase * 2*M_PI);
            // rescale it to be a 16-bit number
            sineValue = (sineValue + 1) * 0xff/2.0;
            // create the 2-D sine images by expanding each 1-D sine value into a rectangle across the entire image
            cv::rectangle(sineImages[i], cv::Point(c,0), cv::Point(c,height), (unsigned char)sineValue, -1);
        }
        // repeat for the horizontal images
        for (int r=0; r<height; r++) {
            sineValue = sin((float)r / wavelength * 2*M_PI + phase * 2*M_PI);
            sineValue = (sineValue + 1) * 0xff/2.0;
            cv::rectangle(sineImages[numPhases+i], cv::Point(0,r), cv::Point(width,r), (unsigned char)sineValue, -1);
        }
    }
    
    return sineImages;

}

// creates an Ajile project and returns in
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_grayscale_triggerin_example";
    if (frameTime_ms < 0)
        frameTime_ms = 1000;
    
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
            deviceType == aj::AJILE_3PORT_CONTROLLER_DEVICE_TYPE)
            controllerIndex = index;
    }
    int dmdIndex = project.GetComponentIndexWithDeviceType(aj::DMD_4500_DEVICE_TYPE);

    // configure the external input triggers of the Ajile controller component to be rising edge
    // (Note that the default is rising edge. This step can therefore be skipped but is here for demonstration purposes only).
    vector<aj::ExternalTriggerSetting> inputTriggerSettings = project.Components()[controllerIndex].InputTriggerSettings();
    vector<aj::ExternalTriggerSetting> outputTriggerSettings = project.Components()[controllerIndex].OutputTriggerSettings();
    for (int index=0; index<outputTriggerSettings.size(); index++)
        inputTriggerSettings[index] = aj::ExternalTriggerSetting(aj::RISING_EDGE);
    project.SetTriggerSettings(controllerIndex, inputTriggerSettings, outputTriggerSettings);


    // create a trigger rule to connect external trigger input 1 to DMD start frame
    aj::TriggerRule extTrigInToDMDStartFrame;
    extTrigInToDMDStartFrame.AddTriggerFromDevice(aj::TriggerRulePair(controllerIndex, aj::EXT_TRIGGER_INPUT_1));
    extTrigInToDMDStartFrame.SetTriggerToDevice(aj::TriggerRulePair(dmdIndex, aj::START_SEQUENCE_ITEM));
    // add the trigger rule to the project
    project.AddTriggerRule(extTrigInToDMDStartFrame);

    // generate a list of sinudoid images (which are opencv matrices)
    std::vector<cv::Mat> sineImages = GenerateSinusoidImages(DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
        
    // create the 8-bit image sequence
    project.AddSequence(aj::Sequence(sequenceID, "sinewave_example 8-bit", aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create the images
    int numImages = sineImages.size();
    u16 nextImageID = 1;
    for (int i=0; i<numImages; i++) {

        // convert the sinusoid image to an Ajile image. Note we convert to an 8-bit image here.
        aj::Image image;
        image.ReadFromMemory((unsigned char*)sineImages[i].data, sineImages[i].rows, sineImages[i].cols, 1, 8, aj::ROW_MAJOR_ORDER, 0, 0, 0, 8, aj::UNDEFINED_MAJOR_ORDER);
        
        // create a sequence item to display the 8 bitplanes of the sine image with the default minimum timing
        aj::SequenceItem sequenceItem(sequenceID);
        std::vector<aj::Image> imageBitplanes;
        project.CreateGrayscaleSequenceItem_FromImage(sequenceItem, imageBitplanes, image, nextImageID);
        // set the display time of this grayscale sequence item by setting its repeat time
        // (note that this must be done AFTER the frames have been added to the sequence item, since its time depends on the frame time)
        sequenceItem.SetRepeatTimeMSec(frameTime_ms);
        // add the image bitplanes to the project
        project.AddImages(imageBitplanes);
        // add the sequence item to the project
        project.AddSequenceItem(sequenceItem);
        // update the image ID for the next set of images
        nextImageID += imageBitplanes.size();
    }
    
    return project;
}


int main(int argc, char **argv) {

    return RunExample(&CreateProject, argc, argv);

}
