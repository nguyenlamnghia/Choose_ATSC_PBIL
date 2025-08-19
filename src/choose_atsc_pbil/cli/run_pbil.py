# choose_atsc_pbil/cli/run_custom.py

import argparse, json, os
from datetime import datetime
import numpy as np
import multiprocessing as mp
import logging

from ..core.pbil import PBIL, PBILConfig
from ..core.selection import pick_best_worst
from ..sim.sim_runner import SumoSimRunner
from ..utils.logger import setup_multiprocess_logging, worker_configurer

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def _pool_worker_init(log_queue):
    # Mỗi process trong Pool sẽ tự cấu hình logger 1 lần
    worker_configurer(log_queue)


def _run_simulation(proc_idx, x, scores, scores_history, candidates, runner, pbil: PBIL):
    # Logger đã được cấu hình bởi _pool_worker_init
    logger = logging.getLogger(__name__)

    try:
        mask = {tls_id: bool(xi) for tls_id, xi in zip(candidates, x)}
        res = runner.run(mask)
        score = pbil.calculate_score(res)

        logger.debug("Process %d: Completed -> Score: %.6f", proc_idx + 1, score)

        scores.append((x, float(score)))
        scores_history.append((x, float(score)))

    except Exception:
        logger.error("Process %d: Failed during simulation for x=%s", proc_idx + 1, list(x), exc_info=True)


def main():
    # --- Cấu hình logging cho tiến trình chính ---
    # Lưu ý Windows dùng 'spawn', cần gọi setup_logging ở entry point
    log_queue, listener = setup_multiprocess_logging()
    logger = logging.getLogger(__name__)


    try:
        logger.info("========== Starting choose ATSC using PBIL ==========")
        logger.info("__________ Setting up configuration __________")

        # Thiết lập đối số
        ap = argparse.ArgumentParser()
        ap.add_argument("--config", default="configs/config.json")
        ap.add_argument("--output", default=None)
        args = ap.parse_args()

        # Load thông tin
        cfg = _load(args.config)
        logger.info("Loaded configuration from: %s", args.config)

        net_info = _load(cfg["sumo"]["net_info_file"])
        logger.info("Loaded network information from: %s", cfg["sumo"]["net_info_file"])

        candidates = _load(cfg["sumo"]["candidates_file"])["candidate_tls_ids"]
        logger.info("Loaded candidate TLS IDs from: %s", cfg["sumo"]["candidates_file"])

        # Thiết lập thư mục chạy
        if args.output:
            run_dir = args.output
        else:
            run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        os.makedirs(run_dir, exist_ok=True)
        _save(os.path.join(run_dir, "run_config_snapshot.json"), cfg)
        logger.info("Setting up run directory: %s", run_dir.replace("\\", "/"))

        # Thiết lập PBIL & SUMO
        logger.info("Setting up PBIL and SUMO...")
        pbil_cfg = PBILConfig(**cfg["pbil"])
        pbil = PBIL(pbil_cfg, candidates)
        runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)

        max_procs = cfg.get("system", {}).get("max_processes") or mp.cpu_count()
        logger.info("Using up to %d parallel processes", max_procs)

        # Cache lịch sử điểm (chia sẻ giữa tiến trình)
        manager = mp.Manager()
        scores_history = manager.list()  # [([1,0,1], 98.0), ...]

        best_hist = []

        for g in range(pbil_cfg.Gmax):
            logger.info("__________ Generation %d/%d: Starting __________", g + 1, pbil_cfg.Gmax)

            pop = pbil.sample_population()
            pop = list(set(tuple(x.tolist()) for x in pop))  # unique

            scores_list = manager.list()

            # Tạo Pool với initializer để cấu hình logging cho từng worker
            with mp.Pool(
                processes=max_procs,
                initializer=_pool_worker_init,
                initargs=(log_queue,)
            ) as pool:
                async_results = []

                for i, x in enumerate(pop):
                    # Cache: nếu đã có trong lịch sử thì không đưa vào Pool
                    for s in scores_history:
                        if s[0] == x:
                            scores_list.append(s)
                            logger.debug("Process %d: %s -> Skipped (cached) -> Score: %.6f", i + 1, list(x), s[1])
                            break
                    else:
                        # Gửi job vào Pool
                        logger.debug("Process %d: %s -> Starting...", i + 1, list(x))
                        async_results.append(pool.apply_async(
                            _run_simulation,
                            args=(i, x, scores_list, scores_history, candidates, runner, pbil)
                        ))

                logger.info("Waiting for %d process(es) to complete...", len(async_results))

                # Chờ tất cả job hoàn thành (và lan truyền exception nếu có)
                for r in async_results:
                    r.wait()

            # Thu kết quả quần thể
            scores = list(scores_list)

            # Best/Worst
            best, worst = pick_best_worst(scores)
            logger.info("Best:  %s -> Score: %.6f", list(best[0]), best[1])
            logger.info("Worst: %s -> Score: %.6f", list(worst[0]), worst[1])

            # Cập nhật vector xác suất
            p_vec = pbil.update(np.array(best[0]), np.array(worst[0]))
            logger.debug("Probability Vector: %s", p_vec)
            logger.info("Updated Probability Vector.")

            best_hist.append(best[1])

            # Lưu kết quả theo thế hệ
            _save(os.path.join(run_dir, f"p_vec_gen_{g:03d}.json"), p_vec.tolist())
            _save(os.path.join(run_dir, f"population_gen_{g:03d}.json"), [list(x) for x, _ in scores])
            _save(os.path.join(run_dir, f"scores_gen_{g:03d}.json"), [{"x": list(x), "score": s} for x, s in scores])

            # Kiểm tra hội tụ
            if pbil.converged(best_hist, eps=pbil_cfg.convergence_eps):
                logger.info("STOP: Convergence reached (eps=%.6f).", pbil_cfg.convergence_eps)
                break

        # Chuyển lịch sử thành list thường
        scores_history = list(scores_history)

        # Tìm cấu hình tốt nhất
        best_score = min(scores_history, key=lambda x: x[1])[1]
        best_configs = {
            "score": best_score,
            "list_configs": [x for x, s in scores_history if s == best_score]
        }

        # In kết quả gọn gàng
        logger.info("__________ RESULT __________")
        logger.info("Best SCORE: %.6f", best_configs["score"])
        for i, cfg_x in enumerate(best_configs["list_configs"]):
            logger.info("Case %d: %s -> Number ATSC %d/%d",
                        i + 1, list(cfg_x), sum(cfg_x), len(cfg_x))

        # Lưu kết quả cuối
        _save(os.path.join(run_dir, "scores_history.json"), scores_history)
        _save(os.path.join(run_dir, "best_configs.json"), best_configs)
        logger.info("Results saved to: %s", run_dir)
        logger.info("========== Choose ATSC using PBIL Completed ==========")

    except FileNotFoundError as e:
        # Bắt lỗi thiếu file input, ghi đầy đủ traceback
        logging.getLogger(__name__).error("Missing file: %s", e, exc_info=True)
    except Exception:
        logging.getLogger(__name__).error("Unhandled error in main()", exc_info=True)
    finally:
        # Dừng listener & shutdown logging)
        listener.stop()
        logging.shutdown()


if __name__ == "__main__":
    # Trên Windows nên đảm bảo spawn
    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass
    main()
