import numpy as np

def compute_avg_network_density(density_values):
    return float(np.mean(density_values)) if len(density_values) else 0.0
