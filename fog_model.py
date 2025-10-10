import diffractsim
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from skimage.restoration import richardson_lucy

diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim import MonochromaticField, ApertureFromImage, Lens, mm, nm, cm, FourierPhaseRetrieval, CircularAperture


F = MonochromaticField(
    wavelength=532.8 * nm, extent_x=30 * mm, extent_y=30 * mm, Nx=2400, Ny=2400, intensity = 0.005
)

F.add(CircularAperture(radius = 0.5*mm))

F.propagate(100 * mm)

I_target = np.abs(F.get_intensity())  # Target image
I_target /= I_target.max()

I_clear = np.abs(F.get_intensity())
I_clear /= I_clear.max()

psf_sigma = 8 #change this value to simulate different levels of fog
I_foggy = gaussian_filter(I_clear, sigma=psf_sigma)

retrieval = FourierPhaseRetrieval(
    I_target=I_target,
    I_output=I_foggy,
    iterations=100,
    support_threshold=0.01
)

retrieval.run()

plt.figure(figsize=(18, 5))

plt.subplot(1, 3, 1)
plt.imshow(I_clear, cmap='gray')
plt.title("Original (Diffracted)")
plt.axis('off')

plt.subplot(1, 3, 2)
plt.imshow(I_foggy, cmap='gray')
plt.title("Simulated Fog (PSF Blurred)")
plt.axis('off')

plt.tight_layout()
plt.show()

#rgb = F.get_colors()
#F.plot_colors(rgb, xlim=[-3*mm,3*mm], ylim=[-3*mm,3*mm])