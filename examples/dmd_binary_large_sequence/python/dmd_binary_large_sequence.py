import ajiledriver as aj
import cv2
import numpy
import sys
import time

def RunProject():

    # default connection settings
    ipAddress = "192.168.200.1"
    netmask = "255.255.255.0"
    gateway = "0.0.0.0"
    port = 5005
    commInterface = aj.USB2_INTERFACE_TYPE

    # default sequence settings
    frameTime_ms = 10 # frame time in milliseconds
    repeatCount = 0
    sequenceID = 1

    # read command line arguments
    i=1
    while i < len(sys.argv):
        if sys.argv[i] == "-i":
            ipAddress = sys.argv[i+1]
            i += 1
        elif sys.argv[i] == "-f":
            frameTime_ms = float(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "--usb3":
            commInterface = aj.USB3_INTERFACE_TYPE
        elif sys.argv[i] == '-r':
            repeatCount = int(sys.argv[i+1])
            i += 1
        else:
            print ("Usage: " + sys.argv[0] + ' [-i <IP address>] [-f <frame rate in ms>]')
            sys.exit(2)
        i += 1

    # connect to the device
    ajileSystem = aj.HostSystem()
    driver = ajileSystem.GetDriver()
    ajileSystem.SetConnectionSettingsStr(ipAddress, netmask, gateway, port)
    ajileSystem.SetCommunicationInterface(commInterface)
    if ajileSystem.StartSystem() != aj.ERROR_NONE:
        print ("Error starting AjileSystem.")
        sys.exit(-1)

    # create the project
    project = aj.Project("dmd_binary_streaming_example")
    # get the connected devices from the project structure
    project.SetComponents(ajileSystem.GetProject().Components())

    dmdIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(aj.DMD_4500_DEVICE_TYPE)
    if dmdIndex < 0:
        dmdIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(aj.DMD_3000_DEVICE_TYPE)

    # first reset the image memory to minimal value
    driver.LoadImageStorageSize(0x00001000, 0, -1)
    driver.LoadImageStorageSize(0x00001000, dmdIndex, -1)        

    time.sleep(1)
    
    # update the component sizes
    # component 0 holds the 'preloaded' images
    controllerComponent = project.Components()[0]
    controllerComponent.SetImageMemorySize(0x1f000000)
    project.SetComponent(0, controllerComponent)

    # component 1 holds the 'streaming' images
    dmdComponent = project.Components()[dmdIndex]
    dmdComponent.SetImageMemorySize(0x01000000)
    project.SetComponent(1, dmdComponent)

    # update the image memory size
    driver.LoadImageStorageSize(controllerComponent.ImageMemorySize(), 0, -1)
    driver.LoadImageStorageSize(dmdComponent.ImageMemorySize(), dmdIndex, -1)

    time.sleep(1)
    
    # stop any existing project from running on the device
    driver.StopSequence(dmdIndex)

    print ("Waiting for the sequence to stop.")
    while ajileSystem.GetDeviceState(dmdIndex).RunState() != aj.RUN_STATE_STOPPED: pass

    # set the project components and the image size based on the DMD type
    imageWidth = ajileSystem.GetProject().Components()[dmdIndex].NumColumns()
    imageHeight = ajileSystem.GetProject().Components()[dmdIndex].NumRows()
    deviceType = ajileSystem.GetProject().Components()[dmdIndex].DeviceType().HardwareType()
    
    # create the streaming sequence
    project.AddSequence(aj.Sequence(sequenceID, "dmd_binary_streaming_example", deviceType, aj.SEQ_TYPE_PRELOAD, repeatCount, aj.SequenceItemList(), aj.RUN_STATE_PAUSED))

    # create a single sequence item, which all the frames will be added to
    project.AddSequenceItem(aj.SequenceItem(sequenceID, 1))

    print ("Generating Images")
    numImages = 4000
    rectHeight = 100
    rectWidth = 1
    for i in range(numImages):
                
        # generate a new image with OpenCV
        npImage = numpy.zeros(shape=(aj.DMD_IMAGE_HEIGHT_MAX, aj.DMD_IMAGE_WIDTH_MAX, 1), dtype=numpy.uint8)
        frameStr = "{0:0{1}x}".format((i & 0xffff0000) >> 16,4)
        cv2.putText(npImage, frameStr, (50, 450),  cv2.FONT_HERSHEY_TRIPLEX, 10, 255, 10)
        frameStr = "{0:0{1}x}".format(i & 0x0000ffff,4)
        cv2.putText(npImage, frameStr, (50, 700),  cv2.FONT_HERSHEY_TRIPLEX, 10, 255, 10)
        frameStr = "{0:0{1}x}".format(i, 8)
        cv2.putText(npImage, frameStr, (10, 1100), cv2.FONT_HERSHEY_TRIPLEX, 5, 255, 5)
        cv2.rectangle(npImage, (0, 0), (rectWidth, rectHeight), 255, -1)
        if imageWidth != npImage.shape[0] or imageHeight != npImage.shape[1]:
            npImage = cv2.resize(npImage, (imageWidth, imageHeight))
            npImage = numpy.expand_dims(npImage, axis=2)
        # convert the OpenCV image to the Ajile DMD image format
        ajImage = aj.Image(i+1)
        ajImage.ReadFromMemory(npImage, 8, aj.ROW_MAJOR_ORDER, deviceType)
        project.AddImage(ajImage)
        # create a new frame which displays the image
        frame = aj.Frame( sequenceID, i+1, aj.FromMSec(frameTime_ms), 0, 0, imageWidth, imageHeight)
        # add the frame to the project
        project.AddFrame(frame)
        if rectWidth == aj.DMD_IMAGE_WIDTH_MAX - 1:
            rectWidth = 1
        else:
            rectWidth += 1    

    # get the first valid component index which will run the sequence
    sequence, wasFound = project.FindSequence(sequenceID)
    if not wasFound: sys.exit(-1)
    componentIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(sequence.HardwareType())

    # stop any existing project from running on the device
    ajileSystem.GetDriver().StopSequence(componentIndex)

    #errorString = project.VerifySequenceStr(sequenceID, dmdIndex, False)
    #print (errorString)
    
    # load the project to the device
    print ("Loading project")
    ajileSystem.GetDriver().LoadProject(project)
    ajileSystem.GetDriver().WaitForLoadComplete(-1)
    
    # run the project
    ajileSystem.GetDriver().StartSequence(sequenceID, componentIndex)

    # wait for the sequence to start
    print ("Waiting for sequence %d to start" % (sequence.ID(),))
    while ajileSystem.GetDeviceState(componentIndex).RunState() != aj.RUN_STATE_RUNNING: pass

    if repeatCount == 0:
        if sys.version_info < (3, 0):
            raw_input("Sequence repeating forever. Press Enter to stop the sequence")
        else:
            input("Sequence repeating forever. Press Enter to stop the sequence")
        ajileSystem.GetDriver().StopSequence(componentIndex)

    frameNum = 0
    while ajileSystem.GetDeviceState(componentIndex).RunState() == aj.RUN_STATE_RUNNING:
        if repeatCount > 0:
            if not ajileSystem.GetDriver().IsSequenceStatusQueueEmpty(componentIndex):
                seqStatus = ajileSystem.GetDriver().GetNextSequenceStatus(componentIndex)
                frameNum += 4
                if frameNum >= (repeatCount * numImages):
                    print("Sequence completed after %d repetitions. Stopping." % repeatCount)
                    ajileSystem.GetDriver().StopSequence(componentIndex)
                    break

    print ("Waiting for the sequence to stop.")
    while ajileSystem.GetDeviceState(componentIndex).RunState() == aj.RUN_STATE_RUNNING: pass

if __name__ == "__main__":

    RunProject()
