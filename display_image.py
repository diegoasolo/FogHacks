import ajiledriver as aj

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
import example_helper

# creates an Ajile project and returns it
def CreateProject(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None, image_name=None):
    """
    Create an Ajile project to display an image from the images folder.
    
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
    image_name : str, optional
        Name of the image file (with or without extension).
        If None, uses the first available image.
    """
    projectName = "display_image"
    currentPath = os.path.dirname(os.path.realpath(__file__))
    imagesPath = os.path.join(currentPath, "images")
    
    # Determine which image to load
    if image_name is None:
        # Try to find any PNG image in the images folder
        from pathlib import Path
        image_files = list(Path(imagesPath).glob("*.png"))
        if not image_files:
            raise FileNotFoundError(f"No PNG images found in {imagesPath}")
        filename = str(image_files[0])
        print(f"No image specified, using: {image_files[0].name}")
    else:
        # Use specified image name
        filename = image_name
        if not filename.endswith('.png'):
            filename = filename + '.png'
        filename = os.path.join(imagesPath, filename)
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Image not found: {filename}")
    
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
    # Get image name from command line if provided
    image_name = None
    if len(sys.argv) > 1:
        image_name = sys.argv[1]
    
    # Create a wrapper function that passes the image_name
    def CreateProjectWrapper(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None):
        return CreateProject(sequenceID, sequenceRepeatCount, frameTime_ms, components, image_name)
    
    example_helper.RunExample(CreateProjectWrapper)
