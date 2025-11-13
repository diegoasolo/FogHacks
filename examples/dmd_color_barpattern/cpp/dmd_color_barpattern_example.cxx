#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>

#include "example_helper.h"

// creates an Ajile project and returns in
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_color_barpattern_example";
    const char* filenameBase = "../../images/Video_Color_Test_Pattern_";
    if (frameTime_ms < 0)
        frameTime_ms = 100;
    int numImages = 3;
    u16 maxCurrent = 6000; 
    char filename[80];
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0)
        project.SetComponents(components);

    // read the images and add them to the project
    for (int i=1; i<=numImages; i++) {
        if (i == 1)
            sprintf(filename, "%sRed_1b.bmp", filenameBase);
        else if (i == 2)
            sprintf(filename, "%sGreen_1b.bmp", filenameBase);
        else
            sprintf(filename, "%sBlue_1b.bmp", filenameBase);
        aj::Image image(i);
        image.ReadFromFile(filename, aj::DMD_4500_DEVICE_TYPE);
        project.AddImage(image);
    }
    
    // create the sequence
    project.AddSequence(aj::Sequence(sequenceID, projectName, aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create first sequence item, which the frames will be added to
    project.AddSequenceItem(aj::SequenceItem(sequenceID, 1));
    // create second sequence item, which we will add to the project after
    aj::SequenceItem colorSequenceItem(sequenceID);

    // create the frames and add them to the project, which adds them to the last sequence item    
    for (int i=0; i<numImages; i++) {
        aj::Frame frame;
        frame.SetSequenceID(sequenceID);
        frame.SetImageID(i+1);
        frame.SetFrameTimeMSec(frameTime_ms);
        // set the LED settings for this frame to turn on only one of the three LEDs
        vector<LedSetting> ledSettings;
        for (u8 ledIndex=0; ledIndex<numImages; ledIndex++) {
            if (ledIndex == i)
                ledSettings.push_back(LedSetting(maxCurrent, 100, aj::FromMSec(frameTime_ms)));
            else
                ledSettings.push_back(LedSetting(0, 0, 0));
        }
        frame.SetLedSettings(ledSettings);        
        // add the frame to the first sequence item
        project.AddFrame(frame);
        // add the frame to the color sequence item, but change the frame time to full speed
        frame.SetFrameTime(DMD_MINIMUM_FRAME_TIME);
        colorSequenceItem.AddFrame(frame);
    }

    // set the time of the color sequence item to the frame time
    colorSequenceItem.SetRepeatTimeMSec(frameTime_ms*3);
    // add the sequenece item to the project
    project.AddSequenceItem(colorSequenceItem);

    return project;
}


int main(int argc, char **argv) {

    return RunExample(&CreateProject, argc, argv);

}
