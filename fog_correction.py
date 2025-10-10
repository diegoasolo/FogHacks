import diffractsim
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from skimage.restoration import richardson_lucy
from diffractsim import MonochromaticField, mm, nm, FourierPhaseRetrieval,  CircularAperture, ApertureFromImage


from PIL import Image
from pathlib import Path




diffractsim.set_backend("CPU")

# Step 1: Create a clean target diffraction image
F1 = MonochromaticField(
    wavelength=532.8 * nm, extent_x=30 * mm, extent_y=30 * mm,
    Nx=512, Ny=512, intensity=0.005
)
F1.add(CircularAperture(radius = 0.5*mm))
F1.propagate(100 * mm)
I_target = np.abs(F1.get_intensity())
I_target /= I_target.max()

# Step 2: Simulate fog (as Gaussian PSF blur)
psf_sigma = 8
I_foggy = gaussian_filter(I_target, sigma=psf_sigma)

# Step 3: Construct Gaussian PSF for deconvolution
size = 2 * psf_sigma + 1
x = np.linspace(-psf_sigma, psf_sigma, size)
xv, yv = np.meshgrid(x, x)
psf = np.exp(-(xv**2 + yv**2) / (2 * psf_sigma**2))
psf /= psf.sum()

# Step 4: Deblur foggy image with Richardson-Lucy
I_deblurred = richardson_lucy(I_foggy, psf, num_iter=20)
I_deblurred /= I_deblurred.max()


# Save deblurred image to disk temporarily (normalize to 8-bit grayscale)
I_target_8bit = (255 * I_target).astype(np.uint8)
Image.fromarray(I_target_8bit).save("target_input.png")


# Step 5: Use phase retrieval to create corrective phase-only hologram
retrieval = FourierPhaseRetrieval("deblurred_input.png", "target_input.png",  (512, 512) )
retrieval.retrieve_phase_mask(200)
retrieval.save_retrieved_phase_as_image("corrective_phase_mask.png")




# Step 6: Generate new field using corrective phase mask
F2 = MonochromaticField(
    wavelength=532.8 * nm, extent_x=30 * mm, extent_y=30 * mm,
    Nx=512, Ny=512, intensity=0.005
)
F2.add(ApertureFromImage(
    amplitude_mask_path= "./diffractsim/examples/apertures/white_background.png", 
     phase_mask_path= "snowflake_phase_hologram.png", image_size=(30.0 * mm, 30.0 * mm), simulation = F2)
)



F2.propagate(100 * mm)
I_phase_output = np.abs(F2.get_intensity())
I_phase_output /= I_phase_output.max()

# Step 7: Simulate fog after projection (to reflect real-world system)
I_phase_output_fogged = gaussian_filter(I_phase_output, sigma=psf_sigma)

# Step 8: Plot everything
plt.figure(figsize=(18, 8))

plt.subplot(2, 3, 1)
plt.imshow(I_target, cmap='gray')
plt.title("Original Target")
plt.axis('off')

plt.subplot(2, 3, 2)
plt.imshow(I_foggy, cmap='gray')
plt.title("Fogged Target (Simulated)")
plt.axis('off')

plt.subplot(2, 3, 3)
plt.imshow(I_deblurred, cmap='gray')
plt.title("Deblurred Estimate")
plt.axis('off')

plt.subplot(2, 3, 4)
plt.imshow(Image.open("corrective_phase_mask.png"), cmap='gray')
plt.title("Phase Mask (Saved Image)")
plt.axis('off')

plt.subplot(2, 3, 5)
plt.imshow(I_phase_output, cmap='gray')
plt.title("Propagated from Phase Mask (No Fog)")
plt.axis('off')

plt.subplot(2, 3, 6)
plt.imshow(I_phase_output_fogged, cmap='gray')
plt.title("Final Output After Fog")
plt.axis('off')

plt.tight_layout()
plt.show()
