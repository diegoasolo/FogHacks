import ajiledriver as aj

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns it
def CreateProject(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None, image_path=None):
    """
    Create an Ajile project to display a DMD binary pattern.
    
    Parameters:
    -----------
    sequenceID : int
        Sequence ID for the project
    sequenceRepeatCount : int
        Number of times to repeat the sequence
    frameTime_ms : int
        Frame time in milliseconds (-1 for default)
    components : optional
        Components to set for the project
    image_path : str, optional
        Path to the DMD pattern image file.
        If None, uses rings_phase_hologram_dmd.png
    """
    projectName = "display_dmd_pattern"
    currentPath = os.path.dirname(os.path.realpath(__file__))
    
    # Determine image path
    if image_path is None:
        image_path = os.path.join(currentPath, "cat_1.png")
    elif not os.path.isabs(image_path):
        # If relative path, make it relative to current directory
        image_path = os.path.join(currentPath, image_path)
    
    # Verify file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"DMD pattern image not found: {image_path}")
    
    print(f"Loading DMD pattern from: {image_path}")
    
    if frameTime_ms < 0:
        frameTime_ms = 10000
    numImages = 1
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)
    
    # create the image
    testImage = aj.Image(1)
    print(f"Reading DMD pattern file: {image_path}")
    read_result = testImage.ReadFromFile(image_path, aj.DMD_4500_DEVICE_TYPE)
    if read_result != aj.ERROR_NONE:
        print(f"Error: ReadFromFile returned {read_result} when reading {image_path}")
        # attempt to read without specifying device type to see if conversion fails
        try:
            alt_result = testImage.ReadFromFile(image_path)
            print(f"ReadFromFile without dstDeviceType returned {alt_result}")
        except Exception as e:
            print(f"ReadFromFile without dstDeviceType raised: {e}")
        raise RuntimeError(f"Failed to load image {image_path} (code {read_result})")
    project.AddImage(testImage)
    print(f"Image added to project with ID: {testImage.ID()}")
    # diagnostic info about the loaded image
    try:
        print(f"Image properties: Width={testImage.Width()}, Height={testImage.Height()}, BitDepth={testImage.BitDepth()}")
    except Exception:
        # if methods not present, ignore
        pass
    # add preview images (which will be used by the GUI only for display, ignore if not opening the example in the GUI)
    example_helper.AddPreviewImageFile(project, image_path, testImage.ID(), testImage.ID(), 1)
    
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
        print(f"Created frame {i+1} with ImageID {i+1}, SequenceID {sequenceID}, FrameTime {frameTime_ms}ms")
    
    print(f"Project created successfully. Loaded DMD pattern: {os.path.basename(image_path)}")
    return project

        
if __name__ == "__main__":
    # Get image path from command line if provided. If the first argument
    # looks like an option (starts with '-'), treat it as a flag and do
    # not use it as the image path. This prevents flags like '--usb3'
    # being interpreted as a filename.
    image_path = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        image_path = sys.argv[1]
    
    # Create a wrapper function that passes the image_path
    def CreateProjectWrapper(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None):
        return CreateProject(sequenceID, sequenceRepeatCount, frameTime_ms, components, image_path)
    
    example_helper.RunExample(CreateProjectWrapper)

