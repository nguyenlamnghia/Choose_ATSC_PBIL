import numpy as np

def pick_best_worst(scores):
    by = sorted(scores, key=lambda x: x["score"])
    best = by[0]
    worst = by[-1]
    return best, worst
