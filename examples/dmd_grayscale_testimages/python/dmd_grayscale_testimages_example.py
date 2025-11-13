import ajiledriver as aj
import os
import cv2

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_grayscale_testimages_example"
    currentPath = os.path.dirname(os.path.realpath(__file__))
    filenames = [currentPath + "/../../images/dog.jpg", 
                 currentPath + "/../../images/plants.jpg"]
    if frameTime_ms < 0:
        frameTime_ms = 1000
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)
    
    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, projectName, aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create the images
    nextImageID = 1
    for filename in filenames:

        # create a sequence item to display the 8 bitplanes of the grayscale image with the default minimum timing
        sequenceItem = aj.SequenceItem(sequenceID)
        imageBitplanes = aj.ImageList()
        project.CreateGrayscaleSequenceItem_FromFile(sequenceItem, imageBitplanes, filename, nextImageID)
        # set the display time of this grayscale sequence item by setting its repeat time
        # (note that this must be done AFTER the frames have been added to the sequence item, since its time depends on the frame time)
        sequenceItem.SetRepeatTimeMSec(frameTime_ms)
        # add the image bitplanes to the project
        project.AddImages(imageBitplanes);
        # add the sequence item to the project
        project.AddSequenceItem(sequenceItem)
        # update the image ID for the next set of images
        nextImageID += len(imageBitplanes)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        for image in imageBitplanes:
            example_helper.AddPreviewImageFile(project, filename, image.ID(), imageBitplanes[0].ID(), 8, 1)

    return project

        
if __name__ == "__main__":

    example_helper.RunExample(CreateProject)
