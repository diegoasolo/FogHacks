import sys
import ajiledriver as aj
import os.path
import cv2
import numpy

sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# Python 2.x - 3.x workaround
try:
    input = raw_input
except NameError:
    pass

# creates an Ajile project and returns it
def CreateProject(sequenceID=1, frameTime_ms=-1, bitDepth=aj.CMV4000_BIT_DEPTH, roiFirstRow=0, roiNumRows=aj.CMV4000_IMAGE_HEIGHT_MAX, subsampleRowSkip=0, components=None):

    projectName = "camera_acquire_example"
    if frameTime_ms < 0:
        frameTime_ms = 10
    numImages = 100
    firstImageID = 1
    sequenceRepeatCount = 1
    
    # create a new project
    project = aj.Project(projectName)
    # set the project components and the image size based on the DMD type
    if components is not None:
        project.SetComponents(components)
        cameraIndex = project.GetComponentIndexWithDeviceType(aj.CMV_4000_MONO_DEVICE_TYPE)
        if cameraIndex < 0: cameraIndex = project.GetComponentIndexWithDeviceType(aj.CMV_2000_MONO_DEVICE_TYPE)
        imageWidth = components[cameraIndex].NumColumns()
        imageHeight = components[cameraIndex].NumRows()
        deviceType = components[cameraIndex].DeviceType().HardwareType()
    else:
        imageWidth = aj.CMV4000_IMAGE_WIDTH_MAX
        imageHeight = aj.CMV4000_IMAGE_HEIGHT_MAX
        deviceType = aj.CMV_4000_MONO_DEVICE_TYPE

    # check the bit depth parameter
    if bitDepth != 10 and bitDepth != 8:
        print("Invalid bit depth selected.")
        bitDepth = aj.CMV4000_BIT_DEPTH
    # check to make sure the region of interest arguments are acceptable
    if roiFirstRow >= imageHeight:
        print("Invalid ROI start row selected.")
        roiFirstRow = 0
    if roiFirstRow + roiNumRows > imageHeight:
        print("Invalid ROI number of rows selected.")
        roiNumRows = imageHeight - roiFirstRow
    # check the subsample row skip parameter
    if subsampleRowSkip >= roiNumRows:
        print("Invalid subsample rows selected.")
        subsampleRowSkip = 0
    if subsampleRowSkip > 0:
        # total number of rows in the image is reduced by the number of rows skipped
        roiNumRows = int(roiNumRows / (subsampleRowSkip+1))
    
    # create an image buffer for each of the images that we want to capture in the sequence
    for i in range(numImages):
        image = aj.Image(firstImageID + i)
        image.SetImagePropertiesForDevice(deviceType)
        image.SetBitDepth(bitDepth)
        image.SetHeight(roiNumRows)
        project.AddImage(image)
    
    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, projectName, deviceType, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create a single sequence item, which all the frames will be added to
    project.AddSequenceItem(aj.SequenceItem(sequenceID, 1))

    # create the frames and add them to the project, which adds them to the last sequence item
    for i in range(numImages):
        frame = aj.Frame()
        frame.SetSequenceID(sequenceID)
        frame.SetImageID(firstImageID+i)
        frame.SetFrameTimeMSec(frameTime_ms)
        frame.SetRoiOffsetRows(roiFirstRow)
        frame.SetRoiHeightRows(roiNumRows)
        if subsampleRowSkip > 0:
            frame.AddImagingParameter(aj.KeyValuePair(aj.IMAGING_PARAM_SUBSAMPLE_NUMROWS, subsampleRowSkip))
        project.AddFrame(frame)

    return project

def RunCameraAcquireExample():

    # read the input command line arguments
    parameters = example_helper.Parameters()
    example_helper.ParseCommandArguments(parameters)    

    # connect to the device
    ajileSystem = aj.HostSystem()
    example_helper.ConnectToDevice(ajileSystem, parameters)

    # create the project
    project = CreateProject(parameters.sequenceID, parameters.frameTime_ms,
                             parameters.bitDepth, parameters.roiFirstRow, parameters.roiNumRows, parameters.subsampleRowSkip,
                             ajileSystem.GetProject().Components())

    # get the first valid component index which will run the sequence
    sequence, wasFound = project.FindSequence(parameters.sequenceID)
    if not wasFound: sys.exit(-1)
    cameraIndex = ajileSystem.GetProject().GetComponentIndexWithDeviceType(sequence.HardwareType())
    
    # stop any existing project from running on the device
    ajileSystem.GetDriver().StopSequence(cameraIndex)

    # load the project to the device
    ajileSystem.GetDriver().LoadProject(project)
    ajileSystem.GetDriver().WaitForLoadComplete(-1)

    numImages = len(project.Images().keys())
    # acquire all numImages images from the camera, which means numImages will automatically be sent to the host when they are captured
    ajileSystem.GetDriver().AcquireImages(numImages, cameraIndex);
    
    ajileSystem.GetDriver().StartSequence(parameters.sequenceID, cameraIndex)

    # wait for the sequence to start
    print ("Waiting for sequence %d to start" % (parameters.sequenceID,))
    while ajileSystem.GetDeviceState(cameraIndex).RunState() != aj.RUN_STATE_RUNNING: pass
    
    print ("Waiting for the sequence to stop.")
    while ajileSystem.GetDeviceState(cameraIndex).RunState() == aj.RUN_STATE_RUNNING: pass

    # get the acquired images from the acquired image (FIFO) queue, and save them to file
    imagesRead = 0
    while imagesRead < numImages:
        if not ajileSystem.GetDriver().IsAcquiredImageQueueEmpty(cameraIndex):            
            ajileImage = ajileSystem.GetDriver().GetNextAcquiredImage(cameraIndex)
            print("Read image " + str(imagesRead) + " with ID " + str(ajileImage.ID()))
            if ajileImage.Size() == ajileImage.Width() * ajileImage.Height() * ajileImage.BitDepth() / 8:
                outputBitDepth = ajileImage.BitDepth()
                if ajileImage.BitDepth() > 8:
                    outputBitDepth = 16 # saving 10-bit images as 16-bit files
                ajileImage.WriteToFile("image_" + str(imagesRead) + ".png", outputBitDepth)
            else:
                print("Image %d bad size, %d." % (imagesRead, ajileImage.Size()))
            # after it is saved we are done with this acquired image, so pop it from the queue to go onto the next one
            ajileSystem.GetDriver().PopNextAcquiredImage(cameraIndex)
            imagesRead += 1

if __name__ == "__main__":

    RunCameraAcquireExample()

                      
