import ajiledriver as aj
import cv2
import numpy
import math

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# helper function which creates a checkerboard pattern and its inverse
def GenerateBlackWhite(width, height):

    # Allocate Gray codes.
    images = []
    images.append(numpy.zeros(shape=(height, width, 1), dtype=numpy.uint8))
    images.append(numpy.ones(shape=(height, width, 1), dtype=numpy.uint8))
    images[1] *= 255
    
    return images

# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_binary_checkerboard_example"
    if frameTime_ms < 0:
        frameTime_ms = 0.05 # default is 50 microseconds per frame
    roiWidthColumns = 16
    roiHeightRows = aj.DMD_IMAGE_HEIGHT_MAX
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)

    # generate a list of gray code images (which are numpy arrays)
    images = GenerateBlackWhite(aj.DMD_IMAGE_WIDTH_MAX, aj.DMD_IMAGE_HEIGHT_MAX)
    
    # create the images from the numpy gray code images and add them to our project
    imageCount = 1
    for image in images:
        ajImage = aj.Image(imageCount)
        imageCount += 1
        ajImage.ReadFromMemory(image, 8, aj.ROW_MAJOR_ORDER, aj.DMD_4500_DEVICE_TYPE)
        project.AddImage(ajImage)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        example_helper.AddPreviewImage(project, image, ajImage.ID(), ajImage.ID(), "roi_" + str(ajImage.ID()), 1)

    numImages = len(images)
    
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
        frame.SetRoiWidthColumns(roiWidthColumns)
        frame.SetRoiHeightRows(roiHeightRows)
        project.AddFrame(frame)

    return project

        
if __name__ == "__main__":

    example_helper.RunExample(CreateProject)
