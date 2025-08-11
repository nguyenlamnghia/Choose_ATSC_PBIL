import argparse, json, os
from datetime import datetime
import numpy as np

from ..core.pbil import PBIL, PBILConfig
from ..core.selection import pick_best_worst
from ..sim.sim_runner import SumoSimRunner

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--graph", default="data/processed/graph.json")
    ap.add_argument("--candidates", default="data/processed/tls_candidates.json")
    args = ap.parse_args()

    cfg = _load(args.config)
    candidates = _load(args.candidates)["candidate_tls_ids"]
    C = len(candidates)

    run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(run_dir, exist_ok=True)
    _save(os.path.join(run_dir, "run_config_snapshot.json"), cfg)

    pbil_cfg = PBILConfig(**cfg["pbil"])
    pbil = PBIL(C, pbil_cfg, rng=cfg.get("random_seed", 123))
    p_vec = pbil.init_prob()

    runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], step_length=cfg["sumo"]["step_length"])

    best_hist = []
    best_overall = None

    for g in range(pbil_cfg.Gmax):
        pop = pbil.sample_population(p_vec, size=pbil_cfg.population, nmax=cfg["constraints"]["Nmax"])
        scores = []
        for x in pop:
            mask = {tls_id: bool(x[i]) for i, tls_id in enumerate(candidates)}
            res = runner.run(mask)
            scores.append((x.tolist(), float(res["avg_network_density"])))

        best, worst = pick_best_worst(scores)
        p_vec = pbil.update(p_vec, np.array(best[0]), np.array(worst[0]))
        best_hist.append(best[1])

        _save(os.path.join(run_dir, f"p_vec_gen_{g:03d}.json"), p_vec.tolist())
        _save(os.path.join(run_dir, f"population_gen_{g:03d}.json"), [x for x,_ in scores])
        _save(os.path.join(run_dir, f"scores_gen_{g:03d}.json"), [{"x":x, "score":s} for x,s in scores])

        if best_overall is None or best[1] < best_overall["score"]:
            best_overall = {"gen": g, "x": best[0], "score": best[1]}

        if pbil.converged(best_hist, eps=pbil_cfg.convergence_eps):
            break

    _save(os.path.join(run_dir, "best_overall.json"), best_overall)

    print("Run saved to:", run_dir)

if __name__ == "__main__":
    main()
