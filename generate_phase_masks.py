from diffractsim_main import diffractsim
diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim_main.diffractsim import MonochromaticField, mm, nm
from Random_Phase_Mask_Scattering import PhaseMaskScattering

# ============================================================================
# Configuration: Phase mask generation parameters
# ============================================================================
# Path where phase masks will be saved (should match PHASE_MASK_SAVE_PATH in simulator.py)
SAVE_DIR = './model_training/training_masks_1'

# Phase mask parameters
num_scattering_masks = 4  # Number of phase masks (scattering layers)
scattering_strength = 0.1  # Scattering strength (0.0 = no scattering, 1.0 = maximum)
mask_size = 20 * mm  # Size of each phase mask (square aperture size)
phase_mask_complexity = 5  # Number of spatial frequencies for each phase mask
layer_thickness = 10 * mm  # Thickness of each scattering layer

# Simulation parameters (must match simulator.py for masks to work correctly)
simulation_extent_x = 30 * mm
simulation_extent_y = 30 * mm
simulation_Nx = 2400
simulation_Ny = 2400
wavelength = 532.8 * nm

# ============================================================================
# Generate Phase Masks
# ============================================================================

print("=" * 70)
print("Phase Mask Generator")
print("=" * 70)
print(f"\nPhase Mask Scattering Parameters:")
print(f"  Number of masks: {num_scattering_masks}")
print(f"  Scattering strength: {scattering_strength}")
print(f"  Mask size: {mask_size/mm:.1f} mm")
print(f"  Phase mask complexity: {phase_mask_complexity}")
print(f"  Layer thickness: {layer_thickness/mm:.1f} mm")
print(f"\nSimulation Parameters:")
print(f"  Extent: {simulation_extent_x/mm:.1f} mm x {simulation_extent_y/mm:.1f} mm")
print(f"  Grid: {simulation_Nx} x {simulation_Ny}")
print(f"  Wavelength: {wavelength/nm:.1f} nm")
print(f"\nSave directory: {SAVE_DIR}")
print("=" * 70)

# Create a minimal simulation just for generating masks
# We only need the grid, not the full optical setup
F = MonochromaticField(
    wavelength=wavelength,
    extent_x=simulation_extent_x,
    extent_y=simulation_extent_y,
    Nx=simulation_Nx,
    Ny=simulation_Ny,
    intensity=0.005
)

# Generate the phase masks
print(f"\nGenerating {num_scattering_masks} phase masks...")
scattering_system = PhaseMaskScattering(
    simulation=F,
    num_masks=num_scattering_masks,
    scattering_strength=scattering_strength,
    mask_size=mask_size,
    phase_mask_complexity=phase_mask_complexity,
    layer_thickness=layer_thickness,
)

# Visualize the masks (optional, set save_images=False to skip saving images)
print(f"\nVisualizing phase masks...")
scattering_system.visualize_phase_masks(save_images=True)

# Save the masks
print(f"\nSaving phase masks to {SAVE_DIR}...")
scattering_system.save_phase_masks(SAVE_DIR)

print("\n" + "=" * 70)
print("Phase mask generation complete!")
print(f"Masks saved to: {SAVE_DIR}")
print("=" * 70)
