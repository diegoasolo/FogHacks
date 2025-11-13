#include <ajile/AJObjects.h>

#include "example_helper.h"

// creates an Ajile project and returns in
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_binary_testimages_example";
    const char* filenameBase = "../../images/cat_";
    if (frameTime_ms < 0)
        frameTime_ms = 100;
    int numImages = 14;
    char filename[80];
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0)
        project.SetComponents(components);

    // create the images
    for (int i=1; i<=numImages; i++) {
        sprintf(filename, "%s%d.png", filenameBase, i);
        aj::Image testImage(i);
        testImage.ReadFromFile(filename, aj::DMD_4500_DEVICE_TYPE);
        project.AddImage(testImage);
    }
    
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
