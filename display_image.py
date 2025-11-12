import ajiledriver as aj

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns it
def CreateProject(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None):
    projectName = "display_image"
    currentPath = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(currentPath, "images", "USAF_test1.png")
    
    if frameTime_ms < 0:
        frameTime_ms = 10000
    numImages = 1
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)
    
    # create the image
    testImage = aj.Image(1)
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
    
    print(f"Loaded image: {os.path.basename(filename)}")
    return project

        
if __name__ == "__main__":
    example_helper.RunExample(CreateProject)
