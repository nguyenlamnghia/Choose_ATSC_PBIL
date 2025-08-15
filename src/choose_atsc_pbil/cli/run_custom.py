import argparse, json, os, time
from datetime import datetime
from ..sim.sim_runner import SumoSimRunner

def _load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():

    # Load configuration
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--net_info", required=True)
    args = ap.parse_args()
    cfg = _load_config(args.config)

    # Load traffic light information
    net_info = _load_config(args.net_info)

    run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "run_config_snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    # Baseline 1: all fixed-time
    runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)
    # mask_none = {}
    # r1 = runner.run(mask_none)
    # with open(os.path.join(run_dir, "baseline_all_fixed.json"), "w", encoding="utf-8") as f:
    #     json.dump(r1, f, indent=2)

    # Baseline 2: all adaptive (controller_plan['adaptive'])
    # tls_ids_guess = ["1", "8", "18"]  # scaffold; replace with actual TLS IDs
    tls_ids_guess = ["1", "18", "12", "63"]
    # i want mask_all = {TLS_0: max-pressure, TLS_1: max-pressure, TLS_2: max-pressure}
    mask_all = {k: True for k in tls_ids_guess}
    print(mask_all)

    r2 = runner.run(mask_all)
    with open(os.path.join(run_dir, "baseline_all_adaptive.json"), "w", encoding="utf-8") as f:
        json.dump(r2, f, indent=2)

    print("Baselines saved to:", run_dir)

if __name__ == "__main__":
    main()
