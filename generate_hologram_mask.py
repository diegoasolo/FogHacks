from diffractsim_main import diffractsim
diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim_main.diffractsim import MonochromaticField, mm, nm, FourierPhaseRetrieval, ApertureFromImage
from Random_Phase_Mask_Scattering import save_hologram_phase_mask

# ============================================================================
# Configuration: hologram mask generation parameters
# ============================================================================
# Path where hologram mask will be saved (should match HOLOGRAM_MASK_SAVE_PATH in simulator.py)
SAVE_DIR = './model_training/hologram_mask_rings'

TARGET_AMPLITUDE_PATH = './diffractsim_main/examples/apertures/rings.jpg'

# Simulation parameters (must match simulator.py for masks to work correctly)
simulation_extent_x = 30 * mm
simulation_extent_y = 30 * mm
simulation_Nx = 2400
simulation_Ny = 2400
wavelength = 650 * nm # CHANGED TO RED

# ============================================================================
# Generate Hologram Mask
# ============================================================================

# Add a plane wave
F = MonochromaticField(
    wavelength=wavelength,
    extent_x=simulation_extent_x,
    extent_y=simulation_extent_y,
    Nx=simulation_Nx,
    Ny=simulation_Ny,
    intensity=0.005
)


# Generate a Fourier plane phase hologram
print(f"\nGenerating fourier plane phase hologram from {TARGET_AMPLITUDE_PATH}...")
PR = FourierPhaseRetrieval(target_amplitude_path = TARGET_AMPLITUDE_PATH, new_size= (400,400), pad = (200,200))
PR.retrieve_phase_mask(max_iter = 200, method = 'Conjugate-Gradient')
PR.save_retrieved_phase_as_image('hologram_mask_red.png')



print(f"\nSaving hologram mask to {SAVE_DIR}...")
save_hologram_phase_mask(F, 'hologram_mask_red.png', (10.0 * mm, 10.0 * mm), SAVE_DIR)

print("\n" + "=" * 70)
print("Hologram mask generation complete!")
print(f"Hologram mask saved to: {SAVE_DIR}")
print("=" * 70)
