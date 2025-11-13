#include <ajile/AJObjects.h>
#include <vector>

#include "example_helper.h"

// creates an Ajile project and returns in
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_color_testimages_example";
    const int numImages = 2;
    const char* filenames[2] = {"../../images/dog.jpg", "../../images/plants.jpg"};
    if (frameTime_ms < 0)
        frameTime_ms = 1000;
    // refresh rate set to 10 ms (100 Hz) to avoid visible flicker
    u32 refreshRate = aj::FromMSec(10);

    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0)
        project.SetComponents(components);

    // create the sequence
    project.AddSequence(aj::Sequence(sequenceID, projectName, aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create the images
    u16 nextImageID = 1;
    for (int i=0; i<numImages; i++) {

        // create a sequence item to display the 24 bitplanes of the color image with the default minimum timing
        SequenceItem sequenceItem(sequenceID);
        std::vector<aj::Image> imageBitplanes;
        project.CreateColorSequenceItemWithTime_FromFile(sequenceItem, imageBitplanes, filenames[i], nextImageID, refreshRate);
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
