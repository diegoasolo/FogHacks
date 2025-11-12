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

    projectName = "dmd_binary_checkerboard_example"
    if frameTime_ms < 0:
        frameTime_ms = 100
    
    # create a new project
    project = aj.Project(projectName)
    # set the project components and the image size based on the DMD type
    if components is not None:
        project.SetComponents(components)
        dmdIndex = project.GetComponentIndexWithDeviceType(aj.DMD_4500_DEVICE_TYPE)
        if dmdIndex < 0: dmdIndex = project.GetComponentIndexWithDeviceType(aj.DMD_3000_DEVICE_TYPE)
        imageWidth = components[dmdIndex].NumColumns()
        imageHeight = components[dmdIndex].NumRows()
        deviceType = components[dmdIndex].DeviceType().HardwareType()
    else:
        imageWidth = aj.DMD_IMAGE_WIDTH_MAX
        imageHeight = aj.DMD_IMAGE_HEIGHT_MAX
        deviceType = aj.DMD_4500_DEVICE_TYPE

    # generate a list of gray code images (which are numpy arrays)
    boardImages = GenerateCheckerboards(imageWidth, imageHeight)
    
    # create the images from the numpy gray code images and add them to our project
    imageCount = 1
    for boardImage in boardImages:
        image = aj.Image(imageCount)
        imageCount += 1
        image.ReadFromMemory(boardImage, 8, aj.ROW_MAJOR_ORDER, deviceType)
        project.AddImage(image)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        example_helper.AddPreviewImage(project, boardImage, image.ID(), image.ID(), "checkberboard_" + str(image.ID()), 1)

    numImages = len(boardImages)
    
    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, projectName, deviceType, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

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
