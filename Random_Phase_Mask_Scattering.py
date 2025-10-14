from diffractsim_main import diffractsim
diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim_main.diffractsim import MonochromaticField, ApertureFromImage, Lens, mm, um, nm, cm, FourierPhaseRetrieval, PSF_convolution, apply_transfer_function, bd, SLM


# # Generate a Fourier plane phase hologram, comment out if already generated
# PR = FourierPhaseRetrieval(target_amplitude_path = './diffractsim_main/examples/apertures/rings.jpg', new_size= (400,400), pad = (200,200))
# PR.retrieve_phase_mask(max_iter = 200, method = 'Conjugate-Gradient')
# PR.save_retrieved_phase_as_image('rings_phase_hologram.png')

class PhaseMaskScattering:
    """
    A new scattering method that uses multiple random phase masks to simulate 
    scattering events in fog/atmospheric conditions.
    """
    
    def __init__(self, simulation, num_masks=5, scattering_strength=0.5, mask_size=5*mm, phase_mask_complexity=8, layer_thickness=1*mm):
        """
        Initialize the phase mask scattering system.
        
        Parameters:
        -----------
        simulation : MonochromaticField
            The simulation object
        num_masks : int
            Number of phase masks to create
        scattering_strength : float
            Strength of scattering (0.0 = no scattering, 1.0 = maximum scattering)
        mask_size : float
            Physical size of each phase mask
        phase_mask_complexity : int
            Number of spatial frequencies for each phase mask
        layer_thickness : float
            Thickness of each scattering layer
        """
        self.simulation = simulation
        self.num_masks = num_masks
        self.scattering_strength = scattering_strength
        self.mask_size = mask_size
        self.phase_masks = []
        self.phase_mask_complexity = phase_mask_complexity
        self.layer_thickness = layer_thickness
        
        # Generate random phase masks
        self._generate_phase_masks()
    
    def _generate_random_phase_pattern(self, xx, yy, strength):
        """
        Generate a random phase pattern for scattering.
        Uses multiple spatial frequencies to create realistic scattering patterns.
        """
        # Create random phase patterns with different spatial frequencies
        phase = bd.zeros_like(xx)
        
        # Add multiple random spatial frequencies for realistic scattering
        num_frequencies = self.phase_mask_complexity
        for i in range(num_frequencies):
            # Random spatial frequency
            fx = (bd.random.random() - 0.5) * 2 / (self.mask_size / 10)  # Normalized frequency
            fy = (bd.random.random() - 0.5) * 2 / (self.mask_size / 10)
            
            # Random amplitude and phase offset
            amplitude = bd.random.random() * strength * 2 * bd.pi
            phase_offset = bd.random.random() * 2 * bd.pi
            
            # Add this frequency component
            phase += amplitude * bd.sin(2 * bd.pi * (fx * xx + fy * yy) + phase_offset)
        
        # Add some Gaussian random noise for fine structure
        noise_amplitude = strength * bd.pi / 4
        phase += noise_amplitude * bd.random.normal(size=xx.shape)
        
        return phase
    
    def _generate_phase_masks(self):
        """Generate the specified number of random phase masks."""
        print(f"Generating {self.num_masks} phase masks with scattering strength {self.scattering_strength}")
        
        for i in range(self.num_masks):
            # Create phase mask function
            def phase_function(xx, yy, strength=self.scattering_strength):
                return self._generate_random_phase_pattern(xx, yy, strength)
            
            # Create SLM (phase mask) for this scattering layer
            mask = SLM(
                phase_mask_function=lambda xx, yy: phase_function(xx, yy),
                size_x=self.mask_size,
                size_y=self.mask_size,
                simulation=self.simulation
            )
            
            self.phase_masks.append(mask)
        
        print(f"Created {len(self.phase_masks)} phase masks")
    
    def apply_scattering(self):
        """
        Apply scattering by propagating through all phase masks.
        Each mask represents a scattering layer in the atmosphere.
        """
        print(f"Applying scattering through {len(self.phase_masks)} phase masks")
        
        # Apply each phase mask sequentially
        for i, mask in enumerate(self.phase_masks):
            # Add the phase mask to the simulation
            self.simulation.add(mask)
            
            # Propagate a small distance to simulate scattering layer thickness
            # Each scattering layer is separated by a small distance
            
            self.simulation.propagate(self.layer_thickness)
            
            print(f"Applied phase mask {i+1}/{len(self.phase_masks)}")
    
    def get_total_scattering_distance(self):
        """
        Return the total distance added by all scattering masks.
        """
        return self.num_masks * self.layer_thickness
    
    def visualize_phase_masks(self, save_images=True):
        """
        Visualize the phase masks by plotting them.
        
        Parameters:
        -----------
        save_images : bool
            Whether to save the phase mask images to files
        """
        import matplotlib.pyplot as plt
        import numpy as np
        
        print(f"Visualizing {len(self.phase_masks)} phase masks...")
        
        # Create subplots for all masks
        fig, axes = plt.subplots(2, len(self.phase_masks), figsize=(4*len(self.phase_masks), 8))
        if len(self.phase_masks) == 1:
            axes = axes.reshape(2, 1)
        
        for i, mask in enumerate(self.phase_masks):
            # Generate the phase pattern for this mask
            phase_pattern = mask.phase_mask_function(self.simulation.xx, self.simulation.yy)
            
            # Plot phase pattern
            im1 = axes[0, i].imshow(bd.real(phase_pattern), cmap='hsv', extent=[
                self.simulation.x[0]/mm, self.simulation.x[-1]/mm,
                self.simulation.y[0]/mm, self.simulation.y[-1]/mm
            ])
            axes[0, i].set_title(f'Phase Mask {i+1} (Phase)')
            axes[0, i].set_xlabel('x (mm)')
            axes[0, i].set_ylabel('y (mm)')
            plt.colorbar(im1, ax=axes[0, i], label='Phase (radians)')
            
            # Plot transmittance magnitude
            transmittance = mask.get_transmittance(self.simulation.xx, self.simulation.yy, self.simulation.λ)
            im2 = axes[1, i].imshow(bd.abs(transmittance), cmap='gray', extent=[
                self.simulation.x[0]/mm, self.simulation.x[-1]/mm,
                self.simulation.y[0]/mm, self.simulation.y[-1]/mm
            ])
            axes[1, i].set_title(f'Phase Mask {i+1} (Transmittance)')
            axes[1, i].set_xlabel('x (mm)')
            axes[1, i].set_ylabel('y (mm)')
            plt.colorbar(im2, ax=axes[1, i], label='Transmittance')
            
            if save_images:
                # Save individual phase mask as image
                plt.figure(figsize=(8, 6))
                plt.imshow(bd.real(phase_pattern), cmap='hsv', extent=[
                    self.simulation.x[0]/mm, self.simulation.x[-1]/mm,
                    self.simulation.y[0]/mm, self.simulation.y[-1]/mm
                ])
                plt.title(f'Scattering Phase Mask {i+1}')
                plt.xlabel('x (mm)')
                plt.ylabel('y (mm)')
                plt.colorbar(label='Phase (radians)')
                plt.savefig(f'scattering_phase_mask_{i+1}.png', dpi=150, bbox_inches='tight')
                plt.close()
        
        plt.tight_layout()
        plt.savefig('all_scattering_phase_masks.png', dpi=150, bbox_inches='tight')
        plt.show()
        
        if save_images:
            print(f"Saved individual phase mask images as 'scattering_phase_mask_*.png'")
            print(f"Saved combined view as 'all_scattering_phase_masks.png'")
    
    def set_scattering_parameters(self, num_masks=None, scattering_strength=None):
        """
        Update scattering parameters and regenerate masks if needed.
        """
        if num_masks is not None:
            self.num_masks = num_masks
            self._generate_phase_masks()
        
        if scattering_strength is not None:
            self.scattering_strength = scattering_strength
            self._generate_phase_masks()




### Main simulation code ###


#Add a plane wave
F = MonochromaticField(
    wavelength=532.8 * nm, extent_x=30 * mm, extent_y=30 * mm, Nx=2400, Ny=2400, intensity = 0.005
)


# load the hologram as a phase mask aperture
F.add(ApertureFromImage(
     amplitude_mask_path= "./diffractsim_main/examples/apertures/white_background.png", 
     phase_mask_path= "rings_phase_hologram.png", image_size=(10.0 * mm, 10.0 * mm), simulation = F))



# #plot colors at z = 0
# rgb = F.get_colors()
# F.plot_colors(rgb)


# set distance to image plane 
z = 200*cm

# add lens to focus the hologram at z 
F.add(Lens(f = z))

### Set parameters for the phase mask scattering here ###
num_scattering_masks = 4  # Number of phase masks (scattering layers)
scattering_strength = 0.1  # Scattering strength (0.0 = no scattering, 1.0 = maximum)
mask_size = 20 * mm  # Size of each phase mask (square aperture size)
phase_mask_complexity = 8 # Number of spatial frequencies for each phase mask
layer_thickness = 1 * mm  # Thickness of each scattering layer


print(f"Phase Mask Scattering Parameters:")
print(f"  Number of masks: {num_scattering_masks}")
print(f"  Scattering strength: {scattering_strength}")
print(f"  Mask size: {mask_size/mm:.1f} mm")
print(f"  Phase mask complexity: {phase_mask_complexity}")
print(f"  Layer thickness: {layer_thickness/mm:.1f} mm")

# Create and apply the new scattering method
scattering_system = PhaseMaskScattering(
    simulation=F,
    num_masks=num_scattering_masks,
    scattering_strength=scattering_strength,
    mask_size=mask_size,
    phase_mask_complexity=phase_mask_complexity,
    layer_thickness=layer_thickness,
)

# Visualize the scattering phase masks, set save_images=False to avoid saving files
scattering_system.visualize_phase_masks(save_images=False)

# Apply the scattering
scattering_system.apply_scattering()


# propagate to the Fourier plane at z
scattering_distance = scattering_system.get_total_scattering_distance()
final_distance = z - scattering_distance
F.propagate(final_distance)


# plot colors (reconstructed image) at z (Fourier plane)
rgb = F.get_colors()
F.plot_colors(rgb)



# #plot longitudinal profile, comment out if not needed
# longitudinal_profile_rgb, longitudinal_profile_E, extent = F.get_longitudinal_profile( start_distance = 0*cm , end_distance = z , steps = 80) 
# #plot colors
# F.plot_longitudinal_profile_colors(longitudinal_profile_rgb = longitudinal_profile_rgb, extent = extent)
# print(longitudinal_profile_rgb.shape)


# F.plot_longitudinal_profile_intensity(longitudinal_profile_E = longitudinal_profile_E, extent = extent, square_root = True)
# print(longitudinal_profile_E.shape)
