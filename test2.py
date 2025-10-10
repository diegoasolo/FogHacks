from diffractsim_main import diffractsim
diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim_main.diffractsim import MonochromaticField, ApertureFromImage, Lens, mm, um, nm, cm, FourierPhaseRetrieval, PSF_convolution, apply_transfer_function, bd


# # Generate a Fourier plane phase hologram
# PR = FourierPhaseRetrieval(target_amplitude_path = './diffractsim_main/examples/apertures/rings.jpg', new_size= (400,400), pad = (200,200))
# PR.retrieve_phase_mask(max_iter = 200, method = 'Conjugate-Gradient')
# PR.save_retrieved_phase_as_image('rings_phase_hologram.png')


#Add a plane wave
F = MonochromaticField(
    wavelength=532.8 * nm, extent_x=30 * mm, extent_y=30 * mm, Nx=2400, Ny=2400, intensity = 0.005
)


# load the hologram as a phase mask aperture
F.add(ApertureFromImage(
     amplitude_mask_path= "./diffractsim_main/examples/apertures/white_background.png", 
     phase_mask_path= "rings_phase_hologram.png", image_size=(10.0 * mm, 10.0 * mm), simulation = F))



# plot colors at z = 0
#rgb = F.get_colors()
#F.plot_colors(rgb)


# set distance to image plane 
z = 200*cm

# add lens to focus the hologram at z 
F.add(Lens(f = z))



# Build a Henyey-Greenstein PSF for Mie scattering (forward-peaked)
def hg_phase_function(theta, g):
    """Henyey-Greenstein phase function"""
    ct = bd.cos(theta)
    denom = (1 + g*g - 2*g*ct)**1.5
    return (1 - g*g) / (4*bd.pi*denom)

# Parameters for Mie scattering
g = 0.5  # anisotropy parameter (0=isotropic, →1 forward-peaked)
fog_scale = 300 * um  # characteristic scattering scale in meters
theta_max = bd.pi/12  # 15 degrees max angle

# Create a proper Henyey-Greenstein PSF that varies with g
# Map spatial coordinates to scattering angles
r = bd.sqrt(F.xx**2 + F.yy**2)
theta = r / fog_scale  # small-angle approximation: theta ≈ r/L

# Create Henyey-Greenstein PSF - apply to all angles, not just within theta_max
PSF = hg_phase_function(theta, g)

# Apply a soft cutoff instead of hard mask to make g value more visible
# This creates a gradual falloff rather than a sharp cutoff
cutoff_factor = bd.exp(-(theta / theta_max)**4)  # Soft exponential cutoff
PSF = PSF * cutoff_factor

# Normalize PSF so that its discrete integral equals 1 (unity DC gain)
PSF = PSF / (bd.sum(PSF) * F.dx * F.dy)

# Debug: Print PSF statistics
print(f"g value: {g}")
print(f"PSF max value: {bd.max(PSF)}")
print(f"PSF sum: {bd.sum(PSF) * F.dx * F.dy}")
print(f"Number of non-zero PSF elements: {bd.sum(PSF > 0)}")
print(f"PSF center value: {PSF[PSF.shape[0]//2, PSF.shape[1]//2]}")
print(f"PSF effective width (FWHM estimate): {bd.sum(PSF > bd.max(PSF)/2) * F.dx / mm:.2f} mm")

# Convolve the current complex field with the PSF (coherent convolution)
F.E = PSF_convolution(F, F.E, F.λ, PSF, scale_factor = 1)



# propagate to the Fourier plane at z
F.propagate(z)


# plot colors (reconstructed image) at z (Fourier plane)
rgb = F.get_colors()
F.plot_colors(rgb)



# #plot longitudinal profile
# longitudinal_profile_rgb, longitudinal_profile_E, extent = F.get_longitudinal_profile( start_distance = 0*cm , end_distance = z , steps = 80) 
# #plot colors
# F.plot_longitudinal_profile_colors(longitudinal_profile_rgb = longitudinal_profile_rgb, extent = extent)
# print(longitudinal_profile_rgb.shape)


# F.plot_longitudinal_profile_intensity(longitudinal_profile_E = longitudinal_profile_E, extent = extent, square_root = True)
# print(longitudinal_profile_E.shape)
