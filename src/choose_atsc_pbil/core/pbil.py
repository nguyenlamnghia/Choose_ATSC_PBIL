from __future__ import annotations
import numpy as np
from dataclasses import dataclass

@dataclass
class PBILConfig:
    Gmax: int = 10
    population: int = 10
    lr_pos: float = 0.1
    lr_neg: float = 0.05
    mutation_rate: float = 0.1
    mutation_step: float = 0.05
    prob_min: float = 0.05
    prob_max: float = 0.95
    convergence_eps: float = 1e-4

class PBIL:
    def __init__(self, C: int, cfg: PBILConfig, rng=None):
        self.C = C
        self.cfg = cfg
        self.rng = np.random.default_rng(rng)

    def init_prob(self, prior = None):
        if prior is not None:
            p = np.clip(np.asarray(prior, dtype=float), self.cfg.prob_min, self.cfg.prob_max)
        else:
            p = np.full(self.C, 0.5, dtype=float)
        return p

    def sample_population(self, p_vec, size, nmax=None):
        pop = []
        for _ in range(size):
            x = self.rng.random(self.C) < p_vec
            if nmax is not None and nmax >= 0:
                # enforce <= nmax by turning off random ones if exceed
                idx1 = np.where(x)[0]
                if len(idx1) > nmax:
                    off = self.rng.choice(idx1, size=len(idx1)-nmax, replace=False)
                    x[off] = False
            pop.append(x.astype(int))
        return pop

    def update(self, p_vec, best, worst):
        p = p_vec.copy()
        lr_pos, lr_neg = self.cfg.lr_pos, self.cfg.lr_neg
        p = (1 - lr_pos) * p + lr_pos * best
        p = (1 - lr_neg) * p + lr_neg * worst * 0  # classic PBIL often moves away from worst; simplified here
        # mutation
        m_mask = self.rng.random(self.C) < self.cfg.mutation_rate
        m_shift = (self.rng.random(self.C) - 0.5) * 2 * self.cfg.mutation_step
        p[m_mask] += m_shift[m_mask]
        # bounds
        return np.clip(p, self.cfg.prob_min, self.cfg.prob_max)

    def converged(self, best_score_hist, eps=None):
        eps = self.cfg.convergence_eps if eps is None else eps
        if len(best_score_hist) < 2:
            return False
        return abs(best_score_hist[-1] - best_score_hist[-2]) < eps
