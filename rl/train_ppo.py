# rl/train_ppo.py
import os
import numpy as np
import matplotlib.pyplot as plt

try:
    # If running as a package: python -m rl.train_ppo
    from .dmd_env import DMDSimEnv
    from .ppo_agent import PPOAgent
except ImportError:
    # If running directly: python rl/train_ppo.py
    from dmd_env import DMDSimEnv
    from ppo_agent import PPOAgent


def train_ppo(
    clear_path: str = "clear.png",
    blurry_path: str = "blurry2.png",
    num_episodes: int = 5,
    max_steps: int = 15,
):
    # ------------- sanity check -------------
    if not os.path.exists(clear_path) or not os.path.exists(blurry_path):
        raise FileNotFoundError(
            f"Missing clear/blurry images. Expected {clear_path} and {blurry_path}"
        )

    # Folder to save visualizations
    viz_dir = "rl_viz"
    os.makedirs(viz_dir, exist_ok=True)

    print("▶ creating environment...")
    env = DMDSimEnv(
        clear_path=clear_path,
        blurry_path=blurry_path,
        img_size=(512, 512),
        max_steps=max_steps,
        device="cpu",
    )

    obs_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    agent = PPOAgent(
        obs_dim=obs_dim,
        action_dim=action_dim,
        gamma=0.99,
        lam=0.95,
        clip_eps=0.2,
        lr=3e-4,
        train_epochs=4,
        batch_size=64,
        device="cpu",
    )

    # For reference: save the pure clear & blurry images once
    env.alpha = 0.0
    env.save_current_image(os.path.join(viz_dir, "blurry_reference.png"))
    env.alpha = 1.0
    env.save_current_image(os.path.join(viz_dir, "clear_reference.png"))
    env.alpha = 0.0  # reset

    for ep in range(num_episodes):
        obs, info = env.reset()
        print(f"\n=== EPISODE {ep} START ===")
        print(
            f"Initial: alpha={info['alpha']:.3f}, "
            f"combined={info['combined_score']:.4f}, "
            f"DISTS={info['dists_score']:.4f}, "
            f"MUSIQ_raw={info['musiq_raw']:.2f}"
        )

        # save initial blended image for this episode
        init_img_path = os.path.join(viz_dir, f"episode_{ep}_step_init.png")
        env.save_current_image(init_img_path)

        episode_return = 0.0

        # For plotting later
        ep_alphas = [info["alpha"]]
        ep_combined = [info["combined_score"]]
        ep_rewards = [0.0]  # no reward yet at t=0

        for t in range(max_steps):
            # Agent chooses action given current obs
            action, logp, value = agent.policy.act(obs)

            # Step environment
            next_obs, reward, terminated, truncated, step_info = env.step(action)

            done = terminated or truncated
            episode_return += reward

            agent.store_transition(obs, action, reward, logp, value, done)

            # Log scalars
            ep_alphas.append(step_info["alpha"])
            ep_combined.append(step_info["combined_score"])
            ep_rewards.append(reward)

            print(
                f"t={t:02d}, "
                f"delta_alpha={action[0]:+.3f}, "
                f"alpha={step_info['alpha']:.3f}, "
                f"reward={reward:.5f}, "
                f"combined={step_info['combined_score']:.4f}"
            )

            # For episode 0, save the image at every step so you can
            # show how the image quality changes as alpha changes.
            if ep == 0:
                step_img_path = os.path.join(viz_dir, f"episode_0_step_{t:02d}.png")
                env.save_current_image(step_img_path)

            obs = next_obs

            if done:
                break

        # After each episode, update PPO using collected rollout
        agent.update()

        print(
            f"=== EPISODE {ep} END | total_return={episode_return:.4f}, "
            f"final_alpha={step_info['alpha']:.3f}, "
            f"final_combined={step_info['combined_score']:.4f} ==="
        )

        # Save final blended image for this episode
        final_img_path = os.path.join(viz_dir, f"episode_{ep}_final.png")
        env.save_current_image(final_img_path)
        print(f"Saved final blended image to {final_img_path}")

        # ----------- plot alpha & combined vs time ----------- #
        steps = np.arange(len(ep_alphas))

        fig, ax1 = plt.subplots(figsize=(6, 4))
        ax1.set_title(f"Episode {ep} – alpha & IQA over steps")
        ax1.set_xlabel("step")

        # alpha on left axis
        ax1.plot(steps, ep_alphas, marker="o", label="alpha (blend fraction)")
        ax1.set_ylabel("alpha (0=blurry, 1=clear)")
        ax1.set_ylim(-0.05, 1.05)

        # combined IQA on right axis
        ax2 = ax1.twinx()
        ax2.plot(steps, ep_combined, marker="x", color="tab:orange", label="combined IQA")
        ax2.set_ylabel("combined IQA score")

        # Build a combined legend
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines + lines2, labels + labels2, loc="lower right")

        plt.tight_layout()
        plot_path = os.path.join(viz_dir, f"episode_{ep}_metrics.png")
        plt.savefig(plot_path, dpi=150)
        plt.close(fig)
        print(f"Saved metrics plot to {plot_path}")


if __name__ == "__main__":
    # Run from project root (with .venv active):
    #   python -m rl.train_ppo
    # or:
    #   python rl/train_ppo.py
    train_ppo()
