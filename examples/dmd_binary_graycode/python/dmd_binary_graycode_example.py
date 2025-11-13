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
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_binary_graycode_example"
    if frameTime_ms < 0:
        frameTime_ms = 100
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)

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
