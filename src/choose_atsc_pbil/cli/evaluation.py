import argparse, json, os, time
from datetime import datetime
import logging
import multiprocessing as mp

from ..sim.sim_runner import SumoSimRunner
from ..utils.logger import setup_logging
from ..core.pbil import PBIL, PBILConfig

def _load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_baseline_1(cfg, net_info, run_dir):
    """Run Baseline 1: all fixed-time"""
    try:
        runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)
        pbil_cfg = PBILConfig(**cfg["pbil"])
        pbil = PBIL(pbil_cfg, {})
        
        mask_none = {}
        r1 = runner.run_evaluation(mask_none, cfg["evaluations"], os.path.join(run_dir, "output_all_fixed"))
        score1 = pbil.calculate_score(r1)
        r1["score"] = score1
        
        with open(os.path.join(run_dir, "baseline_all_fixed.json"), "w", encoding="utf-8") as f:
            json.dump(r1, f, indent=2)
        
        return ("Baseline 1", True, None)
    except Exception as e:
        return ("Baseline 1", False, str(e))

def run_baseline_2(cfg, net_info, run_dir):
    """Run Baseline 2: all ATSC"""
    try:
        runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)
        pbil_cfg = PBILConfig(**cfg["pbil"])
        pbil = PBIL(pbil_cfg, {})
        
        candidate_tls_ids = _load_config(cfg["sumo"]["candidates_file"])["candidate_tls_ids"]
        mask_candidate = {k: True for k in candidate_tls_ids}
        r2 = runner.run_evaluation(mask_candidate, cfg["evaluations"], os.path.join(run_dir, "output_all_atsc"))
        score2 = pbil.calculate_score(r2)
        r2["score"] = score2
        
        with open(os.path.join(run_dir, "baseline_all_atsc.json"), "w", encoding="utf-8") as f:
            json.dump(r2, f, indent=2)
        
        return ("Baseline 2", True, None)
    except Exception as e:
        return ("Baseline 2", False, str(e))

def run_pbil_atsc(cfg, net_info, run_dir, best_file, number):
    """Run PBIL ATSC"""
    try:
        runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)
        pbil_cfg = PBILConfig(**cfg["pbil"])
        pbil = PBIL(pbil_cfg, {})
        
        candidate_tls_ids = _load_config(cfg["sumo"]["candidates_file"])["candidate_tls_ids"]
        bests = _load_config(best_file)["list_configs"][number]["config"]
        
        mask_candidate = {}
        for i, k in enumerate(candidate_tls_ids):
            if bests[i]:
                mask_candidate[k] = True
        
        r3 = runner.run_evaluation(mask_candidate, cfg["evaluations"], os.path.join(run_dir, "output_pbil_atsc"))
        score3 = pbil.calculate_score(r3)
        r3["score"] = score3
        
        with open(os.path.join(run_dir, "pbil_atsc.json"), "w", encoding="utf-8") as f:
            json.dump(r3, f, indent=2)
        
        return ("PBIL ATSC", True, None)
    except Exception as e:
        return ("PBIL ATSC", False, str(e))

def main():
    try:
        # Load configuration
        ap = argparse.ArgumentParser()
        ap.add_argument("--config", default="configs/config.json")
        ap.add_argument("--output", default=None)
        ap.add_argument("--best", required=True)
        ap.add_argument("--number", default=0, type=int)
        args = ap.parse_args()

        # Thiết lập thư mục chạy
        if args.output:
            run_dir = args.output
        else:
            run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

        # Setup logger
        setup_logging(os.path.join(run_dir, "logs"))
        logger = logging.getLogger(__name__)

        logger.info("========== Starting Evaluation ==========")

        cfg = _load_config(args.config)
        logger.info("Loaded configuration from: %s", args.config)

        net_info = _load_config(cfg["sumo"]["net_info_file"])
        logger.info("Loaded network information from: %s", cfg["sumo"]["net_info_file"])

        # Tạo thư mục cho evaluation
        run_dir = os.path.join(run_dir, "evaluation")
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "run_config_snapshot.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        logger.info("Setting up run directory: %s", run_dir.replace("\\", "/"))

        # Run evaluations in parallel
        logger.info("Starting parallel evaluation processes...")
        
        with mp.Pool(processes=3) as pool:
            # Submit all three tasks
            result1 = pool.apply_async(run_baseline_1, (cfg, net_info, run_dir))
            result2 = pool.apply_async(run_baseline_2, (cfg, net_info, run_dir))
            result3 = pool.apply_async(run_pbil_atsc, (cfg, net_info, run_dir, args.best, args.number))
            
            # Collect results
            results = [result1.get(), result2.get(), result3.get()]
        
        # Log results
        for name, success, error in results:
            if success:
                logger.info("%s completed successfully", name)
            else:
                logger.error("Error occurred while running %s: %s", name, error)

        logger.info("All evaluations saved to: %s", run_dir.replace("\\", "/"))
        logger.info("========== Evaluations Completed ==========")
        
    except FileNotFoundError as e:
        logging.getLogger(__name__).error("Missing file: %s", e, exc_info=True)
    except Exception:
        logging.getLogger(__name__).error("Unhandled error in main()", exc_info=True)
    finally:
        logging.shutdown()

if __name__ == "__main__":
    main()
