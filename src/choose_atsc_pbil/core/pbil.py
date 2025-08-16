from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

@dataclass
class PBILConfig:
    # Core loop
    Gmax: int = 10                          # Số lượng quần thể (vòng lặp)
    population: int = 20                    # Số lượng cá thể

    # Learning rates
    lr_pos: float = 0.1                     # Học tích cực
    lr_neg: float = 0.05                    # Học tiêu cực

    # Mutation - Đột biến
    mutation_rate: float = 0.1              # Tỷ lệ đột biến
    mutation_step: float = 0.05             # Bước đột biến

    # Probability bounds
    prob_min: float = 0.05                  # Giới hạn dưới
    prob_max: float = 0.95                  # Giới hạn trên

    # Convergence (relative change of best score)
    convergence_eps: float = 1e-4           # Ngưỡng hội tụ

    # Constraint: max number of 1s allowed in a sample (None = no limit)
    N_max: Optional[int] = None

    # Sampling
    sample_interval: float = 10.0

    # When trimming to satisfy N_max: probability of choosing exploitation vs exploration
    exploit_prob: float = 0.5

    # Evaluation
    evaluation: str = "total_vehicle"

    # Random seed
    random_seed: Optional[int] = None

class PBIL:
    def __init__(self, cfg: PBILConfig, candidates: dict):
        self.C = len(candidates)
        self.candidates = candidates
        self.cfg = cfg
        self.rng = np.random.default_rng(self.cfg.random_seed)

        # initialize probability vector
        self.p = self._init_prob()

    def _init_prob(self):
        # Generator vector
        p = np.array(list(self.candidates.values()), dtype=float)
        return p

    # If N_max is reached, trim the individual
    def _trim_to_N_max(self, x: np.ndarray, p: np.ndarray) -> np.ndarray:
        if self.cfg.N_max is None:
            return x
        k = int(x.sum())
        if k <= self.cfg.N_max:
            return x

        ones_idx = np.flatnonzero(x == 1)
        need_drop = k - self.cfg.N_max

        if self.rng.uniform() < self.cfg.exploit_prob:
            # Exploitation: drop currently-on bits with *lowest* p first
            order = np.argsort(p[ones_idx])  # ascending
            drop_idx = ones_idx[order[:need_drop]]
        else:
            # Exploration: drop random ones
            drop_idx = self.rng.choice(ones_idx, size=need_drop, replace=False)

        x2 = x.copy()
        x2[drop_idx] = 0
        return x2

    def sample_population(self, p: Optional[np.ndarray] = None) -> np.ndarray:
        p = self.p if p is None else p
        # Bernoulli sampling
        X = (self.rng.random((self.cfg.population, self.C)) < p).astype(np.uint8)
        # Enforce N_max per individual
        if self.cfg.N_max is not None:
            for i in range(X.shape[0]):
                X[i] = self._trim_to_N_max(X[i], p)
        return X

    def calculate_score(self, res):
        return np.mean(res.get(self.cfg.evaluation, 0))

    def update(self, best, worst: Optional[np.ndarray] = None):
        p = self.p
        # Positive learning
        p = (1.0 - self.cfg.lr_pos) * p + self.cfg.lr_pos * best.astype(float)
        # Negative learning (symmetric, per doc):
        # If best!=worst:
        #   - best=0,worst=1  -> p <- p*(1-LR-)          (pull toward 0)
        #   - best=1,worst=0  -> p <- p*(1-LR-) + LR-    (pull toward 1)
        # Else keep p unchanged.
        if worst is not None and self.cfg.lr_neg > 0.0:
            b = best.astype(np.uint8)
            w = worst.astype(np.uint8)
            disagree = (b ^ w).astype(bool)
            if np.any(disagree):
                p[disagree] = (1.0 - self.cfg.lr_neg) * p[disagree] + self.cfg.lr_neg * b[disagree].astype(float)
        # mutation - Đột biến
        if self.cfg.mutation_rate > 0.0 and self.cfg.mutation_step > 0.0:
            m_mask = self.rng.random(self.C) < self.cfg.mutation_rate
            if np.any(m_mask):
                shifts = (self.rng.random(self.C) * 2.0 - 1.0) * self.cfg.mutation_step
                p[m_mask] += shifts[m_mask]

        # Lưu lại xác suất mới update
        self.p = np.clip(p, self.cfg.prob_min, self.cfg.prob_max)
        return self.p

    def converged(self, best_score_hist: List[float], eps: Optional[float] = None):
        eps = self.cfg.convergence_eps if eps is None else eps
        if len(best_score_hist) < 2:
            return False
        
        # Lấy giá trị tốt nhất của thế hệ trước và thế hệ hiện tại
        prev, curr = best_score_hist[-2], best_score_hist[-1]
        # Bảo vệ mẫu số, tránh chia cho 0
        denom = max(abs(prev), 1e-12)
        rel_change = abs(curr - prev) / denom
        return rel_change < eps
