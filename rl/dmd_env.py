# rl/dmd_env.py
import numpy as np
from PIL import Image
from typing import Tuple, Dict, Any

import torch
from torchvision import transforms
import pyiqa
from DISTS.DISTS_pytorch.DISTS_pt import DISTS

import gymnasium as gym
from gymnasium import spaces


class DMDSimEnv(gym.Env):
    """
    Simple 1D RL environment simulating DMD control over an image blend.

    State (obs): [alpha, dists_norm, musiq_norm]
    Action:      delta_alpha in [-0.1, 0.1]
    Reward:      combined_score(t) - combined_score(t-1)
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        clear_path: str,
        blurry_path: str,
        img_size: Tuple[int, int] = (512, 512),
        max_steps: int = 15,
        device: str = "cpu",
    ):
        super().__init__()
        self.clear_path = clear_path
        self.blurry_path = blurry_path
        self.img_size = img_size
        self.max_steps = max_steps
        self.device = device

        # --- Spaces ---
        # alpha in [0, 1], dists_norm and musiq_norm in [0, 1]
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0], dtype=np.float32),
            shape=(3,),
            dtype=np.float32,
        )

        # Action: change in alpha in [-0.1, 0.1]
        self.action_space = spaces.Box(
            low=np.array([-0.1], dtype=np.float32),
            high=np.array([0.1], dtype=np.float32),
            shape=(1,),
            dtype=np.float32,
        )

        # --- Load images once, as tensors ---
        self.to_tensor = transforms.ToTensor()

        clear_img = Image.open(self.clear_path).convert("RGB")
        blurry_img = Image.open(self.blurry_path).convert("RGB")

        clear_img = clear_img.resize(self.img_size, Image.BICUBIC)
        blurry_img = blurry_img.resize(self.img_size, Image.BICUBIC)

        self.clear_t = self.to_tensor(clear_img).to(self.device)  # (3,H,W)
        self.blurry_t = self.to_tensor(blurry_img).to(self.device)

        # DISTS & MUSIQ models (same as in your main)
        self.dists_model = DISTS().to(self.device)
        self.dists_model.eval()

        self.musiq_metric = pyiqa.create_metric("musiq", device=self.device)

        # Internal state
        self.alpha = 0.0
        self.prev_combined = 0.0
        self.step_count = 0
        self.last_blended_img = clear_img  # just for saving/visual

    # ----------------- helper functions ----------------- #

    def _blend_tensor(self, alpha: float) -> torch.Tensor:
        """
        Blend clear and blurry tensors using alpha.
        Returns a tensor (3,H,W) on self.device.
        """
        alpha = float(alpha)
        alpha = max(0.0, min(1.0, alpha))
        blended = alpha * self.clear_t + (1.0 - alpha) * self.blurry_t
        blended = torch.clamp(blended, 0.0, 1.0)
        return blended

    def _compute_iqa(self, blended_t: torch.Tensor) -> Dict[str, float]:
        """
        Compute DISTS, MUSIQ and combined score for blended image.
        """
        with torch.no_grad():
            # DISTS: lower = better
            dists_score = self.dists_model(
                self.clear_t.unsqueeze(0), blended_t.unsqueeze(0)
            ).item()
            dists_norm = 1.0 / (1.0 + dists_score)

            # MUSIQ via pyiqa: ~0-100, higher = better
            musiq_raw = self.musiq_metric(blended_t.unsqueeze(0)).item()
            musiq_norm = musiq_raw / 100.0

            combined = 0.5 * dists_norm + 0.5 * musiq_norm

        return {
            "dists_score": float(dists_score),
            "dists_norm": float(dists_norm),
            "musiq_raw": float(musiq_raw),
            "musiq_norm": float(musiq_norm),
            "combined": float(combined),
        }

    # ----------------- Gym API ----------------- #

    def reset(
        self, *, seed: int | None = None, options: Dict[str, Any] | None = None
    ):
        super().reset(seed=seed)

        self.alpha = 0.0  # start fully blurry
        self.step_count = 0

        blended_t = self._blend_tensor(self.alpha)
        metrics = self._compute_iqa(blended_t)
        self.prev_combined = metrics["combined"]

        # cache last blended for saving
        blended_np = (
            (blended_t.cpu().numpy().transpose(1, 2, 0) * 255.0).astype(np.uint8)
        )
        self.last_blended_img = Image.fromarray(blended_np)

        obs = np.array(
            [self.alpha, metrics["dists_norm"], metrics["musiq_norm"]],
            dtype=np.float32,
        )

        info = {
            "alpha": self.alpha,
            "combined_score": metrics["combined"],
            "dists_score": metrics["dists_score"],
            "musiq_raw": metrics["musiq_raw"],
        }

        return obs, info

    def step(self, action: np.ndarray):
        """
        action: np.array with shape (1,) -> delta_alpha
        """
        self.step_count += 1

        delta_alpha = float(action[0])
        delta_alpha = max(-0.1, min(0.1, delta_alpha))  # clip

        self.alpha = float(np.clip(self.alpha + delta_alpha, 0.0, 1.0))

        blended_t = self._blend_tensor(self.alpha)
        metrics = self._compute_iqa(blended_t)

        reward = metrics["combined"] - self.prev_combined
        self.prev_combined = metrics["combined"]

        terminated = False
        truncated = self.step_count >= self.max_steps

        # cache current blended image for saving/inspect
        blended_np = (
            (blended_t.cpu().numpy().transpose(1, 2, 0) * 255.0).astype(np.uint8)
        )
        self.last_blended_img = Image.fromarray(blended_np)

        obs = np.array(
            [self.alpha, metrics["dists_norm"], metrics["musiq_norm"]],
            dtype=np.float32,
        )

        info = {
            "alpha": self.alpha,
            "combined_score": metrics["combined"],
            "dists_score": metrics["dists_score"],
            "musiq_raw": metrics["musiq_raw"],
            "step": self.step_count,
        }

        return obs, reward, terminated, truncated, info

    def render(self):
        # For now just print alpha & combined score
        print(f"[render] alpha={self.alpha:.3f}, last_combined={self.prev_combined:.4f}")

    def save_current_image(self, path: str):
        """Save the last blended image to disk."""
        if self.last_blended_img is not None:
            self.last_blended_img.save(path)

    def get_current_blended_pil(self):
        """
        Return the current blended image (based on self.alpha)
        as a PIL.Image for visualization.
        """
        blended_t = self._blend_tensor(self.alpha)  # (3, H, W)
        blended_t = blended_t.detach().cpu().clamp(0.0, 1.0)

        to_pil = transforms.ToPILImage()
        img = to_pil(blended_t)  # PIL.Image
        return img
