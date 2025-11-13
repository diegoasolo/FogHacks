#include <vector>
#include <utility>
#include <opencv2/opencv.hpp>

#include <ajile/HostSystem.h>
#include <ajile/ControllerDriver.h>
#include <ajile/AJObjects.h>
#include <ajile/dmd_constants.h>

#ifdef OS_WINDOWS
// TODO: windows way of signaling g_stopRunning
#else
#include <signal.h>
#endif

#define NUM_IMAGES 2 // change to 1 to disable double buffering, which causes image jump!

bool g_stopRunning = false;

void stopRunning(int sig)
{
    printf("Stopping image load!\n");
    g_stopRunning = true;
}

std::vector<cv::Mat> GenerateImages(int width, int height) {

    int numImages = NUM_IMAGES;
    int rectSize = 100;

    // Allocate the images
    std::vector<cv::Mat> images;
    for (int i=0; i<numImages; i++)
        images.push_back(cv::Mat::zeros(height, width, CV_8UC1));    

    return images;
}

// creates an Ajile project and returns in
std::pair<aj::Project, std::vector<aj::Image> > CreateProject(unsigned short sequenceID=1, unsigned int sequenceRepeatCount=0, float frameTime_ms=-1, std::vector<aj::Component> components = std::vector<aj::Component>()) {

    const char* projectName = "dmd_reload_image_example";
    if (frameTime_ms < 0)
        frameTime_ms = 100;
    
    // create a new project
    aj::Project project(projectName);
    if (components.size() > 0)
        project.SetComponents(components);

    // generate a list of images (which are opencv matrices)
    std::vector<cv::Mat> images = GenerateImages(DMD_IMAGE_WIDTH_MAX, DMD_IMAGE_HEIGHT_MAX);
        
    // create the image sequence
    project.AddSequence(aj::Sequence(sequenceID, "double buffer", aj::DMD_4500_DEVICE_TYPE, aj::SEQ_TYPE_PRELOAD, sequenceRepeatCount));

    // create the images
    std::vector<aj::Image> imageList;
    int numImages = images.size();
    u16 nextImageID = 1;
    for (int i=0; i<numImages; i++) {

        // add the image
        aj::Image image;
        image.ReadFromMemory((unsigned char*)images[i].data, images[i].rows, images[i].cols, 1, 8, aj::ROW_MAJOR_ORDER, aj::DMD_4500_DEVICE_TYPE);
        image.SetID(nextImageID);
        project.AddImage(image);
        imageList.push_back(image);
        
        // create a sequence item and add it.
        // Note that it has an infinite repeat count since we will be many advancing sequence items with NextSequenceItem()
        aj::SequenceItem sequenceItem(sequenceID);
        sequenceItem.SetRepeatCount(0);
        project.AddSequenceItem(sequenceItem);

        // create and add frame
        aj::Frame frame(sequenceID, nextImageID, aj::FromMSec(frameTime_ms));
        project.AddFrame(frame);

        // update the image ID for the next set of images
        nextImageID += 1;
    }
    
    return std::pair<aj::Project, std::vector<aj::Image> >(project, imageList);
}

int RunExample(int argc, char *argv[]) {

    // default connection settings
    char ipAddress[32] = "192.168.2.210";
    char netmask[32] = "255.255.255.0";
    char gateway[32] = "0.0.0.0";
    unsigned short port = 5005;
    CommunicationInterfaceType_e commInterface = aj::USB2_INTERFACE_TYPE;

    // default sequence settings
    unsigned int repeatCount = 0; // repeat forever
    float frameTime_ms = -1.0; // frame time in milliseconds
    unsigned short sequenceID = 1;

    // read command line arguments
    for (int i=1; i<argc; i++) {
        if (strcmp(argv[i], "-i") == 0) {
            strcpy(ipAddress, argv[++i]);
        } else if (strcmp(argv[i], "-r") == 0) {
            repeatCount = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-f") == 0) {
            frameTime_ms = atof(argv[++i]);
        } else if (strcmp(argv[i], "--usb3") == 0) {
            commInterface = aj::USB3_INTERFACE_TYPE;
        } else {
            printf("Usage: %s [-i <IP address>] [-r <repeat count>] [-f <frame rate in ms>] [--usb3]\n", argv[0]);
            exit(2);
        }
    }

    // connect to the device
    aj::HostSystem ajileSystem;
    ajileSystem.SetConnectionSettingsStr(ipAddress, netmask, gateway, port);
    ajileSystem.SetCommunicationInterface(commInterface);
    if (ajileSystem.StartSystem() != aj::ERROR_NONE) {
        printf("Error starting AjileSystem.\n");
        exit(-1);
    }

    // create the project
    std::pair<aj::Project, std::vector<aj::Image> > projectAndImages = CreateProject(sequenceID, repeatCount, frameTime_ms, ajileSystem.GetProject()->Components());
    aj::Project project = projectAndImages.first;
    std::vector<aj::Image> imageList = projectAndImages.second;


    // pre-generate image data
    int rectSize = 80;
    aj::Image rectangleImage;
    cv::Mat cvImage = cv::Mat::zeros(DMD_IMAGE_HEIGHT_MAX, rectSize, CV_8U);
    cv::rectangle(cvImage, cv::Point(0, DMD_IMAGE_HEIGHT_MAX/2 - rectSize), cv::Point(rectSize, DMD_IMAGE_HEIGHT_MAX/2 + rectSize), 255, -1);
    rectangleImage.ReadFromMemory((u8*)cvImage.data, cvImage.rows, cvImage.cols, 1, 8, ROW_MAJOR_ORDER, cvImage.rows, cvImage.cols, 1, 1, COLUMN_MAJOR_ORDER);

    // get the first valid component index which will run the sequence
    bool wasFound = false;
    const aj::Sequence& sequence = project.FindSequence(sequenceID, wasFound);
    if (!wasFound) exit(-1);
    int componentIndex = ajileSystem.GetProject()->GetComponentIndexWithDeviceType(sequence.HardwareType());

    // stop any existing project from running on the device
    ajileSystem.GetDriver()->StopSequence(componentIndex);

    // load the project to the device
    ajileSystem.GetDriver()->LoadProject(project);
    ajileSystem.GetDriver()->WaitForLoadComplete(-1);

#ifdef OS_WINDOWS
    // TODO: find windows equivalent
#else
    struct sigaction act;
    act.sa_handler = stopRunning;
    sigemptyset(&act.sa_mask);
    act.sa_flags = 0;
    sigaction(SIGINT, &act, 0);
    g_stopRunning = false;
#endif

    // run the project
    if (frameTime_ms >= 0)
        printf("Starting sequence %d with frame rate %f and repeat count %d\n", sequence.ID(), frameTime_ms, repeatCount);

    ajileSystem.GetDriver()->StartSequence(sequence.ID(), componentIndex);
    
    // wait for the sequence to start
    printf("Waiting for sequence %d to start\n", sequence.ID());
    while (ajileSystem.GetDeviceState(componentIndex)->RunState() != aj::RUN_STATE_RUNNING) ;

    u32 frameNum = 0;
    u32 frameProcessed = 0;
    struct timespec startTime;
    struct timespec currTime;
    double elapsedTime = 0;
    aj::GetTime(&startTime);
    u32 totalSeconds = 0;
    int nextImageBufferNum = NUM_IMAGES - 1; // NOTE: setting this to 0 will cause image jumps since we will be updating the image we are displaying!
    int rectLocation = 0;
    while ((!g_stopRunning) && (frameProcessed < repeatCount)) {

        // Uncomment this if statement (following 4 lines) to wait for the sequence status to update.
        // Without this, this loop will update the images as fast as possible and so depending on the frame rate
        // we will likely be updating the images at a different rate than they are being displayed, resulting in jumpy animation
        if (!ajileSystem.GetDriver()->IsSequenceStatusQueueEmpty(componentIndex))
            SequenceStatusValues seqStatus = ajileSystem.GetDriver()->GetNextSequenceStatus(componentIndex);
        else
            continue;
        
        // Update the image. Note we must update the image number which is not currently being displayed.
        memcpy(imageList[nextImageBufferNum].memAddress_+rectLocation*DMD_IMAGE_HEIGHT_MAX/8,
               rectangleImage.memAddress_, rectSize*DMD_IMAGE_HEIGHT_MAX/8);
        // load the image to the device and wait for it to complete.
        ajileSystem.GetDriver()->LoadImage(imageList[nextImageBufferNum]);
        ajileSystem.GetDriver()->WaitForLoadComplete();
        u32 imagesToLoad = ajileSystem.GetDriver()->GetNumImagesToLoad();
        if (imagesToLoad != 0)
            printf("Images to load non-zero! %u\n", imagesToLoad);
        // advance to the next sequence item, which will cause the image to update
        ajileSystem.GetDriver()->NextSequenceItem(componentIndex);
        //ajileSystem.GetDriver()->GotoSequenceItem(componentIndex, nextImageBufferNum); // also works well
        // clear the image memory for next time
        memset(imageList[nextImageBufferNum].memAddress_+rectLocation*DMD_IMAGE_HEIGHT_MAX/8,
               0, rectSize*DMD_IMAGE_HEIGHT_MAX/8);
        // advance the buffer number and rectangle location for next time
        nextImageBufferNum = (nextImageBufferNum + 1) % NUM_IMAGES;
        rectLocation = (rectLocation + 16) % (DMD_IMAGE_WIDTH_MAX-rectSize);
        frameNum += 1;
        frameProcessed++;
        aj::GetTime(&currTime);
        elapsedTime = GetTimeDifferenceMSec(&currTime, &startTime);
        if (elapsedTime > 1000) {
            totalSeconds += 1;
            printf("Frame rate: %u f/s. Total time elapsed %u s. Press Ctrl-C to stop.\n", frameNum, totalSeconds);
            frameNum = 0;
            aj::GetTime(&startTime);
        }
        
    }            
            
    ajileSystem.GetDriver()->StopSequence(componentIndex);

    printf("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(componentIndex)->RunState() == aj::RUN_STATE_RUNNING) ;

    return 0;
}

int main(int argc, char **argv) {

    return RunExample(argc, argv);

}
