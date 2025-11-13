import ajiledriver as aj
import os
import cv2
import numpy
import math

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# helper function which generates a (1-D) De Bruijn sequence with k symbols and order n
def de_bruijn(k, n):

    alphabet = list(map(str, range(k)))

    a = [0] * k * n
    sequence = []

    def db(t, p):
        if t > n:
            if n % p == 0:
                sequence.extend(a[1:p + 1])
        else:
            a[t] = a[t - p]
            db(t + 1, p)
            for j in range(a[t - p] + 1, k):
                a[t] = j
                db(t + 1, t)
    db(1, 1)
    
    return sequence

# Helper function which transforms an image into diagonal space to deal with the diamond indexing of the DMD4500 and DMD3000.
# This is useful for improving the edge sharpness of images with thin (e.g. 1-pixel wide) lines.
# Works best if the inputImage twice the size of transformedImage to avoid black background.
def DiagonalTransform (inputImage, transformedImage):
    inputWidth = inputImage.shape[1]
    inputHeight = inputImage.shape[0]
    transformedWidth = transformedImage.shape[1]
    transformedHeight = transformedImage.shape[0]

    for r in range(inputHeight):
        for c in range(inputWidth):
            transformedColIndex = int(r - math.floor(c/2))
            transformedRowIndex = c
            inputColIndex = r
            inputRowIndex = int(inputHeight/2 - r + c - 1)
            if transformedRowIndex < 0 or transformedColIndex < 0 or transformedRowIndex >= transformedHeight or transformedColIndex >= transformedWidth or \
               inputRowIndex < 0 or inputColIndex < 0 or inputRowIndex >= inputHeight or inputColIndex >= inputWidth:
                continue
            transformedImage[transformedRowIndex, transformedColIndex-1] = inputImage[inputRowIndex, inputColIndex]

# Helper function which generates color De bruijn images. 
# Generates total of 9 binary images, which are 3 color channels for 
# the vertical, horizontal and diagonal (diamond mirror format corrected) images
def GenerateDebruijnImages(width, height):
    
    numColors = 6
    order = 4
    numSequences = 3
    debruijnSequence = de_bruijn(numColors, order)
    colorList = [(0,0,1), (0,1,0), (0,1,1), (1,0,0), (1,0,1), (1,1,0)]
    
    # allocate the images
    debruijnImages = []    
    for i in range(3*numSequences):
        debruijnImages.append(numpy.zeros(shape=(height, width, 1), dtype=numpy.uint8))

    # create the vertical debruijn images
    for i in range(width):
        color = colorList[debruijnSequence[i]]
        for colorIndex in range(3):
            cv2.rectangle(debruijnImages[colorIndex], (i,0), (i,height), color[colorIndex] * 255, -1)

    # create the horizontal debruijn images
    for i in range(height):
        color = colorList[debruijnSequence[i]]
        for colorIndex in range(3):
            cv2.rectangle(debruijnImages[3+colorIndex], (0,i), (width,i), color[colorIndex] * 255, -1)

    # create the diagonal debruijn images by first generating the vertical images at twice the resolution
    # then transforming the oversized images into diagonal format with the correct size
    originalImagesVert = []
    debruijnSequenceLarge = de_bruijn(numColors, order+1)
    for i in range(3):
        originalImagesVert.append(numpy.zeros(shape=(height*2, width*2, 1), dtype=numpy.uint8))
    for i in range(width*2):
        color = colorList[debruijnSequenceLarge[i]]
        for colorIndex in range(3):
            cv2.rectangle(originalImagesVert[colorIndex], (i,0), (i,height*2), color[colorIndex] * 255, -1)
    # now transform into diagonal mirror space
    for i in range(3):
        DiagonalTransform(originalImagesVert[i], debruijnImages[3*2+i])        
                
    return debruijnImages


# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_color_debruijn_example"
    if frameTime_ms < 0:
        frameTime_ms = 100
    maxCurrent = 6000
    numLeds = 3
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)
    
    # generate the debruijn images (which are numpy matrices)
    print ("Generating Debruijn sequence images, this may take a few moments.")
    debruijnImages = GenerateDebruijnImages(aj.DMD_IMAGE_WIDTH_MAX, aj.DMD_IMAGE_HEIGHT_MAX)
    numImages = len(debruijnImages)

    # read the images and add them to the project
    imageCount = 1
    for index, debruijnImage in enumerate(debruijnImages):
        image = aj.Image(imageCount)
        imageCount += 1
        image.ReadFromMemory(debruijnImage, 8, aj.ROW_MAJOR_ORDER, aj.DMD_4500_DEVICE_TYPE)
        project.AddImage(image)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        example_helper.AddPreviewImage(project, debruijnImage, image.ID(), image.ID(), "debruijn_" + str(image.ID()), 1)
    
    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, projectName, aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # add the sequence items and frames to the project
    sequenceItem = None
    for i in range(numImages):
        ledNumber = i % numLeds
        # every three images we create a new sequence item (since they are the 3 color bitplanes)
        if ledNumber == 0:
            sequenceItem = aj.SequenceItem(sequenceID)
        frame = aj.Frame()
        frame.SetSequenceID(sequenceID)
        frame.SetImageID(i+1)
        frame.SetFrameTime(aj.DMD_MINIMUM_FRAME_TIME)
        # set the LED settings for this frame to turn on only one of the three LEDs
        ledSettings = aj.LedSettingList()
        for ledIndex in range(3):
            if ledIndex == ledNumber:
                ledSettings.append(aj.LedSetting(maxCurrent, 100, aj.FromMSec(int(frameTime_ms))))
            else:
                ledSettings.append(aj.LedSetting(0, 0, 0))
        frame.SetLedSettings(ledSettings)
        # add the frame to the sequence item
        sequenceItem.AddFrame(frame)
        if ledNumber == numLeds-1:
            # set the time of the color sequence item to the frame time
            sequenceItem.SetRepeatTimeMSec(frameTime_ms)
            # add the sequenece item to the project
            project.AddSequenceItem(sequenceItem)

    return project

        
if __name__ == "__main__":

    example_helper.RunExample(CreateProject)
