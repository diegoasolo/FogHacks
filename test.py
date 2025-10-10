from diffractsim_main import diffractsim
diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim_main.diffractsim import MonochromaticField, ApertureFromImage, Lens, mm, um, nm, cm, FourierPhaseRetrieval, PSF_convolution, apply_transfer_function, bd
import numpy as np


# Generate a Fourier plane phase hologram
#PR = FourierPhaseRetrieval(target_amplitude_path = './diffractsim_main/examples/apertures/rings.jpg', new_size= (400,400), pad = (200,200))
#PR.retrieve_phase_mask(max_iter = 200, method = 'Conjugate-Gradient')
#PR.save_retrieved_phase_as_image('rings_phase_hologram.png')


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



"""Monte Carlo Henyey–Greenstein PSF (randomized)"""
def _sample_hg_cos_theta(rng, g, n):
    if abs(g) < 1e-6:
        # isotropic: cos(theta) = 1 - 2U
        U = rng.random(n)
        return 1.0 - 2.0*U
    U = rng.random(n)
    num = 1.0 - g*g
    denom = 1.0 - g + 2.0*g*U
    cos_theta = (1.0 + g*g - (num/denom)) / (2.0*g)
    return cos_theta

def _box_blur(psf, k):
    if k <= 1:
        return psf
    pad = k//2
    psf_p = np.pad(psf, ((pad,pad),(pad,pad)), mode='edge')
    kernel = np.ones((k,k), dtype=np.float64) / (k*k)
    out = np.zeros_like(psf)
    # simple conv
    for i in range(out.shape[0]):
        ii = i
        for j in range(out.shape[1]):
            jj = j
            out[i,j] = np.sum(psf_p[ii:ii+k, jj:jj+k] * kernel)
    return out

def make_random_hg_psf(F, g, L_eff, theta_max_rad, num_samples=50000, seed=123, blur_kernel=5):
    rng = np.random.default_rng(seed)
    Ny, Nx = int(F.Ny), int(F.Nx)
    cx, cy = Nx//2, Ny//2
    dx = float(F.dx); dy = float(F.dy)

    psf = np.zeros((Ny, Nx), dtype=np.float64)

    cos_theta = _sample_hg_cos_theta(rng, g, num_samples)
    theta = np.arccos(np.clip(cos_theta, -1.0, 1.0))
    
    # Debug: Print angle statistics
    print(f"Total samples: {num_samples}")
    print(f"Max theta before filtering: {np.max(theta)*180/np.pi:.2f} degrees")
    print(f"Mean theta before filtering: {np.mean(theta)*180/np.pi:.2f} degrees")
    
    # enforce max angle
    m = theta <= float(theta_max_rad)
    theta = theta[m]
    print(f"Angles within theta_max: {theta.size} ({theta.size/num_samples*100:.1f}%)")
    
    if theta.size == 0:
        # fallback to center spike
        print("No angles within theta_max, using center spike")
        psf[cy, cx] = 1.0
        return psf
    else:
        print(f"Max theta after filtering: {np.max(theta)*180/np.pi:.2f} degrees")
    phi = 2.0*np.pi * rng.random(theta.size)

    # small-angle mapping to plane: r ≈ L_eff * theta
    r = float(L_eff) * theta
    x = r * np.cos(phi)
    y = r * np.sin(phi)
    
    print(f"Max displacement: {np.max(r)/mm:.2f} mm")
    print(f"Grid size: {Nx} x {Ny}, pixel size: {dx/mm:.3f} x {dy/mm:.3f} mm")

    ix = np.rint(x / dx).astype(int) + cx
    iy = np.rint(y / dy).astype(int) + cy

    # accumulate samples within bounds
    mask = (ix >= 0) & (ix < Nx) & (iy >= 0) & (iy < Ny)
    print(f"Samples within grid bounds: {np.sum(mask)} ({np.sum(mask)/theta.size*100:.1f}%)")
    
    if np.sum(mask) == 0:
        print("No samples within grid bounds, using center spike")
        psf[cy, cx] = 1.0
        return psf
    
    ix = ix[mask]; iy = iy[mask]
    np.add.at(psf, (iy, ix), 1.0)

    # optional light smoothing to reduce aliasing
    psf = _box_blur(psf, blur_kernel)
    return psf

# Parameters for randomized Mie scattering PSF
g = 0.5  # anisotropy parameter (0=isotropic, →1 forward-peaked)
# Use a smaller effective path to get more spread within the grid
L_eff = 2.0 * mm  # effective remaining path length that maps angle to displacement
theta_max = np.deg2rad(30.0)  # increase max angle to 30 degrees
num_samples = 50000  # reduce samples for faster computation
seed = 2025


# Create randomized HG PSF on the simulation grid (NumPy), then convert to backend array
PSF_np = make_random_hg_psf(F, g=g, L_eff=L_eff, theta_max_rad=theta_max, num_samples=num_samples, seed=seed, blur_kernel=1)
PSF = bd.array(PSF_np)

# Normalize PSF (unity DC gain)
PSF = PSF / (bd.sum(PSF) * F.dx * F.dy)



# Convolve the current complex field with the PSF (coherent convolution)
F.E = PSF_convolution(F, F.E, F.λ, PSF, scale_factor = 1)

# propagate to the Fourier plane at z
F.propagate(z)


# plot colors (reconstructed image) at z (Fourier plane)
rgb = F.get_colors()
F.plot_colors(rgb)

# Debug: Print PSF statistics
print(f"g value: {g}")
print(f"PSF max value: {bd.max(PSF)}")
print(f"PSF sum: {bd.sum(PSF) * F.dx * F.dy}")
print(f"Number of non-zero PSF elements: {bd.sum(PSF > 0)}")
print(f"PSF center value: {PSF[PSF.shape[0]//2, PSF.shape[1]//2]}")

# #plot longitudinal profile
# longitudinal_profile_rgb, longitudinal_profile_E, extent = F.get_longitudinal_profile( start_distance = 0*cm , end_distance = z , steps = 80) 
# #plot colors
# F.plot_longitudinal_profile_colors(longitudinal_profile_rgb = longitudinal_profile_rgb, extent = extent)
# print(longitudinal_profile_rgb.shape)


# F.plot_longitudinal_profile_intensity(longitudinal_profile_E = longitudinal_profile_E, extent = extent, square_root = True)
# print(longitudinal_profile_E.shape)
