import ajiledriver as aj
import cv2
import numpy as np

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import example_helper

# DMD 4500 native resolution (912 x 1140 mirrors) - 1:1 pixel-to-mirror mapping
DMD_WIDTH = 912
DMD_HEIGHT = 1140


def load_and_resize_for_dmd(image_path, dmd_width=DMD_WIDTH, dmd_height=DMD_HEIGHT):
    """
    Load an image and resize to exact DMD dimensions for 1:1 mirror mapping.
    Uses INTER_NEAREST for binary patterns to avoid stretching artifacts.
    Returns numpy array (height, width, 1) in uint8, ready for ReadFromMemory.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"Failed to load image: {image_path}")
    orig_h, orig_w = img.shape[:2]
    # Resize to DMD native resolution - INTER_NEAREST preserves binary edges
    dmd_pattern = cv2.resize(img, (dmd_width, dmd_height), interpolation=cv2.INTER_NEAREST)
    # Ensure shape (height, width, 1) for ajile ReadFromMemory
    if len(dmd_pattern.shape) == 2:
        dmd_pattern = np.expand_dims(dmd_pattern, axis=2)
    print(f"  Original: {orig_w}x{orig_h} -> DMD 1:1: {dmd_width}x{dmd_height} mirrors")
    return dmd_pattern


# creates an Ajile project and returns it
def CreateProject(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None, image_path=None, save_preview=False):
    """
    Create an Ajile project to display a DMD binary pattern.
    
    Uses 1:1 pixel-to-mirror mapping: the image is resized to DMD native
    resolution (912x1140) before loading, so each pixel maps to exactly one
    micromirror without stretching.
    
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
        If None, uses cat_1.png
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
    
    # Get DMD dimensions (use component if available, else native 912x1140)
    dmd_width, dmd_height = DMD_WIDTH, DMD_HEIGHT
    if components is not None:
        try:
            dmd_idx = next((i for i, c in enumerate(components) 
                           if c.DeviceType().HardwareType() == aj.DMD_4500_DEVICE_TYPE), -1)
            if dmd_idx >= 0:
                dmd_width = components[dmd_idx].NumColumns()
                dmd_height = components[dmd_idx].NumRows()
        except Exception:
            pass
    
    # Load image and resize to exact DMD dimensions for 1:1 mapping (no stretching)
    dmd_pattern = load_and_resize_for_dmd(image_path, dmd_width, dmd_height)
    
    # create a new project
    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)
    
    # create the image from numpy array - same data that goes to DMD mirrors
    testImage = aj.Image(1)
    read_result = testImage.ReadFromMemory(dmd_pattern, 8, aj.ROW_MAJOR_ORDER, aj.DMD_4500_DEVICE_TYPE)
    if read_result != aj.ERROR_NONE:
        raise RuntimeError(f"Failed to load image into DMD format (code {read_result})")
    project.AddImage(testImage)
    print(f"Image added to project with ID: {testImage.ID()}")
    try:
        print(f"Image properties: Width={testImage.Width()}, Height={testImage.Height()}, BitDepth={testImage.BitDepth()}")
    except Exception:
        pass
    
    # Add preview with exact 1:1 DMD mirror mapping (same array sent to hardware)
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    example_helper.AddPreviewImage(project, dmd_pattern, testImage.ID(), testImage.ID(), 
                                   f"{image_name}_dmd_1to1", 1)
    
    # Optionally save the exact DMD preview to file (shows exactly what each mirror displays)
    if save_preview:
        preview_path = os.path.join(currentPath, f"{image_name}_dmd_preview_1to1.png")
        cv2.imwrite(preview_path, dmd_pattern)
        print(f"Saved 1:1 DMD preview to: {preview_path}")
    
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
    # Parse command line: image path, --save-preview to save 1:1 DMD preview to file
    image_path = None
    save_preview = False
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args:
        image_path = args[0]
    save_preview = '--save-preview' in sys.argv
    
    # Strip our custom args so example_helper.ParseCommandArguments doesn't choke
    for arg in [image_path, '--save-preview']:
        if arg and arg in sys.argv:
            sys.argv.remove(arg)
    
    # Create a wrapper function that passes the image_path and save_preview
    def CreateProjectWrapper(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None):
        return CreateProject(sequenceID, sequenceRepeatCount, frameTime_ms, components, 
                             image_path, save_preview)
    
    example_helper.RunExample(CreateProjectWrapper)

