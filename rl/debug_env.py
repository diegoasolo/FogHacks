# rl/debug_env.py
from rl.dmd_env import DMDSimEnv
import os

clear_path = os.path.join(os.getcwd(), "clear.png")
blurry_path = os.path.join(os.getcwd(), "blurry2.png")

env = DMDSimEnv(clear_path, blurry_path, max_steps=3)
obs, info = env.reset()
print("Initial:", obs, info)

for t in range(3):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    print(
        f"t={t}, "
        f"alpha={obs[0]:.3f}, "
        f"reward={reward:.4f}, "
        f"combined={info.get('combined_score', None):.4f}"
    )
    if terminated or truncated:
        break
