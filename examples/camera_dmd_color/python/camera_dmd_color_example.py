import ajiledriver as aj
import cv2
import numpy
import math

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns in
def CreateDmdSequence(project, sequenceID, sequenceRepeatCount, frameTime_ms):

    currentPath = os.path.dirname(os.path.realpath(__file__))
    filenames = [currentPath + "/../../images/dog.jpg", 
                 currentPath + "/../../images/plants.jpg"]

    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, "DMD - " + project.Name(), aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create the images
    nextImageID = 1
    for filename in filenames:

        # create a sequence item to display the 8 bitplanes of the grayscale image with the default minimum timing
        sequenceItem = aj.SequenceItem(sequenceID, 1)
        imageBitplanes = aj.ImageList()
        # we subtract the DMD inter-frame overhead time from the color display timing so that the projected image will not be slower than the camera exposure
        colorDisplayTime = aj.FromMSec(frameTime_ms) - 24 * aj.FromSec(aj.DMD_FOT_TIME_CONST)
        project.CreateColorSequenceItemWithTime_FromFile(sequenceItem, imageBitplanes, filename, nextImageID, colorDisplayTime)
        # add the image bitplanes to the project
        project.AddImages(imageBitplanes);
        # add the sequence item to the project
        project.AddSequenceItem(sequenceItem)
        # update the image ID for the next set of images
        nextImageID += len(imageBitplanes)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        for image in imageBitplanes:
            example_helper.AddPreviewImageFile(project, filename, image.ID(), imageBitplanes[0].ID())

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

    projectName = "camera_dmd_color_example"
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
    cameraFrameStartedToDmdFrameBegin.SetTriggerToDevice(aj.TriggerRulePair(dmdIndex, aj.START_SEQUENCE_ITEM))
    # add the trigger rule to the project
    project.AddTriggerRule(cameraFrameStartedToDmdFrameBegin)

    # create the DMD sequence
    CreateDmdSequence(project, sequenceID, sequenceRepeatCount, frameTime_ms)

    # get the number of images and the starting image ID for the camera based on the DMD sequence items
    # (remember each color image consists of 8 24-bit images, so we much count the number of sequence items not the number of images)
    numImages = len(project.Sequences()[sequenceID].SequenceItems())
    firstImageID = sorted(project.Images().keys())[-1] + 1

    # create the camera sequence
    CreateCameraSequence(project, firstImageID, numImages, sequenceID+1, sequenceRepeatCount, frameTime_ms, bitDepth, roiFirstRow, roiNumRows, subsampleRowSkip)
        
    return project

if __name__ == "__main__":

    example_helper.RunCameraDmdExample(CreateProject)
