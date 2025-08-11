import argparse, json, os, time
from datetime import datetime
from ..sim.sim_runner import SumoSimRunner

def _load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = _load_config(args.config)
    run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "run_config_snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    # Baseline 1: all fixed-time
    runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], step_length=cfg["sumo"]["step_length"])
    mask_none = {}
    r1 = runner.run(mask_none)
    with open(os.path.join(run_dir, "baseline_all_fixed.json"), "w", encoding="utf-8") as f:
        json.dump(r1, f, indent=2)

    # Baseline 2: all adaptive (controller_plan['adaptive'])
    tls_ids_guess = ["TLS_0","TLS_1","TLS_2"]  # scaffold; replace with actual TLS IDs
    mask_all = {k: True for k in tls_ids_guess} # output: mask_all = Ơ
    r2 = runner.run(mask_all) 
    with open(os.path.join(run_dir, "baseline_all_adaptive.json"), "w", encoding="utf-8") as f:
        json.dump(r2, f, indent=2)

    print("Baselines saved to:", run_dir)

if __name__ == "__main__":
    main()
