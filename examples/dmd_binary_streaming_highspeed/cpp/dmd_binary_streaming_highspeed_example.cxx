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

void PrintUsage(int argc, char *argv[]) {
    printf("Usage: %s [-i <IP address>] [-f <frame rate in ms>] [--usb3|--pcie] [-t]\n\n", argv[0]);
    printf("\t-i <IP address>:\t set the ip address\n");
    printf("\t-f <frame rate in ms>:\t set the frame rate, in ms\n");
    printf("\t--usb3:\t use the USB3 interface (default is Ethernet/USB2)\n");
    printf("\t--pcie:\t use the PCIE interface\n");
    printf("\t--eth:\t use the Ethernet interface\n");
    printf("\t--trig:\t enable trigger output from DMD\n");
}

int RunStreaming(int argc, char *argv[]) {

    // default connection settings
    char ipAddress[32] = "192.168.200.1";
    char netmask[32] = "255.255.255.0";
    char gateway[32] = "0.0.0.0";
    unsigned short port = 5005;
    CommunicationInterfaceType_e commInterface = aj::PCIE_INTERFACE_TYPE;

    // default sequence settings
    unsigned int repeatCount = 0; // repeat forever
    float frameTime_ms = ToMSec(FromSec(1.0/6600.0)); // frame time in milliseconds    
    unsigned short dmdSequenceID = 1;
    bool useTriggers = false;

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
        } else if (strcmp(argv[i], "-r") == 0) {
            repeatCount = atoi(argv[++i]); 
        } else if (strcmp(argv[i], "--pcie") == 0) {
            commInterface = aj::PCIE_INTERFACE_TYPE;
            printf("Using PCIe interface\n");
        } else if (strcmp(argv[i], "--eth") == 0) {
            commInterface = aj::GIGE_INTERFACE_TYPE;
            printf("Using Ethernet interface\n");
        } else if (strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--trig") == 0) {
            useTriggers = true;
            printf("DMD trigger output enabled\n");
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
    aj::Project project("dmd_binary_streaming_highspeed_example");
    // get the connected devices from the project structure
    project.SetComponents(ajileSystem.GetProject()->Components());

    // find the DMD device index
    int dmdIndex = project.GetComponentIndexWithDeviceType(aj::DMD_4500_DEVICE_TYPE);
    if (dmdIndex < 0) {
        printf("DMD device not found.\n");
        return -1;
    }
    
    // set the amount of memory available for preloaded images to minimal, since we will be streaming
    Component controllerComponent = project.Components()[0];
    u32 controllerMemory = controllerComponent.ImageMemorySize();
    controllerComponent.SetImageMemorySize(0x00001000);
    project.SetComponent(0, controllerComponent);

    // set the amount memory available for DMD streaming images
    Component dmdComponent = project.Components()[dmdIndex];
    u32 dmdMemory = dmdComponent.ImageMemorySize();
    dmdComponent.SetImageMemorySize(0x10000000);
    project.SetComponent(dmdIndex, dmdComponent);

    // create trigger from DMD to external trigger if enabled
    if (useTriggers) {
        aj::TriggerRule dmdFrameStartedToExtTrigOut;
        dmdFrameStartedToExtTrigOut.AddTriggerFromDevice(aj::TriggerRulePair(dmdIndex, aj::FRAME_STARTED));
        dmdFrameStartedToExtTrigOut.SetTriggerToDevice(aj::TriggerRulePair(0, aj::EXT_TRIGGER_OUTPUT_1));
        // add the trigger rule to the project
        project.AddTriggerRule(dmdFrameStartedToExtTrigOut);
    }

    // stop any existing project from running on the device
    driver.StopSequence(dmdIndex);

    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(dmdIndex)->RunState() != aj::RUN_STATE_STOPPED) ;    
    
    // create the streaming sequence
    project.AddSequence(aj::Sequence(dmdSequenceID, "dmd_binary_streaming_highspeed_example", aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_STREAM, 1, deque<SequenceItem>(), aj::RUN_STATE_PAUSED));
    
    // load the project
    driver.LoadProject(project);
    driver.WaitForLoadComplete(-1);

    // local variables used to generate DMD images
    const u32 dmdImageSize = DMD_IMAGE_WIDTH_MAX * DMD_IMAGE_HEIGHT_MAX / 8;
    const u32 maxStreamingSequenceItems = dmdComponent.ImageMemorySize() / dmdImageSize;
    u32 frameNum = 0;
    u32 framesProcessed = 0;
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

    aj::Image streamingImage;
    streamingImage.SetImagePropertiesForDevice(aj::DMD_4500_DEVICE_TYPE);
    streamingImage.AllocateMemory(ComputeImageSize(streamingImage.Width(), streamingImage.Height(), streamingImage.BitDepth(), streamingImage.NumChannels()));
    memset(streamingImage.memAddress_, 0, streamingImage.Size());

#if (CV_MAJOR_VERSION == 3)
    cv::namedWindow("Ajile DMD Streaming Demo", CV_WINDOW_AUTOSIZE );
#else // (CV_MAJOR_VERSION == 4)
    cv::namedWindow("Ajile DMD Streaming Demo", cv::WINDOW_AUTOSIZE );
#endif

    struct timeval startTime;
    struct timeval currTime;
    struct timeval displayTime;
    struct timeval timeDiff;
    gettimeofday(&startTime, NULL);
    gettimeofday(&displayTime, NULL);
    char keyPress = 0;
    while ((keyPress != 'q' && keyPress != 'Q') && (repeatCount == 0 || framesProcessed < repeatCount) ) {
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
            framesProcessed++;
            // add the frame to the streaming sequence item
            streamingSeqItem.AddFrame(streamingFrame);
            // send the streaming sequence item to the device
            driver.AddStreamingSequenceItem(streamingSeqItem, dmdIndex);
        } else {
            // when enough images have been preloaded start the streaming sequence
            if (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_STOPPED && !dmdRunning) {
                driver.StartSequence(dmdSequenceID, dmdIndex, 10);
                dmdRunning = true;
            }
            // check for a keypress to quit
            cv::namedWindow("Ajile DMD Streaming Demo");
            keyPress = cv::waitKey(1);
        }

        // report the frame rate
        gettimeofday(&currTime, NULL);
        timeval_subtract(&timeDiff, &currTime, &startTime);
        if (timeDiff.tv_sec > 0) {            
            printf("DMD Frame: %u. DMD Rate: %f fps.\n",
                   frameNum, (float)(frameNum - lastFrameNum) / ((float)timeDiff.tv_sec+(float)timeDiff.tv_usec/1000000.0));
            lastFrameNum = frameNum;
            startTime = currTime;
        }

    }    
    
    // stop the device when we are done
    driver.StopSequence(dmdIndex);
    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(dmdIndex)->RunState() == aj::RUN_STATE_RUNNING);

    project = Project("dmd_binary_streaming_highspeed_example");
    // get the connected devices from the project structure
    project.SetComponents(ajileSystem.GetProject()->Components());
    controllerComponent = project.Components()[0];
    controllerComponent.SetImageMemorySize(controllerMemory);
    project.SetComponent(0, controllerComponent);
    dmdComponent = project.Components()[dmdIndex];
    dmdComponent.SetImageMemorySize(dmdMemory);
    project.SetComponent(dmdIndex, dmdComponent);
    driver.LoadComponent(dmdComponent, dmdIndex);
    driver.LoadComponent(controllerComponent, 0);    
    driver.WaitForLoadComplete(-1);


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
