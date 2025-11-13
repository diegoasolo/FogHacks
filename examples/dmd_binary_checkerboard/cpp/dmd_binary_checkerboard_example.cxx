#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>

#include <vector>
#include <opencv2/opencv.hpp>

#include "example_helper.h"

// helper function which creates a checkerboard pattern and its inverse
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

    const char* projectName = "dmd_binary_checkerboard_example";
    if (frameTime_ms < 0)
        frameTime_ms = 100;
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0)
        project.SetComponents(components);

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

    int ret = RunExample(&CreateProject, argc, argv);

    return ret;
}
