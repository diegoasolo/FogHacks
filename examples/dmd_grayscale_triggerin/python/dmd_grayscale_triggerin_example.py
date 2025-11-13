import ajiledriver as aj
import os
import cv2
import numpy
import math

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

def GenerateSinusoidImages(width, height):
    
    numPhases = 3
    wavelength = 100   # wavelength (number of pixels per cycle)

    # allocate the images
    # we must allocate the lower 8 bits and upper 8 bits seperately since the ajiledriver Python interface doesn't support 16-bit
    sineImages = []
    for i in range(numPhases*2):
        sineImages.append(numpy.zeros(shape=(height, width, 1), dtype=numpy.uint8))

    for i in range(numPhases):
        phase = i * 1.0 / float(numPhases)
        sineValue = 0.0
        for c in range(width):
            # compute the 1-D sine value
            sineValue = math.sin(float(c) / wavelength * 2*math.pi + phase * 2*math.pi)
            # rescale it to be a 16-bit number
            sineValue = (sineValue + 1) * 0xff/2.0
            # create the 2-D sine images by expanding each 1-D sine value into a rectangle across the entire image
            cv2.rectangle(sineImages[i], (c,0), (c,height), int(sineValue), -1)
        # repeat for the horizontal images
        for r in range(height):
            sineValue = math.sin(float(r) / wavelength * 2*math.pi + phase * 2*math.pi)
            sineValue = (sineValue + 1) * 0xff/2.0
            cv2.rectangle(sineImages[numPhases+i], (0,r), (width,r), int(sineValue), -1)
    
    return sineImages

# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_grayscale_triggerin_example"
    if frameTime_ms < 0:
        frameTime_ms = 1000
    
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
           deviceType == aj.AJILE_3PORT_CONTROLLER_DEVICE_TYPE or \
           deviceType == aj.DMD_CAMERA_CONTROLLER_DEVICE_TYPE:
            controllerIndex = index
    dmdIndex = project.GetComponentIndexWithDeviceType(aj.DMD_4500_DEVICE_TYPE)

    # configure the external input triggers of the Ajile controller component to be rising edge
    # (Note that the default is rising edge. This step can therefore be skipped but is here for demonstration purposes only).
    inputTriggerSettings = project.Components()[controllerIndex].InputTriggerSettings()
    outputTriggerSettings = project.Components()[controllerIndex].OutputTriggerSettings()
    for index in range(len(inputTriggerSettings)):
        inputTriggerSettings[index] = aj.ExternalTriggerSetting(aj.RISING_EDGE)
    project.SetTriggerSettings(controllerIndex, inputTriggerSettings, outputTriggerSettings)

    # create a trigger rule to connect external trigger input 1 to DMD start sequence item
    extTrigInToDMDStartSequenceItem = aj.TriggerRule()
    extTrigInToDMDStartSequenceItem.AddTriggerFromDevice(aj.TriggerRulePair(controllerIndex, aj.EXT_TRIGGER_INPUT_1))
    extTrigInToDMDStartSequenceItem.SetTriggerToDevice(aj.TriggerRulePair(dmdIndex, aj.START_SEQUENCE_ITEM))
    # add the trigger rule to the project
    project.AddTriggerRule(extTrigInToDMDStartSequenceItem)

    # generate a list of sinudoid images (which are numpy matrices)
    sineImages = GenerateSinusoidImages(aj.DMD_IMAGE_WIDTH_MAX, aj.DMD_IMAGE_HEIGHT_MAX)

    # create the 8-bit image sequence
    project.AddSequence(aj.Sequence(sequenceID, "sinewave_example 8-bit", aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create the images
    numImages = len(sineImages)
    nextImageID = 1
    for i in range(numImages):

        # convert the sinusoid image to an Ajile image. Note we convert to an 8-bit image here.
        image = aj.Image()
        image.ReadFromMemory(sineImages[i], 8, aj.ROW_MAJOR_ORDER, 0, 0, 0, 8, aj.UNDEFINED_MAJOR_ORDER)
        
        # create a sequence item to display the 8 bitplanes of the sine image with the default minimum timing
        sequenceItem = aj.SequenceItem(sequenceID)
        imageBitplanes = aj.ImageList()
        project.CreateGrayscaleSequenceItem_FromImage(sequenceItem, imageBitplanes, image, nextImageID)
        # set the display time of this grayscale sequence item by setting its repeat time
        # (note that this must be done AFTER the frames have been added to the sequence item, since its time depends on the frame time)
        sequenceItem.SetRepeatTimeMSec(frameTime_ms)
        # add the image bitplanes to the project
        project.AddImages(imageBitplanes)
        # add the sequence item to the project
        project.AddSequenceItem(sequenceItem)
        # update the image ID for the next set of images
        nextImageID += len(imageBitplanes)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        for image in imageBitplanes:
            example_helper.AddPreviewImage(project, sineImages[i], image.ID(), imageBitplanes[0].ID(), "sinewave_" + str(imageBitplanes[0].ID()))

    return project
        
if __name__ == "__main__":

    example_helper.RunExample(CreateProject)
