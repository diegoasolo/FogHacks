"""
Convert SLM phase holograms to DMD binary patterns using the Lee hologram method.

Based on the method described in:
- D.B. Conkey et al., Opt. Express (2012)
- W.H. Lee, Progress in Optics (1978)
- https://www.wavefrontshaping.net/post/id/16

The Lee method encodes a phase pattern φ(x,y) into a binary amplitude pattern by:
1. Creating an amplitude pattern: f(x,y) = (1/2)[1 + cos(2π(x-y)ν₀ - φ(x,y))]
2. Thresholding to binary: g(x,y) = 1 if f(x,y) > 1/2, else 0

The resulting binary pattern can be used with a DMD in a 4-f setup to reconstruct
the phase pattern (after filtering in the Fourier plane).
"""

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path
from matplotlib.colors import rgb_to_hsv


def load_phase_from_image(image_path, image_size=None, target_size=None):
    """
    Load phase values from a phase hologram image (HSV format).
    
    Parameters:
    -----------
    image_path : str
        Path to the phase hologram image
    image_size : tuple, optional
        Physical size of the image (size_x, size_y) in pixels
    target_size : tuple, optional
        Target size (Nx, Ny) for resampling
    
    Returns:
    --------
    phase : ndarray
        Phase values in radians, range [-π, π]
    """
    img = Image.open(Path(image_path))
    img = img.convert("RGB")
    
    if target_size is not None:
        img = img.resize(target_size, Image.Resampling.LANCZOS)
    
    imgRGB = np.asarray(img) / 255.0
    
    # Extract phase from HSV hue channel
    # phase information is entirely in hue channel, so we only care about H 
    h = rgb_to_hsv(np.moveaxis(np.array([imgRGB[:, :, 0], imgRGB[:, :, 1], imgRGB[:, :, 2]]), 0, -1))[:, :, 0]
    
    # Convert hue [0, 1] to phase [-π, π]
    phase = np.flip(h * 2 * np.pi - np.pi, axis=0)
    
    return phase


def create_lee_hologram(phase, nu0, pixel_size_x=1.0, pixel_size_y=1.0):
    """
    Create a Lee hologram amplitude pattern from a phase pattern.
    
    Parameters:
    -----------
    phase : ndarray
        Phase pattern in radians, shape (Ny, Nx)
    nu0 : float
        Carrier spatial frequency (in units of 1/pixel)
        Should be higher than the highest spatial frequency in phase
    pixel_size_x : float, optional
        Physical pixel size in x direction (for coordinate scaling)
    pixel_size_y : float, optional
        Physical pixel size in y direction (for coordinate scaling)
    
    Returns:
    --------
    amplitude_pattern : ndarray
        Amplitude pattern f(x,y) = (1/2)[1 + cos(2π(x-y)ν₀ - φ(x,y))]
    """
    Ny, Nx = phase.shape
    
    # Create coordinate arrays
    y, x = np.mgrid[0:Ny, 0:Nx]
    
    # Normalize coordinates to physical units if needed
    # For now, we'll work in pixel units
    x_norm = x * pixel_size_x
    y_norm = y * pixel_size_y
    
    # Create the Lee hologram amplitude pattern
    # f(x,y) = (1/2)[1 + cos(2π(x-y)ν₀ - φ(x,y))]
    # Note: The article uses (x-y) for the carrier direction
    carrier = 2 * np.pi * (x_norm - y_norm) * nu0
    amplitude_pattern = 0.5 * (1 + np.cos(carrier - phase))
    
    return amplitude_pattern


def threshold_to_binary(amplitude_pattern, threshold=0.5):
    """
    Threshold amplitude pattern to binary DMD pattern.
    
    Parameters:
    -----------
    amplitude_pattern : ndarray
        Amplitude pattern (0 to 1)
    threshold : float, optional
        Threshold value (default 0.5)
    
    Returns:
    --------
    binary_pattern : ndarray
        Binary pattern (0 or 1)
    """
    binary_pattern = (amplitude_pattern > threshold).astype(np.uint8)
    return binary_pattern


def estimate_carrier_frequency(phase, safety_factor=2.0):
    """
    Estimate appropriate carrier frequency based on phase pattern bandwidth.
    
    Parameters:
    -----------
    phase : ndarray
        Phase pattern in radians
    safety_factor : float
        Safety factor to ensure ν₀ > max spatial frequency of phase
    
    Returns:
    --------
    nu0 : float
        Estimated carrier frequency
    """
    # Compute 2D FFT of phase to find maximum spatial frequency
    phase_fft = np.fft.fft2(phase)
    phase_fft_abs = np.abs(phase_fft)
    
    # Find the maximum spatial frequency component
    Ny, Nx = phase.shape
    kx_max = Nx // 2
    ky_max = Ny // 2
    
    # Get frequency indices
    kx = np.fft.fftshift(np.arange(Nx) - Nx // 2)
    ky = np.fft.fftshift(np.arange(Ny) - Ny // 2)
    KX, KY = np.meshgrid(kx, ky)
    
    # Find maximum frequency magnitude
    max_freq_idx = np.unravel_index(np.argmax(phase_fft_abs[1:, 1:]), phase_fft_abs[1:, 1:].shape)
    max_freq = np.sqrt(KX[max_freq_idx[0]+1, max_freq_idx[1]+1]**2 + KY[max_freq_idx[0]+1, max_freq_idx[1]+1]**2)
    
    # Carrier frequency should be higher than this
    nu0 = safety_factor * max_freq / np.sqrt(2)  # Divide by sqrt(2) since we use (x-y) direction
    
    # Ensure minimum value
    nu0 = max(nu0, 0.1)
    
    return nu0


def convert_slm_to_dmd(phase_image_path, output_path=None, nu0=None, 
                      pixel_size_x=1.0, pixel_size_y=1.0, target_size=None,
                      visualize=True):
    """
    Convert an SLM phase hologram image to a DMD binary pattern.
    
    Parameters:
    -----------
    phase_image_path : str
        Path to the phase hologram image (HSV format)
    output_path : str, optional
        Path to save the binary DMD pattern (default: adds '_dmd.png' suffix)
    nu0 : float, optional
        Carrier spatial frequency. If None, will be estimated automatically
    pixel_size_x : float, optional
        Physical pixel size in x direction
    pixel_size_y : float, optional
        Physical pixel size in y direction
    target_size : tuple, optional
        Target size (Nx, Ny) for resampling
    visualize : bool, optional
        Whether to display visualization plots
    
    Returns:
    --------
    binary_pattern : ndarray
        Binary DMD pattern (0 or 1)
    """
    print(f"Loading phase hologram from: {phase_image_path}")
    
    # Load phase pattern
    phase = load_phase_from_image(phase_image_path, target_size=target_size)
    print(f"Loaded phase pattern: shape {phase.shape}, range [{phase.min():.3f}, {phase.max():.3f}] radians")
    
    # Estimate carrier frequency if not provided
    if nu0 is None:
        nu0 = estimate_carrier_frequency(phase)
        print(f"Estimated carrier frequency: ν₀ = {nu0:.3f} pixels⁻¹")
    else:
        print(f"Using carrier frequency: ν₀ = {nu0:.3f} pixels⁻¹")
    
    # Create Lee hologram amplitude pattern
    print("Creating Lee hologram amplitude pattern...")
    amplitude_pattern = create_lee_hologram(phase, nu0, pixel_size_x, pixel_size_y)
    
    # Threshold to binary
    print("Thresholding to binary DMD pattern...")
    binary_pattern = threshold_to_binary(amplitude_pattern)
    
    # Save binary pattern
    if output_path is None:
        base_name = Path(phase_image_path).stem
        output_path = f"{base_name}_dmd.png"
    
    binary_image = Image.fromarray(binary_pattern * 255, mode='L')
    binary_image.save(output_path)
    print(f"Saved binary DMD pattern to: {output_path}")
    
    # Visualize
    if visualize:
        fig, axes = plt.subplots(1, 2, figsize=(12, 12))
        
        # Original phase
        im1 = axes[0].imshow(phase, cmap='hsv', vmin=-np.pi, vmax=np.pi)
        axes[0].set_title('Original Phase Pattern φ(x,y)')
        axes[0].set_xlabel('x (pixels)')
        axes[0].set_ylabel('y (pixels)')
        plt.colorbar(im1, ax=axes[0], label='Phase (radians)', ticks=[-np.pi, -np.pi/2, 0, np.pi/2, np.pi], shrink=0.7)
        
        # # Amplitude pattern
        # im2 = axes[0, 1].imshow(amplitude_pattern, cmap='gray', vmin=0, vmax=1)
        # axes[0, 1].set_title('Lee Hologram Amplitude Pattern f(x,y)')
        # axes[0, 1].set_xlabel('x (pixels)')
        # axes[0, 1].set_ylabel('y (pixels)')
        # plt.colorbar(im2, ax=axes[0, 1], label='Amplitude')
        
        # Binary pattern
        im3 = axes[1].imshow(binary_pattern, cmap='gray', vmin=0, vmax=1)
        axes[1].set_title('Binary DMD Pattern g(x,y)')
        axes[1].set_xlabel('x (pixels)')
        axes[1].set_ylabel('y (pixels)')
        
        # # Zoomed view of binary pattern
        # zoom_size = min(200, phase.shape[0]//4, phase.shape[1]//4)
        # center_y, center_x = phase.shape[0]//2, phase.shape[1]//2
        # zoom_slice_y = slice(center_y - zoom_size, center_y + zoom_size)
        # zoom_slice_x = slice(center_x - zoom_size, center_x + zoom_size)
        
        # im4 = axes[1, 1].imshow(binary_pattern[zoom_slice_y, zoom_slice_x], 
        #                         cmap='gray', vmin=0, vmax=1)
        # axes[1, 1].set_title(f'Binary DMD Pattern (Zoomed {zoom_size*2}x{zoom_size*2})')
        # axes[1, 1].set_xlabel('x (pixels)')
        # axes[1, 1].set_ylabel('y (pixels)')
    
        plt.tight_layout()
        
        # Save visualization
        viz_path = Path(output_path).stem + '_visualization.png'
        plt.savefig(viz_path, dpi=150, bbox_inches='tight')
        print(f"Saved visualization to: {viz_path}")
        
        plt.show()
    
    return binary_pattern


if __name__ == "__main__":
    # Convert the rings phase hologram to DMD pattern
    phase_image_path = "rings_phase_hologram.png"
    
    # Check if file exists
    if not Path(phase_image_path).exists():
        print(f"Error: Phase hologram file '{phase_image_path}' not found.")
        print("Please make sure the file exists in the current directory.")
    else:
        # Convert with automatic carrier frequency estimation
        binary_pattern = convert_slm_to_dmd(
            phase_image_path,
            output_path="rings_phase_hologram_dmd.png",
            target_size=None, # dont change just set size of phase mask accoruding to DMD
            nu0=None,  # Auto-estimate
            visualize=True
        )
        
        print(f"Binary pattern shape: {binary_pattern.shape}")
        print(f"On pixels: {np.sum(binary_pattern)} ({100*np.sum(binary_pattern)/binary_pattern.size:.1f}%)")
        print(f"Off pixels: {np.sum(1-binary_pattern)} ({100*np.sum(1-binary_pattern)/binary_pattern.size:.1f}%)")

