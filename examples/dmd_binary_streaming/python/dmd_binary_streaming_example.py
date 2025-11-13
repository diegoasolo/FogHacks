import ajiledriver as aj
import cv2
import numpy

def RunStreaming():

    # default connection settings
    ipAddress = "192.168.200.1"
    netmask = "255.255.255.0"
    gateway = "0.0.0.0"
    port = 5005
    commInterface = aj.USB2_INTERFACE_TYPE

    # default sequence settings
    frameTime_ms = 10 # frame time in milliseconds
    sequenceID = 1
    repeatCount = 0
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
        elif sys.argv[i] == "--pcie":
            commInterface = aj.PCIE_INTERFACE_TYPE
        elif sys.argv[i] == "--eth":
            commInterface = aj.GIGE_INTERFACE_TYPE
        else:
            print ("Usage: " + sys.argv[0] + ' [-i <IP address>] [-f <frame rate in ms>] [--usb|--eth|--pcie]')
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
    
    # stop any existing project from running on the device
    driver.StopSequence(dmdIndex)

    print ("Waiting for the sequence to stop.")
    while ajileSystem.GetDeviceState(dmdIndex).RunState() != aj.RUN_STATE_STOPPED: pass

    # set the project components and the image size based on the DMD type
    imageWidth = ajileSystem.GetProject().Components()[dmdIndex].NumColumns()
    imageHeight = ajileSystem.GetProject().Components()[dmdIndex].NumRows()
    deviceType = ajileSystem.GetProject().Components()[dmdIndex].DeviceType().HardwareType()
    
    # create the streaming sequence
    project.AddSequence(aj.Sequence(sequenceID, "dmd_binary_streaming_example", deviceType, aj.SEQ_TYPE_STREAM, 1, aj.SequenceItemList(), aj.RUN_STATE_PAUSED))

    # load the project
    driver.LoadProject(project)
    driver.WaitForLoadComplete(-1)

    # local variables used to generate DMD images
    dmdImageSize = imageWidth * imageHeight / 8
    maxStreamingSequenceItems = 100
    frameNum = 0
    frameProcessed = 0
    rectHeight = 100
    rectWidth = 1
    npImage = numpy.zeros(shape=(aj.DMD_IMAGE_HEIGHT_MAX, aj.DMD_IMAGE_WIDTH_MAX, 1), dtype=numpy.uint8)

    keyPress = '0'
    while (keyPress != 'q' and keyPress != 'Q') and (repeatCount == 0 or frameProcessed < repeatCount):
        if not driver.IsSequenceStatusQueueEmpty(dmdIndex):
            seqStatus = driver.GetNextSequenceStatus(dmdIndex);
        if driver.GetNumStreamingSequenceItems(dmdIndex) < maxStreamingSequenceItems:
            # generate a new image with OpenCV
            myNum = frameNum
            npImage = numpy.zeros(shape=(aj.DMD_IMAGE_HEIGHT_MAX, aj.DMD_IMAGE_WIDTH_MAX, 1), dtype=numpy.uint8)
            frameStr = "{0:0{1}x}".format((frameNum & 0xffff0000) >> 16,4)
            cv2.putText(npImage, frameStr, (50, 450),  cv2.FONT_HERSHEY_TRIPLEX, 10, 255, 10)
            frameStr = "{0:0{1}x}".format(frameNum & 0x0000ffff,4)
            cv2.putText(npImage, frameStr, (50, 700),  cv2.FONT_HERSHEY_TRIPLEX, 10, 255, 10)
            frameStr = "{0:0{1}x}".format(frameNum, 8)
            cv2.putText(npImage, frameStr, (10, 1100), cv2.FONT_HERSHEY_TRIPLEX, 5, 255, 5)
            cv2.rectangle(npImage, (0, 0), (rectWidth, rectHeight), 255, -1)
            if imageWidth != npImage.shape[0] or imageHeight != npImage.shape[1]:
                npImage = cv2.resize(npImage, (imageWidth, imageHeight))
                npImage = numpy.expand_dims(npImage, axis=2)
            # convert the OpenCV image to the Ajile DMD image format
            streamingImage = aj.Image()
            streamingImage.ReadFromMemory(npImage, 8, aj.ROW_MAJOR_ORDER, deviceType)
            # create a new sequence item and frame to be streamed
            streamingSeqItem = aj.SequenceItem(sequenceID, 1)
            streamingFrame = aj.Frame( sequenceID, 0, aj.FromMSec(frameTime_ms), 0, 0, imageWidth, imageHeight)
            # attach the next streaming image to the streaming frame
            streamingFrame.SetStreamingImage(streamingImage)
            frameNum += 1
            frameProcessed += 1
            # add the frame to the streaming sequence item
            streamingSeqItem.AddFrame(streamingFrame)
            if rectWidth == aj.DMD_IMAGE_WIDTH_MAX - 1:
                rectWidth = 1
            else:
                rectWidth += 1
            # send the streaming sequence item to the device
            driver.AddStreamingSequenceItem(streamingSeqItem, dmdIndex)
        else:
            # when enough images have been preloaded start the streaming sequence
            if ajileSystem.GetDeviceState(dmdIndex).RunState() == aj.RUN_STATE_STOPPED:
                driver.StartSequence(sequenceID, dmdIndex)
            # check for a keypress to quit
            cv2.imshow("AJILE Streaming DMD Example", npImage)
            keyPress = cv2.waitKey(10)
            keyPress = chr(keyPress%256) if keyPress%256 < 128 else '?'

    # stop the device when we are done
    driver.StopSequence(dmdIndex)
    print ("Waiting for the sequence to stop.\n")
    while ajileSystem.GetDeviceState(dmdIndex).RunState() == aj.RUN_STATE_RUNNING: pass

    return 0

if __name__ == "__main__":

    import sys
    sys.path.insert(0, "../../common/python/")

    RunStreaming()
