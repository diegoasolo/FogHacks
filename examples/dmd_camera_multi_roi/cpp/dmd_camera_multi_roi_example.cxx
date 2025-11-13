#include <ajile/AJObjects.h>
#include <ajile/HostSystem.h>
#include <ajile/ControllerDriver.h>
#include <ajile/dmd_constants.h>
#include <ajile/camera_constants.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
    #include <winsock.h> 
#endif

#include <opencv2/opencv.hpp>

#ifdef OS_WINDOWS
#include <windows.h>
int gettimeofday(struct timeval * tp, struct timezone * tzp);
#else
#include <sys/time.h>
#endif
int timeval_subtract (struct timeval *result, struct timeval *x, struct timeval *y);

const unsigned int DISPLAY_RATE_US = 13333; // 75Hz display rate, which is the refresh rate of most monitors

const int CAMERA_FIRST_IMAGE_ID = 10;

int CreateCameraSequence(aj::Project& project, float frameTime_ms, int cameraIndex, int cameraSequenceID, unsigned int roiFirstRow, unsigned int roiNumRows, unsigned int subsampleRowSkip) {

    const Component& cameraComponent = project.Components()[cameraIndex];       

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
    const unsigned int NUM_IMAGES = 10;

    // add the images - these are the image buffers where the camera will store its data
    for (unsigned int i=CAMERA_FIRST_IMAGE_ID; i<CAMERA_FIRST_IMAGE_ID+NUM_IMAGES; i++) {
        imageBuffer.SetID(i);
        project.AddImage(imageBuffer);
    }

    // add the camera sequence
    project.AddSequence(Sequence(cameraSequenceID, "Image Capture Test Sequence", cameraDeviceType, SEQ_TYPE_PRELOAD, 0));

    // create a camera sequence item - all frames will be added to it
    project.AddSequenceItem(SequenceItem(cameraSequenceID, 1));
    
    // create frames - these refer to image IDs (the image buffers) and have the timing parameters and other camera properties for each frame
    unsigned int startRow = roiFirstRow;
    for (unsigned int i=CAMERA_FIRST_IMAGE_ID; i<CAMERA_FIRST_IMAGE_ID+NUM_IMAGES; i++) {
        roiFirstRow = startRow + ((i-CAMERA_FIRST_IMAGE_ID)*cameraImageHeight) % cameraComponent.NumRows();
        printf("Roi First row: %d\n", roiFirstRow);
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
    driver.StartSequence(cameraSequenceID, cameraIndex);
    // wait for feedback that the camera is running
    while (ajileSystem.GetDeviceState(cameraIndex)->RunState() != aj::RUN_STATE_RUNNING) ;
    
    // local variables used to generate DMD images
    const u32 dmdImageSize = DMD_IMAGE_WIDTH_MAX * DMD_IMAGE_HEIGHT_MAX / 8;
    const u32 maxStreamingSequenceItems = 800;
    u32 frameNum = 0;
    u32 lastFrameNum = 0;
    char frameStr[80];
    char prevFrameStr[80];
    char formatStr[80];
    int tileWidth = 80;
    int numDigits = 10;
    int progressBarHeight = 1000;
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

    u32 cameraFrameNum = 0;
    u32 lastCameraFrameNum = 0;
    int cameraImageWidth = project.Components()[cameraIndex].NumColumns();
    int cameraImageHeight = project.Components()[cameraIndex].NumRows();

    cv::Mat imageToDisplay = cv::Mat::zeros(100, 100, CV_8U);
    cv::namedWindow("Ajile DMD Camera Streaming Demo", cv::WindowFlags::WINDOW_AUTOSIZE);

    struct timeval startTime;
    struct timeval currTime;
    struct timeval displayTime;
    struct timeval timeDiff;
    gettimeofday(&startTime, NULL);
    gettimeofday(&displayTime, NULL);
    char keyPress = 0;
    int selectedCameraImage = 0;
    while (keyPress != 'q' && keyPress != 'Q') {
        if (!driver.IsSequenceStatusQueueEmpty(dmdIndex)) {
            SequenceStatusValues seqStatus = driver.GetNextSequenceStatus(dmdIndex);
        }
        // load DMD streaming sequence items
        if (driver.GetNumStreamingSequenceItems(dmdIndex) < maxStreamingSequenceItems) {

            // copy in the memory from the tile images based on the image number
            unsigned char* currImageIndex = streamingImage.memAddress_;
            // copy progress bar
            aj::Image& imageTile = progressBarImages[frameNum % progressBarHeight];
            memcpy(currImageIndex, imageTile.memAddress_, imageTile.Size());
            currImageIndex += imageTile.Size();
            // copy digits with frame number
            sprintf(frameStr, formatStr, frameNum);
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
            // create a new sequence item and frame to be streamed
            aj::SequenceItem streamingSeqItem = aj::SequenceItem(dmdSequenceID, 1);
            aj::Frame streamingFrame = aj::Frame( dmdSequenceID, 0, aj::FromMSec(frameTime_ms), 0, 0, DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
            // attach the next streaming image to the streaming frame
            streamingFrame.SetStreamingImage(streamingImage);
            frameNum++;
            // add the frame to the streaming sequence item
            streamingSeqItem.AddFrame(streamingFrame);
            // send the streaming sequence item to the device
            driver.AddStreamingSequenceItem(streamingSeqItem, dmdIndex);
        } else {
            // when enough images have been preloaded start the streaming sequence
            if (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_STOPPED) {
                driver.StartSequence(dmdSequenceID, dmdIndex, 1);
            }
            // check for a keypress to quit
            cv::namedWindow("Ajile DMD Camera Streaming Demo");
            keyPress = cv::waitKey(1);
        }        
        if (!driver.IsSequenceStatusQueueEmpty(cameraIndex)) {
            SequenceStatusValues seqStatus = driver.GetNextSequenceStatus(cameraIndex);                
            cameraFrameNum++;
        }

        // report the frame rate
        gettimeofday(&currTime, NULL);
        timeval_subtract(&timeDiff, &currTime, &startTime);
        if (timeDiff.tv_sec > 0) {            
            printf("DMD Frame: %u. DMD Rate: %f fps. Camera Frame: %u. Camera Rate: %f fps.\n",
                   frameNum, (float)(frameNum - lastFrameNum) / ((float)timeDiff.tv_sec+(float)timeDiff.tv_usec/1000000.0),
                   cameraFrameNum, (float)(cameraFrameNum - lastCameraFrameNum) / ((float)timeDiff.tv_sec+(float)timeDiff.tv_usec/1000000.0));
            printf("Press 'q' to quit, or 0-9 to select which camera image number to display\n");
            lastFrameNum = frameNum;
            lastCameraFrameNum = cameraFrameNum;
            startTime = currTime;
        }

        // display the camera image - only displaying at DISPLAY_RATE_US and not the full camera rate since the screen refresh rate is much slower than the camera
        gettimeofday(&currTime, NULL);
        timeval_subtract(&timeDiff, &currTime, &displayTime);
        if (timeDiff.tv_sec > 0 || timeDiff.tv_usec > DISPLAY_RATE_US) {
            driver.RetrieveImage(RETRIEVE_FROM_IMAGE, CAMERA_FIRST_IMAGE_ID+selectedCameraImage, 0, 0, 0, 0, 0);
            const Image& img = driver.GetLastImageRetrieved();
            //const Image& img = driver.RetrieveImage(RETRIEVE_FROM_IMAGE, CAMERA_FIRST_IMAGE_ID+selectedCameraImage);  // alternate all-in-one (blocking) way to retrieve camera images
            if (img.Size() > 0) {
                cvImage = cv::Mat(cv::Size(img.Width(), img.Height()), CV_8U, img.memAddress_);
                cv::resize(cvImage, imageToDisplay, cv::Size(img.Width()/4, img.Height()/4));
                cv::normalize(imageToDisplay, imageToDisplay, 0, 255, cv::NORM_MINMAX);
                cv::imshow("Ajile DMD Camera Streaming Demo", imageToDisplay);
            }

            keyPress = cv::waitKey(1);
            // if the key pressed was a digit, switch the selected camera image to display
            if (keyPress >= '0' && keyPress <= '9') {
                selectedCameraImage = keyPress - '0';
                printf("Selected camera image to display is %d\n", selectedCameraImage);
            }
            
            displayTime = currTime;
        }
    }    
    
    // stop the device when we are done
    driver.StopSequence(dmdIndex);
    driver.StopSequence(cameraIndex);
    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_RUNNING ||
           ajileSystem.GetDeviceState(cameraIndex)->RunState() == aj::RUN_STATE_RUNNING) ;

    return 0;
}

int main(int argc, char **argv) {

    return RunStreaming(argc, argv);

}

#ifdef OS_WINDOWS
static const unsigned __int64 epoch = ((unsigned __int64) 116444736000000000ULL);

int gettimeofday(struct timeval * tp, struct timezone * tzp)
{
    FILETIME    file_time;
    SYSTEMTIME  system_time;
    ULARGE_INTEGER ularge;

    GetSystemTime(&system_time);
    SystemTimeToFileTime(&system_time, &file_time);
    ularge.LowPart = file_time.dwLowDateTime;
    ularge.HighPart = file_time.dwHighDateTime;

    tp->tv_sec = (long) ((ularge.QuadPart - epoch) / 10000000L);
    tp->tv_usec = (long) (system_time.wMilliseconds * 1000);

    return 0;
}
#endif

int timeval_subtract (struct timeval *result, struct timeval *x, struct timeval *y)
{
    /* Perform the carry for the later subtraction by updating y. */
    if (x->tv_usec < y->tv_usec) {
        int nsec = (y->tv_usec - x->tv_usec) / 1000000 + 1;
        y->tv_usec -= 1000000 * nsec;
        y->tv_sec += nsec;
    }
    if (x->tv_usec - y->tv_usec > 1000000) {
        int nsec = (x->tv_usec - y->tv_usec) / 1000000;
        y->tv_usec += 1000000 * nsec;
        y->tv_sec -= nsec;
    }

    /* Compute the time remaining to wait.
       tv_usec is certainly positive. */
    result->tv_sec = x->tv_sec - y->tv_sec;
    result->tv_usec = x->tv_usec - y->tv_usec;

    /* Return 1 if result is negative. */
    return x->tv_sec < y->tv_sec;
}
