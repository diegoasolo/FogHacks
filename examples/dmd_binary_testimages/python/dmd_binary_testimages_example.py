import ajiledriver as aj

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_binary_testimages_example"
    currentPath = os.path.dirname(os.path.realpath(__file__))
    filenameBase = currentPath + "/../../images/cat_"
    if frameTime_ms < 0:
        frameTime_ms = 100
    numImages = 14
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)
    
    # create the images
    for i in range(1, numImages+1):
        filename = filenameBase + str(i) + ".png"
        testImage = aj.Image(i)
        testImage.ReadFromFile(filename, aj.DMD_4500_DEVICE_TYPE)
        project.AddImage(testImage)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        example_helper.AddPreviewImageFile(project, filename, testImage.ID(), testImage.ID(), 1)
    
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
