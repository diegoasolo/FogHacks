import sys
import ajiledriver as aj
import os.path
import cv2
import numpy

# Python 2.x - 3.x workaround
try:
    input = raw_input
except NameError:
    pass

class Parameters:
    # default connection settings
    ipAddress = "192.168.200.1"
    netmask = "255.255.255.0"
    gateway = "0.0.0.0"
    port = 5005
    commInterface = aj.USB2_INTERFACE_TYPE
    deviceNumber = 0

    # default sequence settings
    repeatCount = 0 # repeat forever
    frameTime_ms = -1 # frame time in milliseconds
    sequenceID = 1

    # camera settings
    bitDepth = aj.CMV4000_BIT_DEPTH
    roiFirstRow = 0
    roiNumRows = aj.CMV4000_IMAGE_HEIGHT_MAX
    subsampleRowSkip = 0
    
def PrintUsage():
    print ("Usage: " + sys.argv[0] + " [options]")
    print ("Options:")
    print ("\t-h | --help:\t print this help message")
    print ("\t-i <IP address>:\t set the ip address")
    print ("\t-r <repeat count>:\t set the sequence repeat count")
    print ("\t-f <frame rate in ms>:\t set the frame rate, in milliseconds")
    print ("\t--usb3:\t use the USB3 interface (default is USB2)")
    print ("\t--pcie:\t use the PCIE interface (default is USB2)")
    print ("\t--eth:\t use the Ethernet interface (default is USB2)")
    print ("\t-d <deviceNumber>:\t use a different device number than device 0")
    print ("\t--roi <roiFirstRow> <roiNumRows>:\t set the region of interest (first row and number of rows) used by the camera")
    print ("\t--sub <subsampleRowSkip>:\t enable camera image subsampling, specifying the number of rows to skip between each row (e.g. 1 skips every other row so selects every 2nd row, 3 selects every 4th row, etc.")
    print("\t--bit <bit depth>:\t set the camera bit depth, either 10 (default) or 8")
    
def ParseCommandArguments(parameters):
    # read command line arguments
    i=1
    while i < len(sys.argv):
        if sys.argv[i] == "-h" or sys.argv[i] == "--help":
            PrintUsage()
        elif sys.argv[i] == "-i":
            parameters.ipAddress = sys.argv[i+1]
            i += 1
        elif sys.argv[i] == "-r":
            parameters.repeatCount = int(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "-f":
            parameters.frameTime_ms = float(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "--usb3":
            parameters.commInterface = aj.USB3_INTERFACE_TYPE
        elif sys.argv[i] == "--pcie":
            parameters.commInterface = aj.PCIE_INTERFACE_TYPE
        elif sys.argv[i] == "--eth":
            parameters.commInterface = aj.GIGE_INTERFACE_TYPE
        elif sys.argv[i] == "-d":
            parameters.deviceNumber = int(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "--roi":
            parameters.roiFirstRow = int(sys.argv[i+1])
            parameters.roiNumRows = int(sys.argv[i+2])
            i += 2
        elif sys.argv[i] == "--sub":
            parameters.subsampleRowSkip = int(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "--bit":
            parameters.bitDepth = int(sys.argv[i+1])
            i += 1
        else:
            PrintUsage()
            sys.exit(2)
        i += 1

    # debug: show parsed parameters
    print("[example_helper] Parsed parameters:")
    print(f"  commInterface={parameters.commInterface}, deviceNumber={parameters.deviceNumber}")
    print(f"  ipAddress={parameters.ipAddress}, port={parameters.port}")
    print(f"  sequenceID={parameters.sequenceID}, repeatCount={parameters.repeatCount}, frameTime_ms={parameters.frameTime_ms}")

def ConnectToDevice(ajileSystem, parameters):
    ajileSystem.SetConnectionSettingsStr(parameters.ipAddress, parameters.netmask, parameters.gateway, parameters.port)
    ajileSystem.SetCommunicationInterface(parameters.commInterface)
    ajileSystem.SetUSB3DeviceNumber(parameters.deviceNumber)
    # attempt to start system and report result for debugging
    start_result = ajileSystem.StartSystem()
    if start_result != aj.ERROR_NONE:
        print ("Error starting AjileSystem. Did you specify the correct interface with the command line arguments, e.g. \"--usb3\"?")
        print(f"[example_helper] StartSystem returned: {start_result}")
        sys.exit(-1)
    else:
        print(f"[example_helper] AjileSystem started successfully (code {start_result})")

def RunExample(createFunction):
    return RunDmdExample(createFunction)
        
def RunDmdExample(createFunction):

    # read the input command line arguments
    parameters = Parameters()
    ParseCommandArguments(parameters)    

    # connect to the device
    ajileSystem = aj.HostSystem()
    ConnectToDevice(ajileSystem, parameters)

    # create the project
    project = createFunction(parameters.sequenceID, parameters.repeatCount, parameters.frameTime_ms, ajileSystem.GetProject().Components())

    # get the first valid component index which will run the sequence
    sequence, wasFound = project.FindSequence(parameters.sequenceID)
    if not wasFound: sys.exit(-1)
    componentIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(sequence.HardwareType())

    # stop any existing project from running on the device
    ajileSystem.GetDriver().StopSequence(componentIndex)

    # load the project to the device
    ajileSystem.GetDriver().LoadProject(project)
    ajileSystem.GetDriver().WaitForLoadComplete(-1)

    for sequenceID, sequence in project.Sequences().iteritems():

        # if using region-of-interest, switch to 'lite mode' to disable lighting/triggers and allow DMD to run faster
        roiWidthColumns = sequence.SequenceItems()[0].Frames()[0].RoiWidthColumns()
        if roiWidthColumns > 0 and roiWidthColumns < aj.DMD_3000_IMAGE_WIDTH_MAX:
            ajileSystem.GetDriver().SetLiteMode(True, componentIndex)
            
        # run the project
        if parameters.frameTime_ms > 0:
            print ("Starting sequence %d with frame rate %f and repeat count %d" % (sequence.ID(), parameters.frameTime_ms, parameters.repeatCount))

        ajileSystem.GetDriver().StartSequence(sequence.ID(), componentIndex)

        # wait for the sequence to start
        print ("Waiting for sequence %d to start" % (sequence.ID(),))
        while ajileSystem.GetDeviceState(componentIndex).RunState() != aj.RUN_STATE_RUNNING: pass

        if parameters.repeatCount == 0:
            input("Sequence repeating forever. Press Enter to stop the sequence")
            ajileSystem.GetDriver().StopSequence(componentIndex)

        print ("Waiting for the sequence to stop.")
        while ajileSystem.GetDeviceState(componentIndex).RunState() == aj.RUN_STATE_RUNNING: pass

def RunCameraExample(createFunction):

    # read the input command line arguments
    parameters = Parameters()
    ParseCommandArguments(parameters)    

    # connect to the device
    ajileSystem = aj.HostSystem()
    ConnectToDevice(ajileSystem, parameters)

    # create the project
    project = createFunction(parameters.sequenceID, parameters.repeatCount, parameters.frameTime_ms,
                             parameters.bitDepth, parameters.roiFirstRow, parameters.roiNumRows, parameters.subsampleRowSkip,
                             ajileSystem.GetProject().Components())

    # get the first valid component index which will run the sequence
    sequence, wasFound = project.FindSequence(parameters.sequenceID)
    if not wasFound: sys.exit(-1)
    componentIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(sequence.HardwareType())

    # stop any existing project from running on the device
    ajileSystem.GetDriver().StopSequence(componentIndex)

    # load the project to the device
    ajileSystem.GetDriver().LoadProject(project)
    ajileSystem.GetDriver().WaitForLoadComplete(-1)

    for sequenceID, sequence in project.Sequences().iteritems():

        # run the project
        if parameters.frameTime_ms > 0:
            print ("Starting sequence %d with frame rate %f and repeat count %d" % (sequence.ID(), parameters.frameTime_ms, parameters.repeatCount))

        ajileSystem.GetDriver().StartSequence(sequence.ID(), componentIndex)

        # wait for the sequence to start
        print ("Waiting for sequence %d to start" % (sequence.ID(),))
        while ajileSystem.GetDeviceState(componentIndex).RunState() != aj.RUN_STATE_RUNNING: pass

        if parameters.repeatCount == 0:
            print("Sequence repeating forever. Select the Ajile Camera Image window and press any key to stop the sequence.")            
        
            # read out images from the 3D imager, and wait for a user key press or for the sequence to end
            keyPress = -1
            while keyPress < 0 or keyPress == 255:
                # wait until a frame has been captured by the camera
                if not ajileSystem.GetDriver().IsSequenceStatusQueueEmpty():
                    # determine the last frame that was captured
                    sequenceStatus = ajileSystem.GetDriver().GetLatestSequenceStatus()
                    # clear the sequence status history from the queue
                    while not ajileSystem.GetDriver().IsSequenceStatusQueueEmpty():
                        ajileSystem.GetDriver().GetNextSequenceStatus()
                    # retrieve the latest image from the camera
                    ajileImage = ajileSystem.GetDriver().RetrieveImage(aj.RETRIEVE_FROM_FRAME, 0, sequenceStatus.FrameIndex()-1, sequenceStatus.SequenceItemIndex()-1, sequenceStatus.SequenceID())
                    if ajileImage.Width() > 0 and ajileImage.Height() > 0:
                        # convert to a numpy image for display purposes
                        numpyImage = numpy.zeros(shape=(ajileImage.Height(), ajileImage.Width(), 1), dtype=numpy.uint8)
                        ajileImage.WriteToMemory(numpyImage, 8)
                        # display the image, using OpenCV
                        if ajileImage.Height() >= 1024 or ajileImage.Width() > 1024:                    
                            # resize the image so it fits on the screen
                            scaleFactor = 1024 / max(ajileImage.Height(), ajileImage.Width())
                            numpyImage = cv2.resize(numpyImage, (int(scaleFactor*ajileImage.Width()),
                                                                 int(scaleFactor*ajileImage.Height())))
                        cv2.imshow("Ajile Camera Image", numpyImage)
                    else:
                        print("Timeout waiting for camera image.")
                keyPress = cv2.waitKey(30)

            ajileSystem.GetDriver().StopSequence(componentIndex)

        print ("Waiting for the sequence to stop.")
        while ajileSystem.GetDeviceState(componentIndex).RunState() == aj.RUN_STATE_RUNNING: pass

        # read out all camera images in the sequence, and save them to file
        for sequenceItem in sequence.SequenceItems():
            for frame in sequenceItem.Frames():
                print("Reading image " + str(frame.ImageID()))
                ajileImage = ajileSystem.GetDriver().RetrieveImage(aj.RETRIEVE_FROM_IMAGE, frame.ImageID())
                if ajileImage.Width() > 0 and ajileImage.Height() > 0:
                    outputBitDepth = ajileImage.BitDepth()
                    if ajileImage.BitDepth() > 8:
                        outputBitDepth = 16 # saving 10-bit images as 16-bit files
                    ajileImage.WriteToFile("image_" + str(frame.ImageID()) + ".png", outputBitDepth)
                else:
                    print("Timeout waiting for camera image.")

def RunCameraDmdExample(createFunction):

    # read the input command line arguments
    parameters = Parameters()
    ParseCommandArguments(parameters)    

    # connect to the device
    ajileSystem = aj.HostSystem()
    ConnectToDevice(ajileSystem, parameters)

    # create the project
    project = createFunction(parameters.sequenceID, parameters.repeatCount, parameters.frameTime_ms,
                             parameters.bitDepth, parameters.roiFirstRow, parameters.roiNumRows, parameters.subsampleRowSkip,
                             ajileSystem.GetProject().Components())

    # get the first valid component index which will run each sequence
    dmdSequence, wasFound = project.FindSequence(parameters.sequenceID)
    if not wasFound: sys.exit(-1)
    dmdComponentIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(dmdSequence.HardwareType())
   
    cameraSequence, wasFound = project.FindSequence(parameters.sequenceID+1)
    if not wasFound: sys.exit(-1)
    cameraComponentIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(cameraSequence.HardwareType())

    # stop any existing project from running on the device
    ajileSystem.GetDriver().StopSequence(dmdComponentIndex)
    ajileSystem.GetDriver().StopSequence(cameraComponentIndex)

    # load the project to the device
    ajileSystem.GetDriver().LoadProject(project)
    ajileSystem.GetDriver().WaitForLoadComplete(-1)

    # first run the DMD sequence, since it will be waiting for the camera trigger
    ajileSystem.GetDriver().StartSequence(dmdSequence.ID(), dmdComponentIndex)
    # wait for the sequence to start
    print ("Waiting for DMD sequence %d to start" % (dmdSequence.ID(),))
    while ajileSystem.GetDeviceState(dmdComponentIndex).RunState() != aj.RUN_STATE_RUNNING: pass

    # then run the camera sequence
    ajileSystem.GetDriver().StartSequence(cameraSequence.ID(), cameraComponentIndex)

    if parameters.repeatCount == 0:
        print("Sequence repeating forever. Select the Ajile Camera Image window and press any key to stop the sequence.")

        # read out images from the 3D imager, and wait for a user key press or for the sequence to end
        keyPress = -1
        while keyPress < 0 or keyPress == 255:
            # wait until a frame has been captured by the camera
            if not ajileSystem.GetDriver().IsSequenceStatusQueueEmpty(cameraComponentIndex):
                # determine the last frame that was captured
                sequenceStatus = ajileSystem.GetDriver().GetLatestSequenceStatus(cameraComponentIndex)
                # clear the sequence status history from the queue
                while not ajileSystem.GetDriver().IsSequenceStatusQueueEmpty(cameraComponentIndex):
                    ajileSystem.GetDriver().GetNextSequenceStatus(cameraComponentIndex)
                # retrieve the latest image from the camera
                ajileImage = ajileSystem.GetDriver().RetrieveImage(aj.RETRIEVE_FROM_FRAME, 0, sequenceStatus.FrameIndex()-1, sequenceStatus.SequenceItemIndex()-1, sequenceStatus.SequenceID())
                if ajileImage.Width() > 0 and ajileImage.Height() > 0:
                    # convert to a numpy image for display purposes
                    numpyImage = numpy.zeros(shape=(ajileImage.Height(), ajileImage.Width(), 1), dtype=numpy.uint8)
                    ajileImage.WriteToMemory(numpyImage, 8)
                    # display the image, using OpenCV
                    if ajileImage.Height() >= 1024 or ajileImage.Width() > 1024:                    
                        # resize the image so it fits on the screen
                        scaleFactor = 1024 / max(ajileImage.Height(), ajileImage.Width())
                        numpyImage = cv2.resize(numpyImage, (int(scaleFactor*ajileImage.Width()),
                                                             int(scaleFactor*ajileImage.Height())))
                    cv2.imshow("Ajile Camera Image", numpyImage)
                else:
                    print("Timeout waiting for camera image.")        
            keyPress = cv2.waitKey(100)

        print ("Stopping the camera sequence.")
        ajileSystem.GetDriver().StopSequence(cameraComponentIndex)
        print ("Waiting for the camera sequence to stop.")
        while ajileSystem.GetDeviceState(cameraComponentIndex).RunState() == aj.RUN_STATE_RUNNING: pass
        print ("Stopping the DMD sequence.")
        ajileSystem.GetDriver().StopSequence(dmdComponentIndex)

    print ("Waiting for the sequences to stop.")
    while ajileSystem.GetDeviceState(cameraComponentIndex).RunState() == aj.RUN_STATE_RUNNING: pass
    while ajileSystem.GetDeviceState(dmdComponentIndex).RunState() == aj.RUN_STATE_RUNNING: pass

    # read out all camera images in the sequence, and save them to file
    imageNumber = 0
    for sequenceItem in cameraSequence.SequenceItems():
        for frame in sequenceItem.Frames():
            print("Reading image number " + str(imageNumber) + " with ID " + str(frame.ImageID()))
            ajileImage = ajileSystem.GetDriver().RetrieveImage(aj.RETRIEVE_FROM_IMAGE, frame.ImageID())
            if ajileImage.Width() > 0 and ajileImage.Height() > 0:
                outputBitDepth = ajileImage.BitDepth()
                if ajileImage.BitDepth() > 8:
                    outputBitDepth = 16 # saving 10-bit images as 16-bit files
                ajileImage.WriteToFile("image_" + str(imageNumber) + ".png", outputBitDepth)
                imageNumber += 1
            else:
                print("Timeout waiting for camera image.")
        
def AddPreviewImage(project, npImage, imageID, previewImageID, imageName, dstBitDepth=0, dstNumChan=0):
    previewImage = aj.Image(previewImageID)
    previewImage.SetImageName(imageName)
    previewImage.ReadFromMemory(npImage, 8, aj.ROW_MAJOR_ORDER, 0, 0, dstNumChan, dstBitDepth, aj.UNDEFINED_MAJOR_ORDER)
    project.AddPreviewImage(previewImage, imageID)

def AddPreviewImageFile(project, filename, imageID, previewImageID, dstBitDepth=0, dstNumChan=0):

    imageName = os.path.splitext(os.path.basename(filename))[0]
    previewImage = aj.Image(previewImageID)
    previewImage.SetImageName(imageName)
    previewImage.ReadFromFile(filename, 0, 0, dstNumChan, dstBitDepth, aj.ROW_MAJOR_ORDER)
    project.AddPreviewImage(previewImage, imageID)
