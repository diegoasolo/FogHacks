#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>

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

// creates an Ajile project and returns in
aj::Project CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_binary_graycode_example";
    if (frameTime_ms < 0)
        frameTime_ms = 100;
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0)
        project.SetComponents(components);

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
