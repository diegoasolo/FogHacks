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
    sineImagesLower = []
    sineImagesUpper = []
    for i in range(numPhases*2):
        sineImagesLower.append(numpy.zeros(shape=(height, width, 1), dtype=numpy.uint8))
        sineImagesUpper.append(numpy.zeros(shape=(height, width, 1), dtype=numpy.uint8))

    for i in range(numPhases):
        phase = i * 1.0 / float(numPhases)
        sineValue = 0.0
        for c in range(width):
            # compute the 1-D sine value
            sineValue = math.sin(float(c) / wavelength * 2*math.pi + phase * 2*math.pi)
            # rescale it to be a 16-bit number
            sineValue = (sineValue + 1) * 0xffff/2.0
            # create the 2-D sine images by expanding each 1-D sine value into a rectangle across the entire image
            cv2.rectangle(sineImagesLower[i], (c,0), (c,height), int(sineValue) & 0xFF, -1)
            cv2.rectangle(sineImagesUpper[i], (c,0), (c,height), (int(sineValue) & 0xFF00) >> 8, -1)
        # repeat for the horizontal images
        for r in range(height):
            sineValue = math.sin(float(r) / wavelength * 2*math.pi + phase * 2*math.pi)
            sineValue = (sineValue + 1) * 0xffff/2.0
            cv2.rectangle(sineImagesLower[numPhases+i], (0,r), (width,r), int(sineValue) & 0xFF, -1)
            cv2.rectangle(sineImagesUpper[numPhases+i], (0,r), (width,r), (int(sineValue) & 0xFF00) >> 8, -1)
    
    return sineImagesLower, sineImagesUpper

# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_grayscale_sinewave_example"
    if frameTime_ms < 0:
        frameTime_ms = 1000
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)

    # generate a list of sinudoid images (which are numpy matrices)
    sineImagesLower, sineImagesUpper = GenerateSinusoidImages(aj.DMD_IMAGE_WIDTH_MAX, aj.DMD_IMAGE_HEIGHT_MAX)

    # create the 8-bit image sequence
    project.AddSequence(aj.Sequence(sequenceID, "sinewave_example 8-bit", aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create the images
    numImages = len(sineImagesUpper)
    nextImageID = 1
    for i in range(numImages):

        # convert the sinusoid image to an Ajile image. Note we convert to an 8-bit image here.
        image = aj.Image()
        image.ReadFromMemory(sineImagesUpper[i], 8, aj.ROW_MAJOR_ORDER, 0, 0, 0, 8, aj.UNDEFINED_MAJOR_ORDER)
        
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
            example_helper.AddPreviewImage(project, sineImagesUpper[i], image.ID(), imageBitplanes[0].ID(), "sinewave_" + str(imageBitplanes[0].ID()))

    # create the 12-bit image sequence
    bitDepth = 12
    project.AddSequence(aj.Sequence(sequenceID+1, "sinewave_example 12-bit", aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    for i in range(numImages):

        # convert the sinusoid image to an Ajile image. Note we keep the image as 16-bit
        imageUpper = aj.Image()
        imageUpper.ReadFromMemory(sineImagesUpper[i], 8, aj.ROW_MAJOR_ORDER, 0, 0, 0, 8, aj.UNDEFINED_MAJOR_ORDER)
        imageLower = aj.Image()
        imageLower.ReadFromMemory(sineImagesLower[i], 8, aj.ROW_MAJOR_ORDER, 0, 0, 0, 8, aj.UNDEFINED_MAJOR_ORDER)
        
        # split the image into its 16 bitplanes and convert into the DMD format
        imageBitplanesLower = aj.ImageList()
        imageLower.SplitBitplanes(imageBitplanesLower, aj.DMD_4500_DEVICE_TYPE)
        imageBitplanesUpper = aj.ImageList()
        imageUpper.SplitBitplanes(imageBitplanesUpper, aj.DMD_4500_DEVICE_TYPE)
        imageBitplanes = aj.ImageList(bitDepth)
        # concatenate the two bitplane lists (throwing away the bottom order bitplanes)
        index = 0
        for j in range(16-bitDepth, len(imageBitplanesLower)):
            imageBitplanes[index] = imageBitplanesLower[j]
            index += 1
        for j in range(len(imageBitplanesUpper)):
            imageBitplanes[index] = imageBitplanesUpper[j]
            index += 1
        # set the image ID of the bitplanes then add them to the project
        for j in range(len(imageBitplanes)):
            imageBitplanes[j].SetID(nextImageID)
            nextImageID += 1
            project.AddImage(imageBitplanes[j])

        # create a sequence item to display the 12 bitplanes of the grayscale image with the default minimum timing
        sequenceItem = aj.SequenceItem(sequenceID+1)
        project.CreateGrayscaleSequenceItem(sequenceItem, imageBitplanes)
        # set the display time of this grayscale sequence item by setting its repeat time
        sequenceItem.SetRepeatTimeMSec(frameTime_ms)
        # add the sequence item to the project
        project.AddSequenceItem(sequenceItem)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        for image in imageBitplanes:
            example_helper.AddPreviewImage(project, sineImagesUpper[i], image.ID(), imageBitplanes[0].ID(), "sinewave_" + str(imageBitplanes[0].ID()))

    return project
        
if __name__ == "__main__":

    example_helper.RunExample(CreateProject)
