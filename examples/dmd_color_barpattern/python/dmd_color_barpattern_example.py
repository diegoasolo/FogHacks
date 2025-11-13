import ajiledriver as aj
import os

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns in
def CreateProject(sequenceID=1, sequenceRepeatCount=0, frameTime_ms=-1, components=None):

    projectName = "dmd_color_barpattern_example"
    currentPath = os.path.dirname(os.path.realpath(__file__))
    filenameBase = currentPath + "/../../images/Video_Color_Test_Pattern_"
    if frameTime_ms < 0:
        frameTime_ms = 100
    numImages = 3
    maxCurrent = 6000
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)
    
    # read the images and add them to the project
    for i in range(1, numImages+1):
        if i == 1:
            filename = filenameBase + "Red_1b.bmp"
        elif i == 2:
            filename = filenameBase + "Green_1b.bmp"
        else:
            filename = filenameBase + "Blue_1b.bmp"
        image = aj.Image(i)
        image.ReadFromFile(filename, aj.DMD_4500_DEVICE_TYPE)
        project.AddImage(image)
        # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
        example_helper.AddPreviewImageFile(project, filename, image.ID(), image.ID(), 1)
    
    # create the sequence
    project.AddSequence(aj.Sequence(sequenceID, projectName, aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))

    # create first sequence item, which the frames will be added to
    project.AddSequenceItem(aj.SequenceItem(sequenceID, 1))
    # create second sequence item, which we will add to the project after
    colorSequenceItem = aj.SequenceItem(sequenceID)

    # create the frames and add them to the project, which adds them to the last sequence item
    for i in range(numImages):
        frame = aj.Frame()
        frame.SetSequenceID(sequenceID)
        frame.SetImageID(i+1)
        frame.SetFrameTimeMSec(frameTime_ms)
        # set the LED settings for this frame to turn on only one of the three LEDs
        ledSettings = aj.LedSettingList()
        for ledIndex in range(numImages):
            if ledIndex == i:
                ledSettings.append(aj.LedSetting(maxCurrent, 100, aj.FromMSec(int(frameTime_ms))))
            else:
                ledSettings.append(aj.LedSetting(0, 0, 0))
        frame.SetLedSettings(ledSettings)
        # add the frame to the first sequence item
        project.AddFrame(frame)
        # add the frame to the color sequence item, but change the frame time to full speed
        frame.SetFrameTime(aj.DMD_MINIMUM_FRAME_TIME)
        colorSequenceItem.AddFrame(frame)

    # set the time of the color sequence item to the frame time
    colorSequenceItem.SetRepeatTimeMSec(frameTime_ms*3)
    # add the sequenece item to the project
    project.AddSequenceItem(colorSequenceItem)

    return project

        
if __name__ == "__main__":

    example_helper.RunExample(CreateProject)
