import ajiledriver as aj
import cv2
import numpy
import math

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns it
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, bitDepth=aj.CMV4000_BIT_DEPTH, roiFirstRow=0, roiNumRows=aj.CMV4000_IMAGE_HEIGHT_MAX, subsampleRowSkip=0, components=None):

    projectName = "camera_triggerout_example"
    if frameTime_ms < 0:
        frameTime_ms = 100
    numImages = 10
    firstImageID = 1
    
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
        controllerComponent = aj.Component()
        controllerComponent.CreateComponentForDevice(aj.DeviceDescriptor(aj.DMD_CAMERA_CONTROLLER_DEVICE_TYPE))
        project.AddComponent(controllerComponent)
        cameraComponent = aj.Component()
        cameraComponent.CreateComponentForDevice(aj.DeviceDescriptor(aj.CMV_4000_MONO_DEVICE_TYPE))
        project.AddComponent(cameraComponent)

    # get the component indices
    for index, component in enumerate(project.Components()):
        deviceType = component.DeviceType().HardwareType()
        if deviceType == aj.AJILE_CONTROLLER_DEVICE_TYPE or \
           deviceType == aj.AJILE_2PORT_CONTROLLER_DEVICE_TYPE or \
           deviceType == aj.AJILE_3PORT_CONTROLLER_DEVICE_TYPE or \
           deviceType == aj.DMD_CAMERA_CONTROLLER_DEVICE_TYPE:
            controllerIndex = index
        if deviceType == aj.CMV_4000_MONO_DEVICE_TYPE or \
           deviceType == aj.CMV_2000_MONO_DEVICE_TYPE:
            cameraIndex = index

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

    # configure the external output triggers of the Ajile controller component to be rising edge, with a hold time of half the frame time
    # (Note that the default trigger hold time is defined by TRIGGER_DEFAULT_HOLD_TIME. 
    #  This step can be skipped if the default hold time and rising edge is sufficient.)
    inputTriggerSettings = project.Components()[controllerIndex].InputTriggerSettings()
    outputTriggerSettings = project.Components()[controllerIndex].OutputTriggerSettings()
    for index in range(len(outputTriggerSettings)):
        outputTriggerSettings[index] = aj.ExternalTriggerSetting(aj.RISING_EDGE, aj.FromMSec(frameTime_ms/2))
    project.SetTriggerSettings(controllerIndex, inputTriggerSettings, outputTriggerSettings)

    # create a trigger rule to connect the camera frame started to the external output trigger 0
    cameraFrameStartedToExtTrigOut = aj.TriggerRule()
    cameraFrameStartedToExtTrigOut.AddTriggerFromDevice(aj.TriggerRulePair(cameraIndex, aj.FRAME_STARTED))
    cameraFrameStartedToExtTrigOut.SetTriggerToDevice(aj.TriggerRulePair(controllerIndex, aj.EXT_TRIGGER_OUTPUT_1))
    # add the trigger rule to the project
    project.AddTriggerRule(cameraFrameStartedToExtTrigOut)
        
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

if __name__ == "__main__":

    example_helper.RunCameraExample(CreateProject)
