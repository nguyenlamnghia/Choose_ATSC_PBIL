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

    # Thiết lập đối số
    ap = argparse.ArgumentParser()
    # ap.add_argument("--config", required=True)
    ap.add_argument("--config", default="data/configs/config.json")
    ap.add_argument("--net_info", default="data/input/net-infomation-example.json")
    ap.add_argument("--candidates", default="data/input/tls-candidates.json")
    args = ap.parse_args()

    # Load thông tin
    cfg = _load(args.config)
    candidates = _load(args.candidates)["candidate_tls_ids"]
    net_info = _load(args.net_info)

    # Thiết lập thư mục chạy
    run_dir = os.path.join("data", "results", "runs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(run_dir, exist_ok=True)
    _save(os.path.join(run_dir, "run_config_snapshot.json"), cfg)

    # Thiết lập PBIL
    pbil_cfg = PBILConfig(**cfg["pbil"])
    pbil = PBIL(pbil_cfg, candidates)

    # Thiết lập SUMO
    runner = SumoSimRunner(cfg["sumo"], cfg["controllers"], cfg["pbil"], net_info)

    # Khởi tạo lịch sử và biến tốt nhất
    best_hist = []
    best_overall = None

    for g in range(pbil_cfg.Gmax):
        # Lấy mẫu quần thể
        pop = pbil.sample_population()

        # Khởi tạo danh sách điểm số
        scores = []

        # Chạy mô phỏng cho từng cá thể trong quần thể
        for x in pop:
            # Tạo mặt nạ được load vào, True = 1; False = 0
            mask = {tls_id: bool(x[i]) for i, tls_id in enumerate(candidates)}
            res = runner.run(mask)

            # Save result to g/

            # Tính toán điểm số
            score = pbil.calculate_score(res)
            scores.append((x.tolist(), float(score)))

        # Lấy cá thể tốt nhất và tồi nhất
        best, worst = pick_best_worst(scores)
        # Cập nhật xác suất
        p_vec = pbil.update(np.array(best[0]), np.array(worst[0]))
        # Lưu lại xác suất mới
        best_hist.append(best[1])

        # Lưu vào thư mục chạy
        _save(os.path.join(run_dir, f"p_vec_gen_{g:03d}.json"), p_vec.tolist())
        _save(os.path.join(run_dir, f"population_gen_{g:03d}.json"), [x for x,_ in scores])
        _save(os.path.join(run_dir, f"scores_gen_{g:03d}.json"), [{"x":x, "score":s} for x,s in scores])

        # Cập nhật cá thể tốt nhất
        if best_overall is None or best[1] < best_overall["score"]:
            best_overall = {"gen": g, "x": best[0], "score": best[1]}

        # Kiểm tra hội tụ
        if pbil.converged(best_hist, eps=pbil_cfg.convergence_eps):
            break

    # Lưu vào thư mục chạy
    _save(os.path.join(run_dir, "best_overall.json"), best_overall)

    print("Run saved to:", run_dir)

if __name__ == "__main__":
    main()
