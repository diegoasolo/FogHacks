import ajiledriver as aj
import cv2
import numpy
import math

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# helper function which creates a set of binary gray code pattern images
def GenerateGrayCodes(width, height):
    # Determine number of required codes and row/column offsets.
    numColumns = int(math.ceil(math.log(width,2)))
    columnShift = int(math.floor((math.pow(2.0,numColumns)-width)/2))

    numRows = int(math.ceil(math.log(height,2)))
    rowShift = int(math.floor((math.pow(2.0,numRows)-height)/2))   

    # Allocate Gray codes.
    grayCodeImages = []
    for i in range(numColumns+numRows+1):
        grayCodeImages.append(numpy.zeros(shape=(height, width, 1), dtype=numpy.uint8))

    # Define first code as a white image.
    grayCodeImages[0].fill(255)

    # Define Gray codes for projector columns.
    for c in range(width):
        for i in range(numColumns):
            imageIndex = i+1
            if i>0:
                grayCodeImages[imageIndex][0, c] = (((c+columnShift) >> (numColumns-i-1)) & 1) ^ (((c+columnShift) >> (numColumns-i)) & 1)
            else: 
                grayCodeImages[imageIndex][0, c] = (((c+columnShift) >> (numColumns-i-1)) & 1)
            grayCodeImages[imageIndex][0, c] *= 255
            cv2.rectangle(grayCodeImages[imageIndex], (c,0), (c,height), int(grayCodeImages[imageIndex][0, c]), -1)

    # Define Gray codes for projector rows.
    for r in range(height):
        for i in range(numRows):
            imageIndex = i+numColumns+1
            if i>0:
                grayCodeImages[imageIndex][r, 0] = (((r+rowShift) >> (numRows-i-1)) & 1)^(((r+rowShift) >> (numRows-i)) & 1)
            else:
                grayCodeImages[imageIndex][r, 0] = (((r+rowShift) >> (numRows-i-1)) & 1)
            grayCodeImages[imageIndex][r, 0] *= 255
            cv2.rectangle(grayCodeImages[imageIndex], (0,r), (width,r), int(grayCodeImages[imageIndex][r, 0]), -1)

    return grayCodeImages

# creates an Ajile project and returns in
def CreateDmdSequence(project, sequenceID, sequenceRepeatCount, frameTime_ms):

    # generate a list of gray code images (which are numpy matrices)
    grayCodeImages = GenerateGrayCodes(aj.DMD_IMAGE_WIDTH_MAX, aj.DMD_IMAGE_HEIGHT_MAX)
    
    # create the images from the numpy gray code images and add them to our project
    imageCount = 1
    for grayCodeImage in grayCodeImages:
        image = aj.Image(imageCount)
        imageCount += 1
        image.ReadFromMemory(grayCodeImage, 8, aj.ROW_MAJOR_ORDER, aj.DMD_4500_DEVICE_TYPE)
        project.AddImage(image)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        example_helper.AddPreviewImage(project, grayCodeImage, image.ID(), image.ID(), "graycode_" + str(image.ID()), 1)

    numImages = len(grayCodeImages)
    
    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, "DMD - " + project.Name(), aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create a single sequence item, which all the frames will be added to
    project.AddSequenceItem(aj.SequenceItem(sequenceID, 1))

    # create the frames and add them to the project, which adds them to the last sequence item
    for i in range(numImages):
        frame = aj.Frame()
        frame.SetSequenceID(sequenceID)
        frame.SetImageID(i+1)
        frame.SetFrameTimeMSec(frameTime_ms)
        project.AddFrame(frame)

def CreateCameraSequence(project, firstImageID, numImages, sequenceID, sequenceRepeatCount, frameTime_ms, bitDepth, roiFirstRow, roiNumRows, subsampleRowSkip):    

    cameraIndex = project.GetComponentIndexWithDeviceType(aj.CMV_4000_MONO_DEVICE_TYPE)
    if cameraIndex < 0: cameraIndex = project.GetComponentIndexWithDeviceType(aj.CMV_2000_MONO_DEVICE_TYPE)
    
    imageWidth = project.Components()[cameraIndex].NumColumns()
    imageHeight = project.Components()[cameraIndex].NumRows()
    deviceType = project.Components()[cameraIndex].DeviceType().HardwareType()
    
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
    project.AddSequence(aj.Sequence(sequenceID, "Camera - " + project.Name(), deviceType, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

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

# creates an Ajile project and returns it
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, bitDepth=aj.CMV4000_BIT_DEPTH, roiFirstRow=0, roiNumRows=aj.CMV4000_IMAGE_HEIGHT_MAX, subsampleRowSkip=0, components=None):

    projectName = "camera_dmd_binary_example"
    if frameTime_ms < 0:
        frameTime_ms = 100
    numImages = 10
    firstImageID = 1
    
    # create a new project
    project = aj.Project(projectName)
    # set the project components and the image size based on the DMD type
    if components is not None:
        project.SetComponents(components)        
    else:
        # create default components if none are passed in
        controllerComponent = aj.Component()
        controllerComponent.CreateComponentForDevice(aj.DeviceDescriptor(aj.DMD_CAMERA_CONTROLLER_DEVICE_TYPE))
        dmdComponent = aj.Component()
        dmdComponent.CreateComponentForDevice(aj.DeviceDescriptor(aj.DMD_4500_DEVICE_TYPE))        
        cameraComponent = aj.Component()
        cameraComponent.CreateComponentForDevice(aj.DeviceDescriptor(aj.CMV_4000_MONO_DEVICE_TYPE))
        project.AddComponent(controllerComponent)
        project.AddComponent(dmdComponent)
        project.AddComponent(cameraComponent)

    cameraIndex = project.GetComponentIndexWithDeviceType(aj.CMV_4000_MONO_DEVICE_TYPE)
    if cameraIndex < 0: cameraIndex = project.GetComponentIndexWithDeviceType(aj.CMV_2000_MONO_DEVICE_TYPE)
    dmdIndex = project.GetComponentIndexWithDeviceType(aj.DMD_4500_DEVICE_TYPE)
    if dmdIndex < 0: dmdIndex = project.GetComponentIndexWithDeviceType(aj.DMD_3000_DEVICE_TYPE)
        
    # add a trigger rule between the camera and DMD
    cameraFrameStartedToDmdFrameBegin = aj.TriggerRule()
    cameraFrameStartedToDmdFrameBegin.AddTriggerFromDevice(aj.TriggerRulePair(cameraIndex, aj.FRAME_STARTED))
    cameraFrameStartedToDmdFrameBegin.SetTriggerToDevice(aj.TriggerRulePair(dmdIndex, aj.START_FRAME))
    # add the trigger rule to the project
    project.AddTriggerRule(cameraFrameStartedToDmdFrameBegin)
        
    # create the DMD sequence
    CreateDmdSequence(project, sequenceID, sequenceRepeatCount, frameTime_ms)

    # get the number of images and the starting image ID for the camera based on the DMD images
    numImages = len(project.Images().keys())
    firstImageID = sorted(project.Images().keys())[-1] + 1

    # create the camera sequence
    CreateCameraSequence(project, firstImageID, numImages, sequenceID+1, sequenceRepeatCount, frameTime_ms, bitDepth, roiFirstRow, roiNumRows, subsampleRowSkip)
        
    return project

if __name__ == "__main__":

    example_helper.RunCameraDmdExample(CreateProject)
