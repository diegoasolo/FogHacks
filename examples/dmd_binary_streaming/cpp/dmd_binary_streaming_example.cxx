#include <ajile/AJObjects.h>
#include <ajile/HostSystem.h>
#include <ajile/ControllerDriver.h>
#include <ajile/dmd_constants.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <opencv2/opencv.hpp>

int RunStreaming(int argc, char *argv[]) {

    // default connection settings
    char ipAddress[32] = "192.168.200.1";
    char netmask[32] = "255.255.255.0";
    char gateway[32] = "0.0.0.0";
    unsigned short port = 5005;
    CommunicationInterfaceType_e commInterface = aj::USB2_INTERFACE_TYPE;

    // default sequence settings
    unsigned int repeatCount = 0; // repeat forever
    float frameTime_ms = 10.0; // frame time in milliseconds
    unsigned short sequenceID = 1;

    // read command line arguments
    for (int i=1; i<argc; i++) {
        if (strcmp(argv[i], "-i") == 0) {
            strcpy(ipAddress, argv[++i]);
        } else if (strcmp(argv[i], "-f") == 0) {
            frameTime_ms = atof(argv[++i]);
        }  else if (strcmp(argv[i], "--usb3") == 0) {
            commInterface = aj::USB3_INTERFACE_TYPE;
        } else if (strcmp(argv[i], "-r") == 0) {
            repeatCount = atoi(argv[++i]); 
        } else if (strcmp(argv[i], "--pcie") == 0) {
            commInterface = aj::PCIE_INTERFACE_TYPE;
        } else if (strcmp(argv[i], "--eth") == 0) {
            commInterface = aj::GIGE_INTERFACE_TYPE;
        } else {
            printf("Usage: %s [-i <IP address>] [-f <frame rate in ms>] [--usb|--eth|--pcie]\n", argv[0]);
            exit(2);
        }
    }

    // connect to the device
    aj::HostSystem ajileSystem;
    aj::ControllerDriver& driver = *ajileSystem.GetDriver();
    ajileSystem.SetConnectionSettingsStr(ipAddress, netmask, gateway, port);
    ajileSystem.SetCommunicationInterface(commInterface);
    if (ajileSystem.StartSystem() != aj::ERROR_NONE) {
        printf("Error starting AjileSystem.\n");
        exit(-1);
    }

    // create the project
    aj::Project project("dmd_binary_streaming_example");
    // get the connected devices from the project structure
    project.SetComponents(ajileSystem.GetProject()->Components());

    int dmdIndex = ajileSystem.GetProject()->GetComponentIndexWithDeviceType(aj::DMD_4500_DEVICE_TYPE);
    
    // stop any existing project from running on the device
    driver.StopSequence(dmdIndex);

    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(dmdIndex)->RunState() != aj::RUN_STATE_STOPPED) ;

    // create the streaming sequence
    project.AddSequence(aj::Sequence(sequenceID, "dmd_binary_streaming_example", aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_STREAM, 1, deque<SequenceItem>(), aj::RUN_STATE_PAUSED));

    // load the project
    driver.LoadProject(project);
    driver.WaitForLoadComplete(-1);

    // local variables used to generate DMD images
    const u32 dmdImageSize = DMD_IMAGE_WIDTH_MAX * DMD_IMAGE_HEIGHT_MAX / 8;
    const u32 maxStreamingSequenceItems = 100;
    u32 frameNum = 0;
    u32 framesProcessed = 0;
    char frameStr[80];
    u32 rectHeight = 100;
    u32 rectWidth = 1;
    cv::Mat cvImage = cv::Mat::zeros(DMD_IMAGE_HEIGHT_MAX, DMD_IMAGE_WIDTH_MAX, CV_8U);

    char keyPress = 0;
    while ((keyPress != 'q' && keyPress != 'Q') && (repeatCount == 0 || framesProcessed < repeatCount)) {
        if (!driver.IsSequenceStatusQueueEmpty(dmdIndex)) {
            SequenceStatusValues seqStatus = driver.GetNextSequenceStatus(dmdIndex);
        }
        if ( driver.GetNumStreamingSequenceItems(dmdIndex) < maxStreamingSequenceItems) {
            // generate a new image with OpenCV
            u32 myNum = frameNum;
            cvImage = cv::Mat::zeros(DMD_IMAGE_HEIGHT_MAX, DMD_IMAGE_WIDTH_MAX, CV_8U);
            sprintf(frameStr, "%04x", (myNum & 0xffff0000) >> 16);
            cv::putText(cvImage, frameStr, cv::Point(50, 450),  cv::FONT_HERSHEY_TRIPLEX, 10, 255, 10);
            sprintf(frameStr, "%04x", (myNum & 0x0000ffff));
            cv::putText(cvImage, frameStr, cv::Point(50, 700),  cv::FONT_HERSHEY_TRIPLEX, 10, 255, 10);
            sprintf(frameStr, "%08x", myNum);
            cv::putText(cvImage, frameStr, cv::Point(10, 1100),  cv::FONT_HERSHEY_TRIPLEX, 5, 255, 5);
            cv::rectangle(cvImage, cv::Point(0, 0), cv::Point(rectWidth, rectHeight), 255, -1);
            // convert the OpenCV image to the Ajile DMD image format
            aj::Image streamingImage;
            streamingImage.ReadFromMemory((u8*)cvImage.data, cvImage.rows, cvImage.cols, 1, 8, ROW_MAJOR_ORDER, DMD_4500_DEVICE_TYPE);
            // create a new sequence item and frame to be streamed
            aj::SequenceItem streamingSeqItem = aj::SequenceItem(sequenceID, 1);
            aj::Frame streamingFrame = aj::Frame( sequenceID, 0, aj::FromMSec(frameTime_ms), 0, 0, DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
            // attach the next streaming image to the streaming frame
            streamingFrame.SetStreamingImage(streamingImage);
            frameNum++;
            framesProcessed++;
            // add the frame to the streaming sequence item
            streamingSeqItem.AddFrame(streamingFrame);
            if (rectWidth == DMD_IMAGE_WIDTH_MAX - 1)
                rectWidth = 1;
            else 
                rectWidth++;
            // send the streaming sequence item to the device
            driver.AddStreamingSequenceItem(streamingSeqItem, dmdIndex);
        } else {
            // when enough images have been preloaded start the streaming sequence
            if (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_STOPPED)
                driver.StartSequence(sequenceID, dmdIndex);
            // check for a keypress to quit
            cv::imshow("AJILE Streaming DMD Example", cvImage);
            keyPress = cv::waitKey(10);
        }
    }

    // stop the device when we are done
    driver.StopSequence(dmdIndex);
    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_RUNNING) ;

    return 0;
}

int main(int argc, char **argv) {

    return RunStreaming(argc, argv);

}
