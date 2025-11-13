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
        sineImages.push_back(cv::Mat::zeros(height, width, CV_16UC1));

    for (int i=0; i<numPhases; i++) {
        float phase = i * 1.0 / (float)numPhases;
        float sineValue = 0.0;
        for (int c=0; c<width; c++) {
            // compute the 1-D sine value
            sineValue = sin((float)c / wavelength * 2*M_PI + phase * 2*M_PI);
            // rescale it to be a 16-bit number
            sineValue = (sineValue + 1) * 0xffff/2.0;
            // create the 2-D sine images by expanding each 1-D sine value into a rectangle across the entire image
            cv::rectangle(sineImages[i], cv::Point(c,0), cv::Point(c,height), (unsigned short)sineValue, -1);
        }
        // repeat for the horizontal images
        for (int r=0; r<height; r++) {
            sineValue = sin((float)r / wavelength * 2*M_PI + phase * 2*M_PI);
            sineValue = (sineValue + 1) * 0xffff/2.0;
            cv::rectangle(sineImages[numPhases+i], cv::Point(0,r), cv::Point(width,r), (unsigned short)sineValue, -1);            
        }
    }
    
    return sineImages;

}

// creates an Ajile project and returns in
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_grayscale_sinewave_example";
    if (frameTime_ms < 0)
        frameTime_ms = 1000;
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0)
        project.SetComponents(components);

    // generate a list of sinudoid images (which are opencv matrices)
    std::vector<cv::Mat> sineImages = GenerateSinusoidImages(DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
        
    // create the 8-bit image sequence
    project.AddSequence(aj::Sequence(sequenceID, "sinewave_example 8-bit", aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create the images and frames
    int numImages = sineImages.size();
    u16 nextImageID = 1;
    for (int i=0; i<numImages; i++) {

        // convert the sinusoid image to an Ajile image. Note we convert to an 8-bit image here.
        aj::Image image;
        image.ReadFromMemory((unsigned char*)sineImages[i].data, sineImages[i].rows, sineImages[i].cols, 1, 16, aj::ROW_MAJOR_ORDER, 0, 0, 0, 8, aj::UNDEFINED_MAJOR_ORDER);
        
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

    // create the 12-bit image sequence
    project.AddSequence(aj::Sequence(sequenceID+1, "sinewave_example 12-bit", aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create the images
    for (int i=0; i<numImages; i++) {

        // convert the sinusoid image to an Ajile image. Note we keep the image as 16-bit
        aj::Image image;
        image.ReadFromMemory((unsigned char*)sineImages[i].data, sineImages[i].rows, sineImages[i].cols, 1, 16, aj::ROW_MAJOR_ORDER, 0, 0, 0, 16, aj::UNDEFINED_MAJOR_ORDER);
        
        // split the image into its 16 bitplanes and convert into the DMD format
        std::vector<aj::Image> imageBitplanes;
        image.SplitBitplanes(imageBitplanes, aj::DMD_4500_DEVICE_TYPE);
        // drop the lower order 4 bitplanes to make the image 12-bit
        while (imageBitplanes.size() > 12)
            imageBitplanes.erase(imageBitplanes.begin());
        for (int j=0; j<imageBitplanes.size(); j++) {
            // set the image ID of the bitplanes then add it to the project
            imageBitplanes[j].SetID(nextImageID);
            nextImageID += 1;
            project.AddImage(imageBitplanes[j]);
        }

        // create a sequence item to display the 12 bitplanes of the grayscale image with the default minimum timing
        SequenceItem sequenceItem(sequenceID+1);
        project.CreateGrayscaleSequenceItem(sequenceItem, imageBitplanes);
        // set the display time of this grayscale sequence item by setting its repeat time
        sequenceItem.SetRepeatTimeMSec(frameTime_ms);
        // add the sequence item to the project
        project.AddSequenceItem(sequenceItem);

    }
    
    return project;
}


int main(int argc, char **argv) {

    return RunExample(&CreateProject, argc, argv);

}
