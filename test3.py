import numpy as np
import matplotlib.pyplot as plt
import diffractsim
import cv2
from typing import Tuple, Optional
from scipy import ndimage

from diffractsim import MonochromaticField, ApertureFromImage, Lens, mm, nm, cm, FourierPhaseRetrieval

diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

class RayBasedPhaseMask:
    """
    Custom ray-based physics model for simulating light propagation through phase masks.
    """
    
    def __init__(self, wavelength: float = 532.8e-9, pixel_pitch: float = 10e-6, focal_length: float = 0.1):
        """
        Initialize the ray-based phase mask simulator.
        
        Args:
            wavelength: Wavelength of light in meters
            pixel_pitch: Physical size of each pixel in meters  
            focal_length: Distance to Fourier plane in meters
        """
        self.wavelength = wavelength
        self.pixel_pitch = pixel_pitch
        self.focal_length = focal_length
        self.k = 2 * np.pi / wavelength
        self.phase_mask = None
        
    def retrieve_hsv_phase_mask(self, target_image_path: str, output_size: Tuple[int, int] = (256, 256)) -> np.ndarray:
        """
        Retrieve HSV phase mask using DiffractSim's FourierPhaseRetrieval class.

        Args:
            target_image_path: Path to target image file
            output_size: Size of the phase mask

        Returns:
            phase_mask: Generated phase mask in radians
        """
        # Verify the image exists
        print(f"Loading target image from: {target_image_path}")
        target_img = cv2.imread(target_image_path, cv2.IMREAD_GRAYSCALE)
        if target_img is None:
            raise FileNotFoundError(f"Could not load image from {target_image_path}")

        print("Initializing FourierPhaseRetrieval...")
        # Initialize FourierPhaseRetrieval with your image path
        PR = FourierPhaseRetrieval(target_amplitude_path=target_image_path, new_size=output_size, pad=(100, 100))

        print("Retrieving phase mask...")
        # Retrieve phase mask
        PR.retrieve_phase_mask(max_iter=200, method='Conjugate-Gradient')

        print("Saving retrieved phase mask as image...")
        # Save the phase mask as an image
        PR.save_retrieved_phase_as_image('retrieved_phase_hologram.png')

        # Load the saved phase mask image and store it in self.phase_mask
        phase_mask_img = cv2.imread('retrieved_phase_hologram.png', cv2.IMREAD_GRAYSCALE)
        if phase_mask_img is None:
            raise FileNotFoundError("Failed to load the saved phase mask image from DiffractSim.")

        # Convert from 0-255 to -π to π range
        self.phase_mask = (phase_mask_img.astype(float) / 255.0) * 2 * np.pi - np.pi
        print(f"Phase mask loaded successfully with shape: {self.phase_mask.shape}")
        print(f"Phase range: {np.min(self.phase_mask):.3f} to {np.max(self.phase_mask):.3f}")

        return self.phase_mask
    
    def calculate_ray_angles(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate ray deflection angles based on phase gradients.
        
        Returns:
            theta_x, theta_y: Ray angles in x and y directions
        """
        if self.phase_mask is None:
            raise ValueError("Phase mask not set. Call retrieve_hsv_phase_mask() first.")
            
        # Calculate phase gradients
        grad_y, grad_x = np.gradient(self.phase_mask, self.pixel_pitch)
        
        # Convert phase gradients to ray angles
        theta_x = self.wavelength * grad_x / (2 * np.pi)
        theta_y = self.wavelength * grad_y / (2 * np.pi)
        
        return theta_x, theta_y
    
    def ray_trace_with_lens(self, lens_focal_length: float = 0.05, image_plane_size: Tuple[int, int] = (512, 512)) -> np.ndarray:
        """
        Trace rays through phase mask and then through a converging lens.
        Shows the image formed at the lens focal plane.
        
        Args:
            lens_focal_length: Focal length of the converging lens in meters
            image_plane_size: Size of the image plane at focal distance
            
        Returns:
            intensity_distribution: 2D intensity at lens focal plane
        """
        if self.phase_mask is None:
            raise ValueError("Phase mask not set. Call retrieve_hsv_phase_mask() first.")
            
        # Get phase mask dimensions
        height, width = self.phase_mask.shape
        
        # Calculate ray deflection angles from phase mask
        theta_x, theta_y = self.calculate_ray_angles()
        
        # For a thin lens: rays with angle θ are focused to position f*θ at the focal plane
        # This is the key physics: angle gets converted to position by the lens
        x_image = lens_focal_length * theta_x
        y_image = lens_focal_length * theta_y
        
        # Create image plane coordinate system
        image_height, image_width = image_plane_size
        # Scale the field of view based on the maximum ray angles and focal length
        max_angle = np.max(np.sqrt(theta_x**2 + theta_y**2))
        image_extent = 2.0 * lens_focal_length * max_angle * 1.2  # 20% margin
        
        # Convert to pixel coordinates on image plane
        pixel_x = ((x_image + image_extent/2) / image_extent * image_width).astype(int)
        pixel_y = ((y_image + image_extent/2) / image_extent * image_height).astype(int)
        
        # Find valid pixels (within bounds)
        valid_mask = ((pixel_x >= 0) & (pixel_x < image_width) & 
                     (pixel_y >= 0) & (pixel_y < image_height))
        
        # Initialize intensity array
        intensity = np.zeros(image_plane_size, dtype=float)
        
        # Accumulate intensity using histogram
        if np.any(valid_mask):
            x_valid = pixel_x[valid_mask]
            y_valid = pixel_y[valid_mask]
            
            intensity, _, _ = np.histogram2d(
                y_valid, x_valid,
                bins=[image_height, image_width],
                range=[[0, image_height], [0, image_width]]
            )
            
            # Apply light Gaussian smoothing for better visualization
            intensity = ndimage.gaussian_filter(intensity, sigma=0.8)
            
        return intensity

    def ray_trace_to_fourier_plane(self, fourier_plane_size: Tuple[int, int] = (512, 512)) -> np.ndarray:
        """
        Trace rays from phase mask to Fourier plane using geometric optics.
        
        Args:
            fourier_plane_size: Size of the output Fourier plane
            
        Returns:
            intensity_distribution: 2D intensity at Fourier plane
        """
        if self.phase_mask is None:
            raise ValueError("Phase mask not set. Call retrieve_hsv_phase_mask() first.")
            
        # Get phase mask dimensions
        height, width = self.phase_mask.shape
        
        # Create coordinate grids for phase mask
        x_coords = np.arange(width) * self.pixel_pitch - (width * self.pixel_pitch / 2)
        y_coords = np.arange(height) * self.pixel_pitch - (height * self.pixel_pitch / 2)
        X, Y = np.meshgrid(x_coords, y_coords)
        
        # Calculate ray deflection angles
        theta_x, theta_y = self.calculate_ray_angles()
        
        # Calculate ray positions at Fourier plane
        x_fourier = X + self.focal_length * theta_x
        y_fourier = Y + self.focal_length * theta_y
        
        # Create Fourier plane coordinate system
        fourier_height, fourier_width = fourier_plane_size
        fourier_extent_x = fourier_width * self.pixel_pitch
        fourier_extent_y = fourier_height * self.pixel_pitch
        
        # Convert to pixel coordinates on Fourier plane
        pixel_x = ((x_fourier + fourier_extent_x/2) / fourier_extent_x * fourier_width).astype(int)
        pixel_y = ((y_fourier + fourier_extent_y/2) / fourier_extent_y * fourier_height).astype(int)
        
        # Find valid pixels (within bounds)
        valid_mask = ((pixel_x >= 0) & (pixel_x < fourier_width) & 
                     (pixel_y >= 0) & (pixel_y < fourier_height))
        
        # Initialize intensity array
        intensity = np.zeros(fourier_plane_size, dtype=float)
        
        # Accumulate intensity using histogram with proper normalization
        if np.any(valid_mask):
            x_valid = pixel_x[valid_mask]
            y_valid = pixel_y[valid_mask]
            
            # Use weighted histogram for smoother results
            weights = np.ones_like(x_valid, dtype=float)
            
            intensity, _, _ = np.histogram2d(
                y_valid, x_valid,
                bins=[fourier_height, fourier_width],
                range=[[0, fourier_height], [0, fourier_width]],
                weights=weights
            )
            
            # Apply Gaussian smoothing to reduce pixelation
            intensity = ndimage.gaussian_filter(intensity, sigma=1.0)
            
        return intensity
    
    def visualize_results(self, target_image_path: Optional[str] = None, show_lens: bool = True, lens_focal_length: float = 0.05):
        """
        Visualize the phase mask and ray tracing results.
        
        Args:
            target_image_path: Optional path to show target image comparison
            show_lens: Whether to show lens-focused reconstruction
            lens_focal_length: Focal length for lens reconstruction
        """
        if self.phase_mask is None:
            raise ValueError("Phase mask not set. Call retrieve_hsv_phase_mask() first.")
        
        # Choose subplot layout based on whether to show lens reconstruction
        if show_lens:
            fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        else:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            
        # Phase mask (HSV colormap)
        im1 = axes[0,0].imshow(self.phase_mask, cmap='hsv', vmin=-np.pi, vmax=np.pi)
        axes[0,0].set_title('HSV Phase Mask')
        axes[0,0].set_xlabel('X (pixels)')
        axes[0,0].set_ylabel('Y (pixels)')
        plt.colorbar(im1, ax=axes[0,0], label='Phase (radians)')
        
        # Ray angles
        theta_x, theta_y = self.calculate_ray_angles()
        angle_magnitude = np.sqrt(theta_x**2 + theta_y**2)
        im2 = axes[0,1].imshow(angle_magnitude, cmap='viridis')
        axes[0,1].set_title(f'Ray Deflection Magnitude\nMax: {np.max(angle_magnitude):.2e} rad')
        axes[0,1].set_xlabel('X (pixels)')
        axes[0,1].set_ylabel('Y (pixels)')
        plt.colorbar(im2, ax=axes[0,1], label='Angle (rad)')
        
        # Free space propagation result
        fourier_result = self.ray_trace_to_fourier_plane()
        if show_lens:
            im3 = axes[1,0].imshow(fourier_result, cmap='hot')
            axes[1,0].set_title(f'Free Space Propagation\nMax Intensity: {np.max(fourier_result):.1f}')
        else:
            im3 = axes[1,0].imshow(fourier_result, cmap='hot')
            axes[1,0].set_title(f'Ray-Traced Fourier Plane\nMax Intensity: {np.max(fourier_result):.1f}')
        axes[1,0].set_xlabel('X (pixels)')
        axes[1,0].set_ylabel('Y (pixels)')
        plt.colorbar(im3, ax=axes[1,0], label='Intensity')
        
        # Lens reconstruction (if enabled)
        if show_lens:
            lens_result = self.ray_trace_with_lens(lens_focal_length=lens_focal_length)
            im4 = axes[0,2].imshow(lens_result, cmap='hot')
            axes[0,2].set_title(f'Lens Reconstruction (f={lens_focal_length*1000:.1f}mm)\nMax Intensity: {np.max(lens_result):.1f}')
            axes[0,2].set_xlabel('X (pixels)')
            axes[0,2].set_ylabel('Y (pixels)')
            plt.colorbar(im4, ax=axes[0,2], label='Intensity')
            
            # Target image comparison
            target_subplot = axes[1,1]
            lens_info_subplot = axes[1,2]
        else:
            target_subplot = axes[1,1]
            lens_info_subplot = None
        
        # Target image comparison
        if target_image_path:
            try:
                target_img = cv2.imread(target_image_path, cv2.IMREAD_GRAYSCALE)
                if target_img is not None:
                    target_img = cv2.resize(target_img, (256, 256))
                    target_subplot.imshow(target_img, cmap='gray')
                    target_subplot.set_title('Original Target Image')
                    target_subplot.set_xlabel('X (pixels)')
                    target_subplot.set_ylabel('Y (pixels)')
                else:
                    target_subplot.text(0.5, 0.5, f'Could not load:\n{target_image_path}', 
                                      ha='center', va='center', transform=target_subplot.transAxes)
                    target_subplot.set_title('Target Image (Failed to Load)')
            except Exception as e:
                target_subplot.text(0.5, 0.5, f'Error loading image:\n{str(e)}', 
                                  ha='center', va='center', transform=target_subplot.transAxes)
                target_subplot.set_title('Target Image (Error)')
        else:
            target_subplot.text(0.5, 0.5, 'No target image provided', 
                              ha='center', va='center', transform=target_subplot.transAxes)
            target_subplot.set_title('Target Image')
            
            
        # Remove axis ticks for info subplots
        info_subplots = [target_subplot]
        if lens_info_subplot is not None:
            info_subplots.append(lens_info_subplot)
            
        for ax in info_subplots:
            ax.set_xticks([])
            ax.set_yticks([])
            
        plt.tight_layout()
        
        # Print some diagnostic info
        print(f"\nDiagnostic Information:")
        print(f"Phase mask range: {np.min(self.phase_mask):.3f} to {np.max(self.phase_mask):.3f} rad")
        print(f"Ray angle range: {np.min(angle_magnitude):.2e} to {np.max(angle_magnitude):.2e} rad")
        print(f"Free space intensity range: {np.min(fourier_result):.1f} to {np.max(fourier_result):.1f}")
        if show_lens:
            print(f"Lens reconstruction intensity range: {np.min(lens_result):.1f} to {np.max(lens_result):.1f}")
        
        plt.show()

# Simple usage example
def demo():
    """
    Simple demonstration using your own image file.
    """
    # Initialize ray-based simulator
    simulator = RayBasedPhaseMask(
        wavelength=632.8e-9,  # Red HeNe laser
        pixel_pitch=10e-6,    # 10 micron pixels
        focal_length=0.1      # 10 cm focal length
    )
    
    # Use your image file path here
    your_image_path = 'your_image.png'  # Replace with your actual file path
    
    print(f"Processing image: {your_image_path}")
    
    # Retrieve phase mask from your image
    phase_mask = simulator.retrieve_hsv_phase_mask(your_image_path, output_size=(256, 256))
    
    # Run ray tracing
    fourier_result = simulator.ray_trace_to_fourier_plane(fourier_plane_size=(512, 512))
    
    # Show results
    simulator.visualize_results(your_image_path)
    
    print(f"Phase mask shape: {phase_mask.shape}")
    print(f"Fourier plane result shape: {fourier_result.shape}")
    print(f"Max intensity at Fourier plane: {np.max(fourier_result):.2f}")
    
    return simulator

# Direct usage - just replace 'your_image.png' with your file path
if __name__ == "__main__":
    # For direct usage:
    simulator = RayBasedPhaseMask()
    
    # Put your image path here
    my_image_path = './diffractsim/examples/apertures/rings.jpg'  # <-- Change this to your file path
    
    phase_mask = simulator.retrieve_hsv_phase_mask(my_image_path, output_size=(256, 256))
    simulator.visualize_results(my_image_path, show_lens=True)