#include <ajile/AJObjects.h>
#include <ajile/HostSystem.h>
#include <ajile/ControllerDriver.h>
#include <ajile/dmd_constants.h>
#include <ajile/camera_constants.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <opencv2/opencv.hpp>

const int CAMERA_FIRST_IMAGE_ID = 10;
const int DMD_NUM_IMAGES = 10000;
const int DMD_REPORTING_FREQUENCY = 50; // DMD sequence status messages only every nth frame to limit message overhead


int CreateCameraSequence(aj::Project& project, float frameTime_ms, int cameraIndex, int cameraSequenceID, unsigned int roiFirstRow, unsigned int roiNumRows, unsigned int subsampleRowSkip) {

    const Component& cameraComponent = project.Components()[cameraIndex];
    const Component& controllerComponent = project.Components()[0];

    // verify the camera ROI and subsample parameters
    if (roiFirstRow + roiNumRows > cameraComponent.NumRows() || roiNumRows < 1) {
        roiNumRows = cameraComponent.NumRows() - roiFirstRow;
    }
    if (subsampleRowSkip > cameraComponent.NumRows()) {
        printf("Invalid subsample selected. Disabling.\n");
        subsampleRowSkip = 0;
    }

    int cameraImageWidth = cameraComponent.NumColumns();
    int cameraImageHeight = roiNumRows / (subsampleRowSkip+1);
    DeviceType_e cameraDeviceType = cameraComponent.DeviceType().HardwareType();
    
    // set up some image buffers
    Image imageBuffer;
    imageBuffer.SetImagePropertiesForDevice(cameraDeviceType);
    imageBuffer.SetBitDepth(8);
    imageBuffer.SetWidth(cameraImageWidth);
    imageBuffer.SetHeight(cameraImageHeight);
    imageBuffer.SetSize(0);  // size is 0 since we have not allocated the data yet - the camera will do this

    // subtracting the camera frame overhead time (~59us) from the frame time so that the exposure + the overhead time
    // is less than the DMD frame time, to ensure we don't miss DMD triggers
    const u32 cameraFrameTime = aj::FromMSec(frameTime_ms) - aj::FromSec(CMV_FOT_TIME_CONST) - aj::FromUSec(1);
    const unsigned int NUM_CAMERA_IMAGES = controllerComponent.ImageMemorySize() / (cameraImageWidth * cameraImageHeight) - 1;

    // add the images - these are the image buffers where the camera will store its data
    for (unsigned int i=CAMERA_FIRST_IMAGE_ID; i<CAMERA_FIRST_IMAGE_ID+NUM_CAMERA_IMAGES; i++) {
        imageBuffer.SetID(i);
        project.AddImage(imageBuffer);
    }

    // add the camera sequence
    project.AddSequence(Sequence(cameraSequenceID, "Image Capture Test Sequence", cameraDeviceType, SEQ_TYPE_PRELOAD, 0));

    // create a camera sequence item - all frames will be added to it
    project.AddSequenceItem(SequenceItem(cameraSequenceID, 1));
    
    // create frames - these refer to image IDs (the image buffers) and have the timing parameters and other camera properties for each frame
    for (unsigned int i=CAMERA_FIRST_IMAGE_ID; i<CAMERA_FIRST_IMAGE_ID+NUM_CAMERA_IMAGES; i++) {
        Frame cameraFrame (cameraSequenceID, i, cameraFrameTime, 0, roiFirstRow, cameraImageWidth, cameraImageHeight);
        if (subsampleRowSkip > 0)
            cameraFrame.AddImagingParameter(KeyValuePair(IMAGING_PARAM_SUBSAMPLE_NUMROWS, subsampleRowSkip));
        project.AddFrame(cameraFrame);
    }
    
}

void PrintUsage(int argc, char *argv[]) {
    printf("Usage: %s [-i <IP address>] [-f <frame rate in ms>] [--usb3|--pcie] [-t]\n\n", argv[0]);
    printf("\t-i <IP address>:\t set the ip address\n");
    printf("\t-f <frame rate in ms>:\t set the frame rate, in ms\n");
    printf("\t--usb3:\t use the USB3 interface (default is Ethernet/USB2)\n");
    printf("\t--pcie:\t use the PCIE interface\n");
    printf("\t--trig:\t enable triggering between the DMD and camera\n");
    printf("\t-r <firstRow> <numRows>:\t set the region of interest (first row and number of rows) used by the camera\n");
    printf("\t-s <rowsToSkip>:\t enable camera image subsampling, specifying the number of rows to skip between each row (e.g. 1 skips every other row so selects every 2nd row, 3 selects every 4th row, etc.)\n");
}

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
    unsigned short dmdSequenceID = 1;
    unsigned short cameraSequenceID = 2;
    bool useTriggers = false;
    unsigned int cameraRoiFirstRow = 0;
    unsigned int cameraRoiNumRows = CMV4000_IMAGE_HEIGHT_MAX;
    unsigned int subsampleRowSkip = 0;

    // read command line arguments
    for (int i=1; i<argc; i++) {
        if (strcmp(argv[i], "-i") == 0) {
            strcpy(ipAddress, argv[++i]);
        } else if (strcmp(argv[i], "-f") == 0) {
            frameTime_ms = atof(argv[++i]);
            printf("Frame rate is %f ms\n", frameTime_ms);
        } else if (strcmp(argv[i], "--usb3") == 0) {
            commInterface = aj::USB3_INTERFACE_TYPE;
            printf("Using USB3 interface\n");
        } else if (strcmp(argv[i], "--pcie") == 0) {
            commInterface = aj::PCIE_INTERFACE_TYPE;
            printf("Using PCIe interface\n");
        } else if (strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--trig") == 0) {
            useTriggers = true;
            printf("DMD to camera triggering enabled\n");
        } else if (strcmp(argv[i], "-r") == 0 || strcmp(argv[i], "--roi") == 0) {
            cameraRoiFirstRow = atoi(argv[++i]);
            cameraRoiNumRows = atoi(argv[++i]);
            printf("Camera ROI enabled, first row %d, number of rows %d\n", cameraRoiFirstRow, cameraRoiNumRows);
        } else if (strcmp(argv[i], "-s") == 0 || strcmp(argv[i], "--skip") == 0) {
            subsampleRowSkip = atoi(argv[++i]);
            printf("Camera image subsampling enabled, number of rows to skip is %d\n", subsampleRowSkip);
        } else if (strcmp(argv[i], "-h") == 0) {
            PrintUsage(argc, argv);
            exit(2);
        } else {
            PrintUsage(argc, argv);            
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

    // find the DMD device index
    int dmdIndex = project.GetComponentIndexWithDeviceType(aj::DMD_4500_DEVICE_TYPE);
    if (dmdIndex < 0) {
        printf("DMD device not found.\n");
        return -1;
    }
    // find the camera device index
    DeviceType_e cameraDeviceType = aj::CMV_4000_MONO_DEVICE_TYPE;
    int cameraIndex = project.GetComponentIndexWithDeviceType(aj::CMV_4000_MONO_DEVICE_TYPE);
    if (cameraIndex < 0) {
        cameraIndex = project.GetComponentIndexWithDeviceType(aj::CMV_2000_MONO_DEVICE_TYPE);
        cameraDeviceType = aj::CMV_2000_MONO_DEVICE_TYPE;
    }
    if (cameraIndex < 0) {
        printf("Camera device not found.\n");
        return -1;
    }

    // set the amount of memory available for preloaded images (in this case the camera images)
    Component controllerComponent = project.Components()[0];
    controllerComponent.SetImageMemorySize(0x10000000);
    project.SetComponent(0, controllerComponent);

    // set the amount memory available for DMD streaming images
    Component dmdComponent = project.Components()[dmdIndex];
    dmdComponent.SetImageMemorySize(0x10000000);
    project.SetComponent(dmdIndex, dmdComponent);

    Component cameraComponent = project.Components()[cameraIndex];
    int cameraImageW = cameraComponent.NumColumns();
    int cameraImageH = cameraRoiNumRows / (subsampleRowSkip+1);
    
    // create triggers between the camera and the DMD if enabled
    if (useTriggers) {
        TriggerRule dmdFrameStartedToCameraStartFrame;
        dmdFrameStartedToCameraStartFrame.AddTriggerFromDevice(TriggerRulePair(dmdIndex, FRAME_STARTED));
        dmdFrameStartedToCameraStartFrame.SetTriggerToDevice(TriggerRulePair(cameraIndex, START_FRAME));
        project.AddTriggerRule(dmdFrameStartedToCameraStartFrame);
    }

    // stop any existing project from running on the device
    driver.StopSequence(dmdIndex);
    driver.StopSequence(cameraIndex);

    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(dmdIndex)->RunState() != aj::RUN_STATE_STOPPED &&
           ajileSystem.GetDeviceState(cameraIndex)->RunState() != aj::RUN_STATE_STOPPED) ;
    
    // create the camera sequence
    CreateCameraSequence(project, frameTime_ms, cameraIndex, cameraSequenceID, cameraRoiFirstRow, cameraRoiNumRows, subsampleRowSkip);
    
    // create the streaming sequence
    project.AddSequence(aj::Sequence(dmdSequenceID, "dmd_binary_streaming_example", aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_STREAM, 1, deque<SequenceItem>(), aj::RUN_STATE_PAUSED));
    
    // load the project
    driver.LoadProject(project);
    driver.WaitForLoadComplete(-1);
    
    // start the camera sequence (before the DMD sequence since the DMD is triggering the camera)
    // note that the reporting frequency for the camera is 0, since we don't need camera feedback messages when running in image acquire mode
    driver.StartSequence(cameraSequenceID, cameraIndex, 0);
    // wait for feedback that the camera is running
    while (ajileSystem.GetDeviceState(cameraIndex)->RunState() != aj::RUN_STATE_RUNNING) ;

    printf("Pre-generating %d DMD images\n", DMD_NUM_IMAGES);
    
    // local variables used to generate DMD images
    const u32 dmdImageSize = DMD_IMAGE_WIDTH_MAX * DMD_IMAGE_HEIGHT_MAX / 8;
    const u32 maxStreamingSequenceItems = dmdComponent.ImageMemorySize() / dmdImageSize - 1;
    u32 frameNum = 0;
    u32 lastFrameNum = 0;
    char frameStr[80];
    char prevFrameStr[80];
    char formatStr[80];
    int tileWidth = 80;
    int numDigits = 10;
    int progressBarHeight = 1000;
    bool dmdRunning = false;
    cv::Mat cvImage = cv::Mat::zeros(DMD_IMAGE_HEIGHT_MAX, DMD_IMAGE_WIDTH_MAX, CV_8U);
    sprintf(formatStr, "%%%dd", numDigits);
    
    // create tile images from 0-9
    std::vector<aj::Image> digitImages;
    for (int i=0; i<=9; i++) {
        cvImage = cv::Mat::zeros(DMD_IMAGE_HEIGHT_MAX, tileWidth, CV_8U);
        sprintf(frameStr, "%d", i);
        cv::putText(cvImage, frameStr, cv::Point(0, 1000),  cv::FONT_HERSHEY_TRIPLEX, 4, 255, 5);
        cv::rectangle(cvImage, cv::Point(10, 900-i*(tileWidth)), cv::Point(70, 900), 255, -1);
        aj::Image image;
        image.ReadFromMemory((u8*)cvImage.data, cvImage.rows, cvImage.cols, 1, 8, ROW_MAJOR_ORDER, cvImage.rows, cvImage.cols, 1, 1, COLUMN_MAJOR_ORDER);
        digitImages.push_back(image);
    }

    // create progress bar images
    std::vector<aj::Image> progressBarImages;
    int startRow = DMD_IMAGE_HEIGHT_MAX - (DMD_IMAGE_HEIGHT_MAX - progressBarHeight)/2;
    for (int i=1; i<=progressBarHeight; i++) {
        cvImage = cv::Mat::zeros(DMD_IMAGE_HEIGHT_MAX, tileWidth, CV_8U);
        cv::rectangle(cvImage, cv::Point(0, startRow-i), cv::Point(tileWidth, startRow), 255, -1);
        aj::Image image;
        image.ReadFromMemory((u8*)cvImage.data, cvImage.rows, cvImage.cols, 1, 8, ROW_MAJOR_ORDER, cvImage.rows, cvImage.cols, 1, 1, COLUMN_MAJOR_ORDER);
        progressBarImages.push_back(image);
    }

    cvImage = cv::Mat::zeros(DMD_IMAGE_HEIGHT_MAX, tileWidth, CV_8U);
    aj::Image zeroImage;    
    zeroImage.ReadFromMemory((u8*)cvImage.data, cvImage.rows, cvImage.cols, 1, 8, ROW_MAJOR_ORDER, cvImage.rows, cvImage.cols, 1, 1, COLUMN_MAJOR_ORDER);

    aj::Image streamingImage;
    streamingImage.SetImagePropertiesForDevice(aj::DMD_4500_DEVICE_TYPE);
    streamingImage.AllocateMemory(ComputeImageSize(streamingImage.Width(), streamingImage.Height(), streamingImage.BitDepth(), streamingImage.NumChannels()));
    memset(streamingImage.memAddress_, 0, streamingImage.Size());

    vector< aj::Image > dmdImages;
    for (int imageNum=0; imageNum<DMD_NUM_IMAGES; imageNum++) {
        // copy in the memory from the tile images based on the image number
        unsigned char* currImageIndex = streamingImage.memAddress_;
        // copy progress bar
        aj::Image& imageTile = progressBarImages[imageNum % progressBarHeight];
        memcpy(currImageIndex, imageTile.memAddress_, imageTile.Size());
        currImageIndex += imageTile.Size();
        // copy digits with frame number
        sprintf(frameStr, formatStr, imageNum);
        for (int i=0; i<numDigits; i++) {
            int digit = 0;
            int prevDigit = 0;
            if (frameStr[i] != ' ') digit = frameStr[i] - '0';
            if (prevFrameStr[i] != ' ') prevDigit = prevFrameStr[i] - '0';
            if (digit != prevDigit)
                memcpy(currImageIndex, digitImages[digit].memAddress_, digitImages[digit].Size());
            currImageIndex += digitImages[digit].Size();
        }
        strcpy(prevFrameStr, frameStr);
        dmdImages.push_back(streamingImage);
    }
    
    u32 cameraFrameNum = 0;
    u32 nextCameraImageID = CAMERA_FIRST_IMAGE_ID;
    u32 lastCameraFrameNum = 0;
    int cameraImageWidth = project.Components()[cameraIndex].NumColumns();
    int cameraImageHeight = project.Components()[cameraIndex].NumRows();
    int framesDisplayed = 0;

    // acquire DMD_NUM_IMAGES from the camera, which means DMD_NUM_IMAGES will automatically be sent to the host when they are captured
    driver.AcquireImages(DMD_NUM_IMAGES, cameraIndex);
    
    char keyPress = 0;
    while (framesDisplayed < DMD_NUM_IMAGES) {
        if (!driver.IsSequenceStatusQueueEmpty(dmdIndex)) {
            SequenceStatusValues seqStatus = driver.GetNextSequenceStatus(dmdIndex);
            framesDisplayed += DMD_REPORTING_FREQUENCY;
        }
        // load DMD streaming sequence items
        if ((driver.GetNumStreamingSequenceItems(dmdIndex) < maxStreamingSequenceItems) && (frameNum < DMD_NUM_IMAGES)) {
            // create a new sequence item and frame to be streamed
            aj::SequenceItem streamingSeqItem = aj::SequenceItem(dmdSequenceID, 1);
            aj::Frame streamingFrame = aj::Frame( dmdSequenceID, 0, aj::FromMSec(frameTime_ms), 0, 0, DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
            // attach the next streaming image to the streaming frame
            streamingFrame.SetStreamingImage(dmdImages[frameNum % DMD_NUM_IMAGES]);
            frameNum++;
            // add the frame to the streaming sequence item
            streamingSeqItem.AddFrame(streamingFrame);
            // send the streaming sequence item to the device
            driver.AddStreamingSequenceItem(streamingSeqItem, dmdIndex);
        } else {
            // when enough images have been preloaded start the streaming sequence
            if (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_STOPPED && !dmdRunning) {
                printf("Starting DMD\n");
                driver.StartSequence(dmdSequenceID, dmdIndex, DMD_REPORTING_FREQUENCY);
                dmdRunning = true;
            }
        }

    }

    // stop the device when we are done
    driver.StopSequence(dmdIndex);
    driver.StopSequence(cameraIndex);
    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_RUNNING ||
           ajileSystem.GetDeviceState(cameraIndex)->RunState() == aj::RUN_STATE_RUNNING) ;
    
    printf("All DMD images have been sent, reading out camera images.\n");
    printf("Press any key to read out and display the next image, or press q to quit.\n");

    keyPress = 0;
    while (cameraFrameNum < DMD_NUM_IMAGES && keyPress != 'q' && keyPress != 'Q') {
        // wait until acquired images are available in the acquired image queue
        if (!driver.IsAcquiredImageQueueEmpty(cameraIndex)) {
            const aj::Image& img = driver.GetNextAcquiredImage(cameraIndex);
            if (img.Size() == cameraImageH * cameraImageW) {
                // copy the acquired image to an OpenCV image for display
                cvImage = cv::Mat::zeros(cameraImageH, cameraImageW, CV_8UC1);
                memcpy(cvImage.data, img.memAddress_, img.Size());
                cv::resize(cvImage, cvImage, cv::Size(cameraImageW/4, cameraImageH/4));
                cv::normalize(cvImage, cvImage, 0, 255, cv::NORM_MINMAX);
                printf("Displaying image number %d\n", cameraFrameNum);
                cv::imshow("Camera Image", cvImage);
                // pausing every 1000 frames to allow verification (999, 1999, 2999, ...)
                if ((cameraFrameNum+1) % 1000 == 0)
                    keyPress = cv::waitKey(1000);
                else
                    keyPress = cv::waitKey(1);
            } else {
                printf("Image %d bad size, %u\n", cameraFrameNum, img.Size());
            }
            driver.PopNextAcquiredImage(cameraIndex);
            cameraFrameNum++;
        } else {
            driver.WaitForAcquiredImage(cameraIndex);
        }
    }

    return 0;
}

int main(int argc, char **argv) {

    return RunStreaming(argc, argv);

}
