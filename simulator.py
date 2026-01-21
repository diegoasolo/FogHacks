from diffractsim_main import diffractsim
diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim_main.diffractsim import MonochromaticField, ApertureFromImage, Lens, mm, um, nm, cm, FourierPhaseRetrieval, PSF_convolution, apply_transfer_function, bd, SLM
from Random_Phase_Mask_Scattering import PhaseMaskScattering, load_hologram_phase_mask, get_hologram_pixel, get_hologram_info, edit_hologram_pixel


# ============================================================================
# Configuration: Phase mask storage paths
# ============================================================================
# Change these paths to load phase masks from different locations
# These should match the paths used when saving the masks
PHASE_MASK_SAVE_PATH = './model_training/training_masks_1'
HOLOGRAM_MASK_SAVE_PATH = './model_training/hologram_mask_rings'

# Example for editing a pixel in the hologram phase mask
# edit_hologram_pixel(HOLOGRAM_MASK_SAVE_PATH, x coordinate, y coordinate, number between -pi and pi)

#Add a plane wave
F = MonochromaticField(
    wavelength=532.8 * nm, extent_x=30 * mm, extent_y=30 * mm, Nx=2400, Ny=2400, intensity = 0.005
)


# Load the hologram phase mask (from saved file if available, otherwise from image)
try:
    # Try to load from saved file
    hologram_slm = load_hologram_phase_mask(F, HOLOGRAM_MASK_SAVE_PATH)
    F.add(hologram_slm)
    print("Loaded hologram phase mask from saved file")
except FileNotFoundError:
    # Fallback to loading from image
    print("Saved hologram mask not found, loading from image...")
    F.add(ApertureFromImage(
         amplitude_mask_path= "./diffractsim_main/examples/apertures/white_background.png", 
         phase_mask_path= "rings_phase_hologram.png", image_size=(10.0 * mm, 10.0 * mm), simulation = F)
    )


# #plot colors at z = 0
# rgb = F.get_colors()
# F.plot_colors(rgb)


# set distance to image plane 
z = 200*cm

# add lens to focus the hologram at z 
F.add(Lens(f = z))

# Load the saved phase masks and apply scattering
print("Loading saved phase masks...")
scattering_system = PhaseMaskScattering.load_phase_masks(F, PHASE_MASK_SAVE_PATH)

# Apply the scattering (this propagates through all the phase masks)
scattering_system.apply_scattering()

# Calculate remaining distance to propagate to the image plane
scattering_distance = scattering_system.get_total_scattering_distance()
final_distance = z - scattering_distance
F.propagate(final_distance)

# Alternatively, propagate directly to z without scattering (comment lines 50-60 and uncomment line 63)
# F.propagate(z)

# Plot the final result at the image plane
print("Plotting final result...")
rgb = F.get_colors()
F.plot_colors(rgb)