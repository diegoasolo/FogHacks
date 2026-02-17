"""
Display DMD patterns that are already padded to 912x1140.
Skips resize when image matches DMD dimensions to avoid stretching from interpolation.
Use for pre-padded images like rings_phase_hologram_padded_dmd.png.

If display still looks slightly stretched (e.g. circles appear elliptical), try:
  --compress-v=0.95   to pre-compress vertically (fixes vertical stretch)
  --compress-h=0.95   to pre-compress horizontally (fixes horizontal stretch)
Adjust the value (0.9-1.0) until circles look round.
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


def load_padded_dmd_image(image_path, dmd_width=DMD_WIDTH, dmd_height=DMD_HEIGHT,
                          compress_v=1.0, compress_h=1.0):
    """
    Load an image for DMD display. If already 912x1140, use as-is (no resize).
    compress_v, compress_h: aspect correction (0.9-1.0) - pre-compress to counteract display stretch.
    E.g. compress_v=0.95 if display stretches vertically.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"Failed to load image: {image_path}")
    orig_h, orig_w = img.shape[:2]

    if orig_w == dmd_width and orig_h == dmd_height:
        dmd_pattern = img.copy()
        print(f"  Image already {dmd_width}x{dmd_height} - using as-is (no resize)")
    else:
        dmd_pattern = cv2.resize(img, (dmd_width, dmd_height), interpolation=cv2.INTER_NEAREST)
        print(f"  Original: {orig_w}x{orig_h} -> resized to {dmd_width}x{dmd_height}")

    # Aspect correction: pre-compress to counteract display stretch
    if compress_v != 1.0 or compress_h != 1.0:
        new_w = int(dmd_width * compress_h)
        new_h = int(dmd_height * compress_v)
        dmd_pattern = cv2.resize(dmd_pattern, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        padded = np.zeros((dmd_height, dmd_width), dtype=dmd_pattern.dtype)
        y0 = (dmd_height - new_h) // 2
        x0 = (dmd_width - new_w) // 2
        padded[y0:y0 + new_h, x0:x0 + new_w] = dmd_pattern
        dmd_pattern = padded
        print(f"  Aspect correction: compress_v={compress_v}, compress_h={compress_h}")

    if len(dmd_pattern.shape) == 2:
        dmd_pattern = np.expand_dims(dmd_pattern, axis=2)
    return dmd_pattern


def CreateProject(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None, image_path=None, save_preview=False, compress_v=1.0, compress_h=1.0):
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

    # Load without resize when already correct size; apply aspect correction if requested
    dmd_pattern = load_padded_dmd_image(image_path, dmd_width, dmd_height, compress_v, compress_h)

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


def _parse_float_arg(flag, default=1.0):
    """Parse --flag=value or --flag value from sys.argv."""
    for i, a in enumerate(sys.argv):
        if a.startswith(flag + '='):
            try:
                return float(a.split('=')[1])
            except (IndexError, ValueError):
                return default
        if a == flag and i + 1 < len(sys.argv):
            try:
                return float(sys.argv[i + 1])
            except ValueError:
                return default
    return default


if __name__ == "__main__":
    image_path = None
    save_preview = False
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args:
        image_path = args[0]
    save_preview = '--save-preview' in sys.argv
    compress_v = _parse_float_arg('--compress-v')
    compress_h = _parse_float_arg('--compress-h')

    # Strip custom args for example_helper
    to_remove = [image_path, '--save-preview']
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a.startswith('--compress-v=') or a.startswith('--compress-h='):
            to_remove.append(a)
        elif a in ('--compress-v', '--compress-h') and i + 1 < len(sys.argv):
            to_remove.extend([a, sys.argv[i + 1]])
            i += 1
        i += 1
    for arg in to_remove:
        if arg and arg in sys.argv:
            sys.argv.remove(arg)

    def CreateProjectWrapper(sequenceID=1, sequenceRepeatCount=10, frameTime_ms=-1, components=None):
        return CreateProject(sequenceID, sequenceRepeatCount, frameTime_ms, components,
                             image_path, save_preview, compress_v, compress_h)

    example_helper.RunExample(CreateProjectWrapper)
