import ajiledriver as aj
import cv2
import numpy
import math

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# helper function which creates a checkerboard pattern and its inverse
def GenerateCheckerboards(width, height):

    # width and height of each checkerboard square
    squareWidth = 50
    squareHeight = 100

    # Allocate Gray codes.
    boardImages = []
    for i in range(2):
        boardImages.append(numpy.zeros(shape=(height, width, 1), dtype=numpy.uint8))
    
    # draw the checkerboard pattern
    value = 0
    firstValue = 0
    for i in range(0, width, squareWidth):
        value = firstValue
        for j in range(0, height, squareHeight):
            cv2.rectangle(boardImages[0], (i, j), (i+squareWidth, j+squareHeight), value, -1)
            value = 255 if value == 0 else 0
        firstValue = 255 if firstValue == 0 else 0

    # the second board is the inverse of the first
    boardImages[1] = 255 - boardImages[0]

    return boardImages

# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_binary_triggerout_example"
    if frameTime_ms < 0:
        frameTime_ms = 100
    
    # create a new project
    project = aj.Project(projectName)

    # set the components for the project if they were provided, or create default ones if not
    if components is not None:
        project.SetComponents(components)
    else:
        # these defaults are for a DMD_4500 device on a standalone board. 
        # Either pass in the proper components or modify if they are different from your setup.
        controllerComponent = aj.Component()
        controllerComponent.CreateComponentForDevice(aj.DeviceDescriptor(aj.AJILE_CONTROLLER_DEVICE_TYPE))
        project.AddComponent(controllerComponent)
        dmdComponent = aj.Component()
        dmdComponent.CreateComponentForDevice(aj.DeviceDescriptor(aj.DMD_4500_DEVICE_TYPE))
        project.AddComponent(dmdComponent)

    # get the component indices
    for index, component in enumerate(project.Components()):
        deviceType = component.DeviceType().HardwareType()
        if deviceType == aj.AJILE_CONTROLLER_DEVICE_TYPE or \
           deviceType == aj.AJILE_2PORT_CONTROLLER_DEVICE_TYPE or \
           deviceType == aj.AJILE_3PORT_CONTROLLER_DEVICE_TYPE:
            controllerIndex = index
    dmdIndex = project.GetComponentIndexWithDeviceType(aj.DMD_4500_DEVICE_TYPE)

    # configure the external output triggers of the Ajile controller component to be rising edge, with a hold time of half the frame time
    # (Note that the default trigger hold time is defined by TRIGGER_DEFAULT_HOLD_TIME. 
    #  This step can be skipped if the default hold time and rising edge is sufficient.)
    inputTriggerSettings = project.Components()[controllerIndex].InputTriggerSettings()
    outputTriggerSettings = project.Components()[controllerIndex].OutputTriggerSettings()
    for index in range(len(outputTriggerSettings)):
        outputTriggerSettings[index] = aj.ExternalTriggerSetting(aj.RISING_EDGE, aj.FromMSec(frameTime_ms/2))
    project.SetTriggerSettings(controllerIndex, inputTriggerSettings, outputTriggerSettings)

    # create a trigger rule to connect the DMD frame started to the external output trigger 0
    dmdFrameStartedToExtTrigOut = aj.TriggerRule()
    dmdFrameStartedToExtTrigOut.AddTriggerFromDevice(aj.TriggerRulePair(dmdIndex, aj.FRAME_STARTED))
    dmdFrameStartedToExtTrigOut.SetTriggerToDevice(aj.TriggerRulePair(controllerIndex, aj.EXT_TRIGGER_OUTPUT_1))
    # add the trigger rule to the project
    project.AddTriggerRule(dmdFrameStartedToExtTrigOut)

    dmdFrameStartedToExtTrigOut2 = aj.TriggerRule()
    dmdFrameStartedToExtTrigOut2.AddTriggerFromDevice(aj.TriggerRulePair(dmdIndex, aj.FRAME_STARTED))
    dmdFrameStartedToExtTrigOut2.SetTriggerToDevice(aj.TriggerRulePair(controllerIndex, aj.EXT_TRIGGER_OUTPUT_2))
    # add the trigger rule to the project
    project.AddTriggerRule(dmdFrameStartedToExtTrigOut2)

    # generate a list of gray code images (which are numpy arrays)
    boardImages = GenerateCheckerboards(aj.DMD_IMAGE_WIDTH_MAX, aj.DMD_IMAGE_HEIGHT_MAX)
    
    # create the images from the numpy gray code images and add them to our project
    imageCount = 1
    for boardImage in boardImages:
        image = aj.Image(imageCount)
        imageCount += 1
        image.ReadFromMemory(boardImage, 8, aj.ROW_MAJOR_ORDER, aj.DMD_4500_DEVICE_TYPE)
        project.AddImage(image)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        example_helper.AddPreviewImage(project, boardImage, image.ID(), image.ID(), "checkberboard_" + str(image.ID()), 1)

    numImages = len(boardImages)
    
    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, projectName, aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create a single sequence item, which all the frames will be added to
    project.AddSequenceItem(aj.SequenceItem(sequenceID, 1))

    # create the frames and add them to the project, which adds them to the last sequence item
    for i in range(numImages):
        frame = aj.Frame()
        frame.SetSequenceID(sequenceID)
        frame.SetImageID(i+1)
        frame.SetFrameTimeMSec(frameTime_ms)
        project.AddFrame(frame)

    return project

        
if __name__ == "__main__":

    example_helper.RunExample(CreateProject)
