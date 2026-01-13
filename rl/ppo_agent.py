# rl/ppo_agent.py
import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Normal


class ActorCritic(nn.Module):
    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
        )
        self.mean_head = nn.Linear(hidden_dim, action_dim)
        self.value_head = nn.Linear(hidden_dim, 1)
        self.log_std = nn.Parameter(torch.zeros(action_dim))

    def forward(self, obs: torch.Tensor):
        if obs.dim() == 1:
            obs = obs.unsqueeze(0)
        x = self.net(obs)
        mean = self.mean_head(x)
        value = self.value_head(x).squeeze(-1)
        log_std = self.log_std.expand_as(mean)
        return mean, log_std, value

    def act(self, obs: np.ndarray):
        """Given a single observation, sample an action."""
        if isinstance(obs, np.ndarray):
            obs_t = torch.from_numpy(obs.astype(np.float32))
        else:
            obs_t = torch.tensor(obs, dtype=torch.float32)

        if obs_t.dim() == 1:
            obs_t = obs_t.unsqueeze(0)  # (1, obs_dim)

        mean, log_std, value = self.forward(obs_t)
        std = torch.exp(log_std)
        dist = Normal(mean, std)

        action = dist.sample()          # (1, action_dim)
        log_prob = dist.log_prob(action).sum(dim=-1)  # (1,)

        return (
            action.squeeze(0).detach().cpu().numpy(),  # np.array(action_dim,)
            log_prob.squeeze(0).detach(),              # scalar tensor
            value.squeeze(0).detach(),                 # scalar tensor
        )

    def evaluate_actions(self, obs_batch: torch.Tensor, act_batch: torch.Tensor):
        """
        obs_batch: (N, obs_dim)
        act_batch: (N, action_dim)
        """
        mean, log_std, value = self.forward(obs_batch)
        std = torch.exp(log_std)
        dist = Normal(mean, std)
        log_probs = dist.log_prob(act_batch).sum(dim=-1)
        entropy = dist.entropy().sum(dim=-1)
        return log_probs, entropy, value


class PPOAgent:
    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        gamma: float = 0.99,
        lam: float = 0.95,
        clip_eps: float = 0.2,
        lr: float = 3e-4,
        train_epochs: int = 4,
        batch_size: int = 64,
        device: str = "cpu",
    ):
        self.gamma = gamma
        self.lam = lam
        self.clip_eps = clip_eps
        self.train_epochs = train_epochs
        self.batch_size = batch_size
        self.device = device

        self.policy = ActorCritic(obs_dim, action_dim).to(self.device)
        self.optimizer = torch.optim.Adam(self.policy.parameters(), lr=lr)

        # Rollout storage
        self.reset_buffer()

    def reset_buffer(self):
        self.obs_buf = []
        self.act_buf = []
        self.rew_buf = []
        self.logp_buf = []
        self.val_buf = []
        self.done_buf = []

    def store_transition(self, obs, act, rew, logp, val, done):
        self.obs_buf.append(np.array(obs, dtype=np.float32))
        self.act_buf.append(np.array(act, dtype=np.float32))
        self.rew_buf.append(float(rew))
        self.logp_buf.append(float(logp.detach().cpu().numpy()))
        self.val_buf.append(float(val.detach().cpu().numpy()))
        self.done_buf.append(float(done))

    def compute_returns_and_advantages(self):
        rewards = np.array(self.rew_buf, dtype=np.float32)
        values = np.array(self.val_buf, dtype=np.float32)
        dones = np.array(self.done_buf, dtype=np.float32)

        n = len(rewards)
        returns = np.zeros_like(rewards)
        advantages = np.zeros_like(rewards)

        last_gae_lam = 0.0
        last_value = 0.0

        for t in reversed(range(n)):
            nonterminal = 1.0 - dones[t]
            delta = rewards[t] + self.gamma * last_value * nonterminal - values[t]
            last_gae_lam = delta + self.gamma * self.lam * nonterminal * last_gae_lam
            advantages[t] = last_gae_lam
            last_value = values[t]
            returns[t] = advantages[t] + values[t]

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        return returns, advantages

    def update(self):
        if len(self.rew_buf) == 0:
            return

        obs = torch.from_numpy(np.vstack(self.obs_buf)).float().to(self.device)
        acts = torch.from_numpy(np.vstack(self.act_buf)).float().to(self.device)
        old_logps = torch.from_numpy(np.array(self.logp_buf)).float().to(self.device)
        returns, advantages = self.compute_returns_and_advantages()
        returns = torch.from_numpy(returns).float().to(self.device)
        advantages = torch.from_numpy(advantages).float().to(self.device)

        dataset_size = obs.shape[0]
        idxs = np.arange(dataset_size)

        for _ in range(self.train_epochs):
            np.random.shuffle(idxs)
            for start in range(0, dataset_size, self.batch_size):
                end = start + self.batch_size
                batch_idx = idxs[start:end]

                batch_obs = obs[batch_idx]
                batch_acts = acts[batch_idx]
                batch_old_logps = old_logps[batch_idx]
                batch_returns = returns[batch_idx]
                batch_adv = advantages[batch_idx]

                log_probs, entropy, values = self.policy.evaluate_actions(
                    batch_obs, batch_acts
                )

                ratio = torch.exp(log_probs - batch_old_logps)
                surr1 = ratio * batch_adv
                surr2 = torch.clamp(ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * batch_adv
                policy_loss = -torch.min(surr1, surr2).mean()

                value_loss = ((values - batch_returns) ** 2).mean()

                entropy_loss = -entropy.mean() * 0.0  # optional entropy bonus

                loss = policy_loss + 0.5 * value_loss + entropy_loss

                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

        self.reset_buffer()
