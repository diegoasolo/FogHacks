from diffractsim_main import diffractsim
diffractsim.set_backend("CPU") #Change the string to "CUDA" to use GPU acceleration

from diffractsim_main.diffractsim import MonochromaticField, ApertureFromImage, Lens, mm, um, nm, cm, FourierPhaseRetrieval, PSF_convolution, apply_transfer_function, bd, SLM
import numpy as np
import json
from pathlib import Path


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
    
    def save_phase_masks(self, save_dir='./saved_phase_masks'):
        """
        Save the generated phase masks as numpy arrays so they can be loaded back
        into a simulation to get the same result.
        
        Parameters:
        -----------
        save_dir : str
            Directory path where phase masks and metadata will be saved
            
        Returns:
        --------
        save_dir : str
            The directory where files were saved
        """
        # Create directory if it doesn't exist
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"Saving {len(self.phase_masks)} phase masks to {save_dir}...")
        
        # Evaluate and save each phase mask as a numpy array
        phase_mask_arrays = []
        for i, mask in enumerate(self.phase_masks):
            # Evaluate the phase pattern at the simulation grid points
            phase_pattern = mask.phase_mask_function(self.simulation.xx, self.simulation.yy)
            
            # Convert to numpy array (handle both numpy and cupy arrays)
            if hasattr(phase_pattern, 'get'):  # cupy array
                phase_array = np.array(phase_pattern.get())
            else:
                phase_array = np.array(phase_pattern)
            
            # Save as numpy file
            mask_filename = f'phase_mask_{i+1}.npy'
            mask_path = Path(save_dir) / mask_filename
            np.save(mask_path, phase_array)
            phase_mask_arrays.append(mask_filename)
            print(f"  Saved {mask_filename}")
        
        # Save the actual grid coordinates used for evaluation
        # Convert to numpy arrays (handle both numpy and cupy)
        if hasattr(self.simulation.xx, 'get'):  # cupy array
            xx_array = np.array(self.simulation.xx.get())
            yy_array = np.array(self.simulation.yy.get())
        else:
            xx_array = np.array(self.simulation.xx)
            yy_array = np.array(self.simulation.yy)
        
        # Save grid coordinates
        grid_xx_path = Path(save_dir) / 'grid_xx.npy'
        grid_yy_path = Path(save_dir) / 'grid_yy.npy'
        np.save(grid_xx_path, xx_array)
        np.save(grid_yy_path, yy_array)
        
        # Save metadata
        metadata = {
            'num_masks': self.num_masks,
            'scattering_strength': float(self.scattering_strength),
            'mask_size': float(self.mask_size),
            'phase_mask_complexity': self.phase_mask_complexity,
            'layer_thickness': float(self.layer_thickness),
            'simulation_extent_x': float(self.simulation.extent_x),
            'simulation_extent_y': float(self.simulation.extent_y),
            'simulation_Nx': int(self.simulation.Nx),
            'simulation_Ny': int(self.simulation.Ny),
            'phase_mask_files': phase_mask_arrays,
            'grid_xx_file': 'grid_xx.npy',
            'grid_yy_file': 'grid_yy.npy'
        }
        
        metadata_path = Path(save_dir) / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved metadata to {metadata_path}")
        print(f"All phase masks saved successfully to {save_dir}")
        
        return save_dir
    
    @classmethod
    def load_phase_masks(cls, simulation, save_dir='./saved_phase_masks'):
        """
        Load previously saved phase masks and recreate the PhaseMaskScattering object.
        
        Parameters:
        -----------
        simulation : MonochromaticField
            The simulation object (should match the original simulation parameters)
        save_dir : str
            Directory path where phase masks and metadata were saved
            
        Returns:
        --------
        scattering_system : PhaseMaskScattering
            A PhaseMaskScattering object with loaded phase masks
        """
        from diffractsim_main.diffractsim.util.file_handling import create_interpolator
        
        save_path = Path(save_dir)
        
        # Load metadata
        metadata_path = save_path / 'metadata.json'
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found at {metadata_path}")
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        print(f"Loading phase masks from {save_dir}...")
        print(f"  Number of masks: {metadata['num_masks']}")
        mask_size_mm = metadata['mask_size'] * 1000  # Convert from meters to mm
        print(f"  Mask size: {mask_size_mm:.1f} mm")
        
        # Verify simulation parameters match (warn if they don't)
        if (abs(float(simulation.extent_x) - metadata['simulation_extent_x']) > 1e-6 or
            abs(float(simulation.extent_y) - metadata['simulation_extent_y']) > 1e-6 or
            int(simulation.Nx) != metadata['simulation_Nx'] or
            int(simulation.Ny) != metadata['simulation_Ny']):
            print("  WARNING: Simulation parameters don't match saved masks!")
            print(f"    Saved: extent=({metadata['simulation_extent_x']}, {metadata['simulation_extent_y']}), "
                  f"grid=({metadata['simulation_Nx']}, {metadata['simulation_Ny']})")
            print(f"    Current: extent=({float(simulation.extent_x)}, {float(simulation.extent_y)}), "
                  f"grid=({int(simulation.Nx)}, {int(simulation.Ny)})")
            print("    Results may differ due to interpolation.")
        
        # Create instance without generating masks
        instance = cls.__new__(cls)
        instance.simulation = simulation
        instance.num_masks = metadata['num_masks']
        instance.scattering_strength = metadata['scattering_strength']
        instance.mask_size = metadata['mask_size']
        instance.phase_mask_complexity = metadata['phase_mask_complexity']
        instance.layer_thickness = metadata['layer_thickness']
        instance.phase_masks = []
        
        # Load the grid coordinates that were used when saving
        if 'grid_xx_file' in metadata and 'grid_yy_file' in metadata:
            grid_xx_path = save_path / metadata['grid_xx_file']
            grid_yy_path = save_path / metadata['grid_yy_file']
            if grid_xx_path.exists() and grid_yy_path.exists():
                saved_xx = np.load(grid_xx_path)
                saved_yy = np.load(grid_yy_path)
                # Use the saved grid coordinates for interpolation bounds
                x_min = float(np.min(saved_xx))
                x_max = float(np.max(saved_xx))
                y_min = float(np.min(saved_yy))
                y_max = float(np.max(saved_yy))
            else:
                # Fallback to simulation grid if saved grid not found
                x_min = float(simulation.x[0])
                x_max = float(simulation.x[-1])
                y_min = float(simulation.y[0])
                y_max = float(simulation.y[-1])
        else:
            # Fallback for old format without saved grid
            x_min = float(simulation.x[0])
            x_max = float(simulation.x[-1])
            y_min = float(simulation.y[0])
            y_max = float(simulation.y[-1])
        
        # Load each phase mask
        for i, mask_filename in enumerate(metadata['phase_mask_files']):
            mask_path = save_path / mask_filename
            if not mask_path.exists():
                raise FileNotFoundError(f"Phase mask file not found at {mask_path}")
            
            # Load the phase array
            phase_array = np.load(mask_path)
            
            # Create interpolator function from the saved array using the exact grid coordinates
            phase_function = create_interpolator(
                phase_array,
                x_interval=[x_min, x_max],
                y_interval=[y_min, y_max],
                method='linear',
                bounds_error=False,
                fill_value=0.0
            )
            
            # Create SLM with the loaded phase function
            mask = SLM(
                phase_mask_function=phase_function,
                size_x=instance.mask_size,
                size_y=instance.mask_size,
                simulation=simulation
            )
            
            instance.phase_masks.append(mask)
            print(f"  Loaded {mask_filename}")
        
        print(f"Successfully loaded {len(instance.phase_masks)} phase masks")
        
        return instance




### Main simulation code ###
# NOTE: This code has been moved to generate_phase_masks.py and simulator.py
# Use generate_phase_masks.py to generate and save phase masks
# Use simulator.py to load and use saved phase masks in a simulation

# #Add a plane wave
# F = MonochromaticField(
#     wavelength=532.8 * nm, extent_x=30 * mm, extent_y=30 * mm, Nx=2400, Ny=2400, intensity = 0.005
# )
# 
# 
# # load the hologram as a phase mask aperture
# F.add(ApertureFromImage(
#      amplitude_mask_path= "./diffractsim_main/examples/apertures/white_background.png", 
#      phase_mask_path= "rings_phase_hologram.png", image_size=(10.0 * mm, 10.0 * mm), simulation = F))
# 
# 
# 
# # #plot colors at z = 0
# # rgb = F.get_colors()
# # F.plot_colors(rgb)
# 
# 
# # set distance to image plane 
# z = 200*cm
# 
# # add lens to focus the hologram at z 
# F.add(Lens(f = z))
# 
# ### Set parameters for the phase mask scattering here ###
# num_scattering_masks = 4  # Number of phase masks (scattering layers)
# scattering_strength = 0.1  #Scattering strength (0.0 = no scattering, 1.0 = maximum)
# mask_size = 20 * mm  # Size of each phase mask (square aperture size)
# phase_mask_complexity = 5 # Number of spatial frequencies for each phase mask
# layer_thickness = 10 * mm  # Thickness of each scattering layer
# 
# 
# print(f"Phase Mask Scattering Parameters:")
# print(f"  Number of masks: {num_scattering_masks}")
# print(f"  Scattering strength: {scattering_strength}")
# print(f"  Mask size: {mask_size/mm:.1f} mm")
# print(f"  Phase mask complexity: {phase_mask_complexity}")
# print(f"  Layer thickness: {layer_thickness/mm:.1f} mm")
# 
# # Check if saved masks exist and load them, otherwise generate new ones
# save_dir = './my_saved_masks'
# metadata_path = Path(save_dir) / 'metadata.json'
# 
# if metadata_path.exists():
#     print(f"\nFound existing saved masks at {save_dir}, loading them...")
#     scattering_system = PhaseMaskScattering.load_phase_masks(F, save_dir)
# else:
#     print(f"\nNo saved masks found at {save_dir}, generating new ones...")
#     # Create and apply the new scattering method
#     scattering_system = PhaseMaskScattering(
#         simulation=F,
#         num_masks=num_scattering_masks,
#         scattering_strength=scattering_strength,
#         mask_size=mask_size,
#         phase_mask_complexity=phase_mask_complexity,
#         layer_thickness=layer_thickness,
#     )
#     # Save the newly generated masks
#     print(f"\nSaving newly generated masks...")
#     scattering_system.save_phase_masks(save_dir)
# 
# # Visualize the scattering phase masks, set save_images=False to avoid saving files
# scattering_system.visualize_phase_masks(save_images=True)
# 
# # Apply the scattering
# scattering_system.apply_scattering()
# 
# # propagate to the Fourier plane at z
# scattering_distance = scattering_system.get_total_scattering_distance()
# final_distance = z - scattering_distance
# F.propagate(final_distance)
# 
# 
# # plot colors (reconstructed image) at z (Fourier plane)
# rgb = F.get_colors()
# F.plot_colors(rgb)
# 
# 
# 
# # #plot longitudinal profile, comment out if not needed
# # longitudinal_profile_rgb, longitudinal_profile_E, extent = F.get_longitudinal_profile( start_distance = 0*cm , end_distance = z , steps = 80) 
# # #plot colors
# # F.plot_longitudinal_profile_colors(longitudinal_profile_rgb = longitudinal_profile_rgb, extent = extent)
# # print(longitudinal_profile_rgb.shape)
# 
# 
# # F.plot_longitudinal_profile_intensity(longitudinal_profile_E = longitudinal_profile_E, extent = extent, square_root = True)
# # print(longitudinal_profile_E.shape)
