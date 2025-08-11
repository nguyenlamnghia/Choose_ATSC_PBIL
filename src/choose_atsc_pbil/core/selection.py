import numpy as np

def pick_best_worst(scores):
    # scores: list[(x_vec, score)]
    by = sorted(scores, key=lambda t: t[1])
    best = by[0]
    worst = by[-1]
    return best, worst
