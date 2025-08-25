import argparse, json, os, time
from datetime import datetime
import logging

from ..sim.sim_runner import SumoSimRunner
from ..utils.logger import setup_logging
from ..core.pbil import PBIL, PBILConfig

def _load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    try:
        # Load configuration
        ap = argparse.ArgumentParser()
        ap.add_argument("--config", default="configs/config.json")
        ap.add_argument("--output", default=None)
        ap.add_argument("--name", required=True)
        args = ap.parse_args()

        # Thiết lập thư mục chạy
        if args.output:
            run_dir = args.output
        else:
            run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

        # Setup logger
        setup_logging(os.path.join(run_dir, "logs"))
        logger = logging.getLogger(__name__)

        logger.info("========== Starting CUSTOM ==========")

        cfg = _load_config(args.config)
        logger.info("Loaded configuration from: %s", args.config)

        net_info = _load_config(cfg["sumo"]["net_info_file"])
        logger.info("Loaded network information from: %s", cfg["sumo"]["net_info_file"])

        # Tạo thư mục cho evaluation
        run_dir = os.path.join(run_dir, "evaluation")
        os.makedirs(run_dir, exist_ok=True)
        logger.info("Setting up run directory: %s", run_dir.replace("\\", "/"))

        # Initial SumoSimRunner
        runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)

        # Init PBIL
        pbil_cfg = PBILConfig(**cfg["pbil"])
        pbil = PBIL(pbil_cfg, {})

        # Baseline 2: all ATSC
        try:
            logger.info("Running evaluation custom")
            candidate_tls_ids = _load_config(cfg["sumo"]["candidates_file"])["candidate_tls_ids"]
            
            solution = [1,1,0,1,0,1,1,1,1,1,1,1]
            mask_candidate = {}
            for i, tls_id in enumerate(candidate_tls_ids):
                if solution[i] == 1:
                    mask_candidate[tls_id] = True
            # mask_candidate = {k: True for k in candidate_tls_ids}
            
            r = runner.run_evaluation(mask_candidate, cfg["evaluations"], os.path.join(run_dir, f"{args.name}"))
            score2 = pbil.calculate_score(r)
            r["score"] = score2
        except Exception as e:
            logger.error("Error occurred while running custom: %s", e)
        with open(os.path.join(run_dir, f"{args.name}.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, indent=2)

        logger.info("All baselines saved to: %s", run_dir.replace("\\", "/"))
        logger.info("========== Completed ==========")
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
