"""
Display DMD patterns that are already padded to 912x1140.
Skips resize when image matches DMD dimensions to avoid any stretching from interpolation.
Use this for pre-padded images like rings_phase_hologram_padded_dmd.png.
"""

import ajiledriver as aj
import cv2
import numpy as np

import sys
import os.path
sys.path.insert(0, os.path.split(os.path.realpath(__file__))[0] + "/../../common/python/")
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import example_helper

# DMD 4500 native resolution (912 x 1140 mirrors)
DMD_WIDTH = 912
DMD_HEIGHT = 1140


def load_padded_dmd_image(image_path, dmd_width=DMD_WIDTH, dmd_height=DMD_HEIGHT):
    """
    Load an image for DMD display. If already 912x1140, use as-is (no resize)
    to avoid any stretching from interpolation. Only resize when dimensions differ.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"Failed to load image: {image_path}")
    orig_h, orig_w = img.shape[:2]

    if orig_w == dmd_width and orig_h == dmd_height:
        # Already correct size - use raw pixels, NO resize (avoids stretching)
        dmd_pattern = img.copy()
        print(f"  Image already {dmd_width}x{dmd_height} - using as-is (no resize)")
    else:
        # Resize only when needed - INTER_NEAREST preserves binary edges
        dmd_pattern = cv2.resize(img, (dmd_width, dmd_height), interpolation=cv2.INTER_NEAREST)
        print(f"  Original: {orig_w}x{orig_h} -> resized to {dmd_width}x{dmd_height}")

    # Ensure shape (height, width, 1) for ajile ReadFromMemory
    if len(dmd_pattern.shape) == 2:
        dmd_pattern = np.expand_dims(dmd_pattern, axis=2)
    return dmd_pattern


def CreateProject(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None, image_path=None, save_preview=False):
    """
    Display a pre-padded DMD pattern (912x1140) without stretching.
    Skips resize when dimensions match to preserve exact pixel-to-mirror mapping.
    """
    projectName = "display_dmd_pattern_padded"
    currentPath = os.path.dirname(os.path.realpath(__file__))

    if image_path is None:
        image_path = os.path.join(currentPath, "rings_phase_hologram_padded_dmd.png")
    elif not os.path.isabs(image_path):
        image_path = os.path.join(currentPath, image_path)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"DMD pattern image not found: {image_path}")

    print(f"Loading DMD pattern from: {image_path}")

    if frameTime_ms < 0:
        frameTime_ms = 10000
    numImages = 1

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

    # Load without resize when already correct size
    dmd_pattern = load_padded_dmd_image(image_path, dmd_width, dmd_height)

    project = aj.Project(projectName)
    if components is not None:
        project.SetComponents(components)

    testImage = aj.Image(1)
    read_result = testImage.ReadFromMemory(dmd_pattern, 8, aj.ROW_MAJOR_ORDER, aj.DMD_4500_DEVICE_TYPE)
    if read_result != aj.ERROR_NONE:
        raise RuntimeError(f"Failed to load image into DMD format (code {read_result})")
    project.AddImage(testImage)
    print(f"Image added to project with ID: {testImage.ID()}")

    image_name = os.path.splitext(os.path.basename(image_path))[0]
    example_helper.AddPreviewImage(project, dmd_pattern, testImage.ID(), testImage.ID(),
                                   f"{image_name}_dmd_1to1", 1)

    if save_preview:
        preview_path = os.path.join(currentPath, f"{image_name}_dmd_preview_1to1.png")
        cv2.imwrite(preview_path, dmd_pattern)
        print(f"Saved 1:1 DMD preview to: {preview_path}")

    project.AddSequence(aj.Sequence(sequenceID, projectName, aj.DMD_4500_DEVICE_TYPE, aj.SEQ_TYPE_PRELOAD, sequenceRepeatCount))
    project.AddSequenceItem(aj.SequenceItem(sequenceID, 1))

    for i in range(numImages):
        frame = aj.Frame()
        frame.SetSequenceID(sequenceID)
        frame.SetImageID(i + 1)
        frame.SetFrameTimeMSec(frameTime_ms)
        project.AddFrame(frame)

    print(f"Project created successfully. Loaded: {os.path.basename(image_path)}")
    return project


if __name__ == "__main__":
    image_path = None
    save_preview = False
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args:
        image_path = args[0]
    save_preview = '--save-preview' in sys.argv

    for arg in [image_path, '--save-preview']:
        if arg and arg in sys.argv:
            sys.argv.remove(arg)

    def CreateProjectWrapper(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None):
        return CreateProject(sequenceID, sequenceRepeatCount, frameTime_ms, components,
                             image_path, save_preview)

    example_helper.RunExample(CreateProjectWrapper)
