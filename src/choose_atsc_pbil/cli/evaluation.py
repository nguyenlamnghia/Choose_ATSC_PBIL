import argparse, json, os, time
from datetime import datetime
import logging

from ..sim.sim_runner import SumoSimRunner
from ..utils.logger import setup_logging

def _load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    # Setup logger
    setup_logging()
    logger = logging.getLogger(__name__)

    try:

        logger.info("========== Starting Evaluation ==========")

        # Load configuration
        ap = argparse.ArgumentParser()
        ap.add_argument("--config", default="configs/config.json")
        ap.add_argument("--output", default=None)
        args = ap.parse_args()

        cfg = _load_config(args.config)
        logger.info("Loaded configuration from: %s", args.config)

        net_info = _load_config(cfg["sumo"]["net_info_file"])
        logger.info("Loaded network information from: %s", cfg["sumo"]["net_info_file"])

        # Thiết lập thư mục chạy
        if args.output:
            run_dir = args.output
        else:
            run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "run_config_snapshot.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        logger.info("Setting up run directory: %s", run_dir.replace("\\", "/"))

        # Initial SumoSimRunner
        runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)
        
        # Baseline 1: all fixed-time
        try:
            logger.info("Running Baseline 1: all fixed-time")
            mask_none = {}
            r1 = runner.run(mask_none)
            with open(os.path.join(run_dir, "baseline_all_fixed.json"), "w", encoding="utf-8") as f:
                json.dump(r1, f, indent=2)
        except Exception as e:
            logger.error("Error occurred while running Baseline 1: %s", e)

        # Baseline 2: all ATSC
        try:
            logger.info("Running Baseline 2: all ATSC")
            candidate_tls_ids = _load_config(cfg["sumo"]["candidates_file"])["candidate_tls_ids"]
            mask_candidate = {k: True for k in candidate_tls_ids}
            r2 = runner.run(mask_candidate)
        except Exception as e:
            logger.error("Error occurred while running Baseline 2: %s", e)
        with open(os.path.join(run_dir, "baseline_all_atsc.json"), "w", encoding="utf-8") as f:
            json.dump(r2, f, indent=2)

        logger.info("All baselines saved to: %s", run_dir)

        logger.info("========== Baselines Completed ==========")
    except FileNotFoundError as e:
        # Bắt lỗi thiếu file input, ghi đầy đủ traceback
        logging.getLogger(__name__).error("Missing file: %s", e, exc_info=True)
    except Exception:
        logging.getLogger(__name__).error("Unhandled error in main()", exc_info=True)
    finally:
        # Dừng shutdown logging
        logging.shutdown()

if __name__ == "__main__":
    main()
