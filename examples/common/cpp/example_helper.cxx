#include "example_helper.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <algorithm>

#include <ajile/HostSystem.h>
#include <ajile/ControllerDriver.h>
#include <ajile/camera_constants.h>

#ifdef EXAMPLE_OPENCV_REQUIRED
#include <opencv2/opencv.hpp>
#endif

Parameters::Parameters() {
    // initialize defaults
    strncpy ( ipAddress, "192.168.200.1", sizeof(ipAddress) );
    strncpy ( netmask, "255.255.255.0", sizeof(netmask) );
    strncpy ( gateway, "0.0.0.0", sizeof(gateway) );
    port = 5005;
    commInterface = aj::USB2_INTERFACE_TYPE;
    deviceNumber = 0;
    repeatCount = 0; // repeat forever
    frameTime_ms = -1.0; // frame time in milliseconds
    sequenceID = 1;
    bitDepth = CMV4000_BIT_DEPTH;
    roiFirstRow = 0;
    roiNumRows = CMV4000_IMAGE_HEIGHT_MAX;
    subsampleRowSkip = 0;
}

void PrintUsage(int argc, char *argv[]) {
    printf ("Usage: %s [options]\n", argv[0]);
    printf ("Options:\n");
    printf ("\t-h | --help:\t print this help message\n");
    printf ("\t-i <IP address>:\t set the ip address\n");
    printf ("\t-r <repeat count>:\t set the sequence repeat count\n");
    printf ("\t-f <frame rate in ms>:\t set the frame rate, in milliseconds\n");
    printf ("\t--usb3:\t use the USB3 interface (default is USB2)\n");
    printf ("\t--pcie:\t use the PCIE interface (default is USB2)\n");
    printf ("\t--eth:\t use the Ethernet interface (default is USB2)\n");
    printf ("\t-d <deviceNumber>:\t use a different device number than device 0\n");
    printf ("\t--roi <roiFirstRow> <roiNumRows>:\t set the region of interest (first row and number of rows); used by the camera\n");
    printf ("\t--sub <subsampleRowSkip>:\t enable camera image subsampling, specifying the number of rows to skip between each row (e.g. 1 skips every other row so selects every 2nd row, 3 selects every 4th row, etc.\n");
    printf("\t--bit <bit depth>:\t set the camera bit depth, either 10 (default) or 8\n");
}

void ParseCommandArguments(Parameters& parameters, int argc, char *argv[]) {
    // read command line arguments
    for (int i=1; i<argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            PrintUsage(argc, argv);
        } else if (strcmp(argv[i], "-i") == 0) {
            strcpy(parameters.ipAddress, argv[++i]);
        } else if (strcmp(argv[i], "-r") == 0) {
            parameters.repeatCount = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-f") == 0) {
            parameters.frameTime_ms = atof(argv[++i]);
        } else if (strcmp(argv[i], "--usb3") == 0) {
            parameters.commInterface = aj::USB3_INTERFACE_TYPE;
        } else if (strcmp(argv[i], "--pcie") == 0) {
            parameters.commInterface = aj::PCIE_INTERFACE_TYPE;
        } else if (strcmp(argv[i], "--eth") == 0) {
            parameters.commInterface = aj::GIGE_INTERFACE_TYPE;
        } else if (strcmp(argv[i], "-d") == 0) {
            parameters.deviceNumber = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--roi") == 0) {
            parameters.roiFirstRow = atoi(argv[++i]);
            parameters.roiNumRows = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--sub") == 0) {
            parameters.subsampleRowSkip = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--bit") == 0) {
            parameters.bitDepth = atoi(argv[++i]);
        } else {
            PrintUsage(argc, argv);
            exit(2);
        }
    }
}

void ConnectToDevice(aj::HostSystem& ajileSystem, Parameters& parameters) {
    // connect to the device
    ajileSystem.SetConnectionSettingsStr(parameters.ipAddress, parameters.netmask, parameters.gateway, parameters.port);
    ajileSystem.SetCommunicationInterface(parameters.commInterface);
    ajileSystem.SetUSB3DeviceNumber(parameters.deviceNumber);
    if (ajileSystem.StartSystem() != aj::ERROR_NONE) {
        printf("Error starting AjileSystem.\n");
        exit(-1);
    }
}

int RunExample(aj::Project (*createFunction)(unsigned short, unsigned int, float, std::vector<aj::Component>), int argc, char *argv[]) {

    // read the input command line arguments
    Parameters parameters;
    ParseCommandArguments(parameters, argc, argv);

    // connect to the device
    aj::HostSystem ajileSystem;
    ConnectToDevice(ajileSystem, parameters);

    // create the project
    aj::Project project = createFunction(parameters.sequenceID, parameters.repeatCount, parameters.frameTime_ms, ajileSystem.GetProject()->Components());

    // get the first valid component index which will run the sequence
    bool wasFound = false;
    const aj::Sequence& sequence = project.FindSequence(parameters.sequenceID, wasFound);
    if (!wasFound) exit(-1);
    int componentIndex = ajileSystem.GetProject()->GetComponentIndexWithDeviceType(sequence.HardwareType());

    // stop any existing project from running on the device
    ajileSystem.GetDriver()->StopSequence(componentIndex);

    // load the project to the device
    ajileSystem.GetDriver()->LoadProject(project);
    ajileSystem.GetDriver()->WaitForLoadComplete(-1);

    for (map<int, aj::Sequence>::const_iterator iter = project.Sequences().begin(); iter != project.Sequences().end(); iter++) {
        const Sequence& sequence = iter->second;
        // run the project
        if (parameters.frameTime_ms >= 0)
            printf("Starting sequence %d with frame rate %f and repeat count %d\n", sequence.ID(), parameters.frameTime_ms, parameters.repeatCount);

        ajileSystem.GetDriver()->StartSequence(sequence.ID(), componentIndex);
    
        // wait for the sequence to start
        printf("Waiting for sequence %d to start\n", sequence.ID());
        while (ajileSystem.GetDeviceState(componentIndex)->RunState() != aj::RUN_STATE_RUNNING) ;

        if (parameters.repeatCount == 0) {
            printf("Sequence repeating forever. Press Enter to stop the sequence\n");
            getchar();
            ajileSystem.GetDriver()->StopSequence(componentIndex);
        }

        printf("Waiting for the sequence to stop.\n");
        while (ajileSystem.GetDeviceState(componentIndex)->RunState() == aj::RUN_STATE_RUNNING) ;
    }
    
    return 0;
}

int RunCameraExample(aj::Project (*createFunction)(unsigned short, unsigned int, float,
                                                   unsigned int, unsigned int, unsigned int, unsigned int,
                                                   std::vector<aj::Component>),
                     int argc, char *argv[]) {

    // read the input command line arguments
    Parameters parameters;
    ParseCommandArguments(parameters, argc, argv);

    // connect to the device
    aj::HostSystem ajileSystem;
    ConnectToDevice(ajileSystem, parameters);

    // create the project
    aj::Project project = createFunction(parameters.sequenceID, parameters.repeatCount, parameters.frameTime_ms,
                                         parameters.bitDepth, parameters.roiFirstRow, parameters.roiNumRows, parameters.subsampleRowSkip,
                                         ajileSystem.GetProject()->Components());

    // get the first valid component index which will run the sequence
    bool wasFound = false;
    const aj::Sequence& sequence = project.FindSequence(parameters.sequenceID, wasFound);
    if (!wasFound) exit(-1);
    int componentIndex = ajileSystem.GetProject()->GetComponentIndexWithDeviceType(sequence.HardwareType());

    // stop any existing project from running on the device
    ajileSystem.GetDriver()->StopSequence(componentIndex);

    // load the project to the device
    ajileSystem.GetDriver()->LoadProject(project);
    ajileSystem.GetDriver()->WaitForLoadComplete(-1);

    for (map<int, aj::Sequence>::const_iterator iter = project.Sequences().begin(); iter != project.Sequences().end(); iter++) {
        const Sequence& sequence = iter->second;
        // run the project
        if (parameters.frameTime_ms >= 0)
            printf("Starting sequence %d with frame rate %f and repeat count %d\n", sequence.ID(), parameters.frameTime_ms, parameters.repeatCount);
        
        ajileSystem.GetDriver()->StartSequence(sequence.ID(), componentIndex);
        
        // wait for the sequence to start
        printf("Waiting for sequence %d to start\n", sequence.ID());
        while (ajileSystem.GetDeviceState(componentIndex)->RunState() != aj::RUN_STATE_RUNNING) ;
    
        if (parameters.repeatCount == 0) {
            printf("Sequence repeating forever. Select the Ajile Camera Image window and press any key to stop the sequence.\n");
        
            // read out images from the 3D imager, and wait for a user key press or for the sequence to end
            char keyPress = -1;
            while (keyPress < 0 || keyPress == 255) {
                // wait until a frame has been captured by the camera
                if (!ajileSystem.GetDriver()->IsSequenceStatusQueueEmpty()) {
                    // determine the last frame that was captured
                    aj::SequenceStatusValues sequenceStatus = ajileSystem.GetDriver()->GetLatestSequenceStatus();
                    // clear the sequence status history from the queue
                    while (!ajileSystem.GetDriver()->IsSequenceStatusQueueEmpty()) ajileSystem.GetDriver()->GetNextSequenceStatus();
                    // retrieve the latest image from the camera
                    const aj::Image& ajileImage = ajileSystem.GetDriver()->RetrieveImage(aj::RETRIEVE_FROM_FRAME, 0, sequenceStatus.FrameIndex()-1, sequenceStatus.SequenceItemIndex()-1, sequenceStatus.SequenceID());
#ifdef EXAMPLE_OPENCV_REQUIRED
                    if (ajileImage.Width() > 0 && ajileImage.Height() > 0) {
                        // convert to a numpy image for display purposes
                        cv::Mat cvImage = cv::Mat::zeros(ajileImage.Height(), ajileImage.Width(), CV_8UC1);
                        ajileImage.WriteToMemory(cvImage.data, cvImage.rows, cvImage.cols, 1, 8);
                        // display the image, using OpenCV
                        if (ajileImage.Height() >= 1024 || ajileImage.Width() > 1024) {
                            // resize the image so it fits on the screen
                            float scaleFactor = 1024.0 / (float)std::max(ajileImage.Height(), ajileImage.Width());
                            cv::resize(cvImage, cvImage, cv::Size(0, 0), scaleFactor, scaleFactor);
                            cv::imshow("Ajile Camera Image", cvImage);
                        } else {
                            printf("Timeout waiting for camera image.\n");
                        }
                    }
                    keyPress = cv::waitKey(30);
#endif
                }
            }

            ajileSystem.GetDriver()->StopSequence(componentIndex);
        }

        printf ("Waiting for the sequence to stop.\n");
        while (ajileSystem.GetDeviceState(componentIndex)->RunState() == aj::RUN_STATE_RUNNING) ;

        // read out all camera images in the sequence, and save them to file
        for (int seqItemIndex = 0; seqItemIndex < sequence.SequenceItems().size(); seqItemIndex++) {
            const SequenceItem& seqItem = sequence.SequenceItems()[seqItemIndex];
            for (int frameIndex = 0; frameIndex < seqItem.Frames().size(); frameIndex++) {
                const Frame& frame = seqItem.Frames()[frameIndex];
                printf("Reading image %d\n", frame.ImageID());
                const aj::Image& ajileImage = ajileSystem.GetDriver()->RetrieveImage(aj::RETRIEVE_FROM_IMAGE, frame.ImageID());
                if (ajileImage.Width() > 0 && ajileImage.Height() > 0) {
                    int outputBitDepth = ajileImage.BitDepth();
                    if (ajileImage.BitDepth() > 8)
                        outputBitDepth = 16; // saving 10-bit images as 16-bit files
                    char filename[32];
                    sprintf(filename, "image_%d.png", frame.ImageID());
                    ajileImage.WriteToFile(filename, outputBitDepth);
                } else {
                    printf("Timeout waiting for camera image.\n");
                }
            }
        }
    }    

}

int RunCameraDmdExample(aj::Project (*createFunction)(unsigned short, unsigned int, float,
                                                      unsigned int, unsigned int, unsigned int, unsigned int,
                                                      std::vector<aj::Component>),
                        int argc, char *argv[]) {

    // read the input command line arguments
    Parameters parameters;
    ParseCommandArguments(parameters, argc, argv);

    // connect to the device
    aj::HostSystem ajileSystem;
    ConnectToDevice(ajileSystem, parameters);

    // create the project
    aj::Project project = createFunction(parameters.sequenceID, parameters.repeatCount, parameters.frameTime_ms,
                                         parameters.bitDepth, parameters.roiFirstRow, parameters.roiNumRows, parameters.subsampleRowSkip,
                                         ajileSystem.GetProject()->Components());

    // get the first valid component index which will run each sequence
    bool wasFound = false;
    const aj::Sequence& dmdSequence = project.FindSequence(parameters.sequenceID, wasFound);
    if (!wasFound) exit(-1);
    int dmdComponentIndex = ajileSystem.GetProject()->GetComponentIndexWithDeviceType(dmdSequence.HardwareType());

    const aj::Sequence& cameraSequence = project.FindSequence(parameters.sequenceID+1, wasFound);
    if (!wasFound) exit(-1);
    int cameraComponentIndex = ajileSystem.GetProject()->GetComponentIndexWithDeviceType(cameraSequence.HardwareType());

    // stop any existing project from running on the device
    ajileSystem.GetDriver()->StopSequence(dmdComponentIndex);
    ajileSystem.GetDriver()->StopSequence(cameraComponentIndex);

    // load the project to the device
    ajileSystem.GetDriver()->LoadProject(project);
    ajileSystem.GetDriver()->WaitForLoadComplete(-1);

    // first run the DMD sequence, since it will be waiting for the camera trigger
    ajileSystem.GetDriver()->StartSequence(dmdSequence.ID(), dmdComponentIndex);
    // wait for the sequence to start
    printf ("Waiting for DMD sequence %d to start\n", dmdSequence.ID());
    while (ajileSystem.GetDeviceState(dmdComponentIndex)->RunState() != aj::RUN_STATE_RUNNING) ;

    // then run the camera sequence
    ajileSystem.GetDriver()->StartSequence(cameraSequence.ID(), cameraComponentIndex);
            
    // wait for the sequence to start
    printf("Waiting for camera sequence %d to start\n", cameraSequence.ID());
    while (ajileSystem.GetDeviceState(cameraComponentIndex)->RunState() != aj::RUN_STATE_RUNNING) ;
    
    if (parameters.repeatCount == 0) {
        printf("Sequence repeating forever. Select the Ajile Camera Image window and press any key to stop the sequence.\n");
        
        // read out images from the 3D imager, and wait for a user key press or for the sequence to end
        char keyPress = -1;
        while (keyPress < 0 || keyPress == 255) {
            // wait until a frame has been captured by the camera
            if (!ajileSystem.GetDriver()->IsSequenceStatusQueueEmpty(cameraComponentIndex)) {
                // determine the last frame that was captured
                aj::SequenceStatusValues sequenceStatus = ajileSystem.GetDriver()->GetLatestSequenceStatus(cameraComponentIndex);
                // clear the sequence status history from the queue
                while (!ajileSystem.GetDriver()->IsSequenceStatusQueueEmpty(cameraComponentIndex)) ajileSystem.GetDriver()->GetNextSequenceStatus(cameraComponentIndex);
                // retrieve the latest image from the camera
                const aj::Image& ajileImage = ajileSystem.GetDriver()->RetrieveImage(aj::RETRIEVE_FROM_FRAME, 0, sequenceStatus.FrameIndex()-1, sequenceStatus.SequenceItemIndex()-1, sequenceStatus.SequenceID());
#ifdef EXAMPLE_OPENCV_REQUIRED
                if (ajileImage.Width() > 0 && ajileImage.Height() > 0) {
                    // convert to a numpy image for display purposes
                    cv::Mat cvImage = cv::Mat::zeros(ajileImage.Height(), ajileImage.Width(), CV_8UC1);
                    ajileImage.WriteToMemory(cvImage.data, cvImage.rows, cvImage.cols, 1, 8);
                    // display the image, using OpenCV
                    if (ajileImage.Height() >= 1024 || ajileImage.Width() > 1024) {
                        // resize the image so it fits on the screen
                        float scaleFactor = 1024.0 / (float)std::max(ajileImage.Height(), ajileImage.Width());
                        cv::resize(cvImage, cvImage, cv::Size(0, 0), scaleFactor, scaleFactor);
                        cv::imshow("Ajile Camera Image", cvImage);
                    } else {
                        printf("Timeout waiting for camera image.\n");
                    }
                }
                keyPress = cv::waitKey(30);
#endif
            }
        }

        printf ("Stopping the camera sequence.\n");
        ajileSystem.GetDriver()->StopSequence(cameraComponentIndex);
        printf ("Waiting for the camera sequence to stop.\n");
        while (ajileSystem.GetDeviceState(cameraComponentIndex)->RunState() == aj::RUN_STATE_RUNNING) ;
        printf ("Stopping the DMD sequence.\n");
        ajileSystem.GetDriver()->StopSequence(dmdComponentIndex);
    }

    printf ("Waiting for the sequence to stop.\n");
    while (ajileSystem.GetDeviceState(cameraComponentIndex)->RunState() == aj::RUN_STATE_RUNNING) ;
    while (ajileSystem.GetDeviceState(dmdComponentIndex)->RunState() == aj::RUN_STATE_RUNNING) ;

    // read out all camera images in the sequence, and save them to file
    int imageNumber = 0;
    for (int seqItemIndex = 0; seqItemIndex < cameraSequence.SequenceItems().size(); seqItemIndex++) {
        const SequenceItem& seqItem = cameraSequence.SequenceItems()[seqItemIndex];
        for (int frameIndex = 0; frameIndex < seqItem.Frames().size(); frameIndex++) {
            const Frame& frame = seqItem.Frames()[frameIndex];
            printf("Reading image number %d with ID %d\n", imageNumber, frame.ImageID());
            const aj::Image& ajileImage = ajileSystem.GetDriver()->RetrieveImage(aj::RETRIEVE_FROM_IMAGE, frame.ImageID());
            if (ajileImage.Width() > 0 && ajileImage.Height() > 0) {
                int outputBitDepth = ajileImage.BitDepth();
                if (ajileImage.BitDepth() > 8)
                    outputBitDepth = 16; // saving 10-bit images as 16-bit files
                char filename[32];
                sprintf(filename, "image_%d.png", imageNumber);
                ajileImage.WriteToFile(filename, outputBitDepth);
                imageNumber += 1;
            } else {
                printf("Timeout waiting for camera image.\n");
            }
        }
    }

}
