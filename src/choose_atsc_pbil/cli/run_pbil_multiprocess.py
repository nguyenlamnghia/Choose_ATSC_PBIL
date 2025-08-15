import argparse, json, os
from datetime import datetime
import numpy as np
import multiprocessing as mp

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

# Chạy mô phỏng cho một cá thể
def _run_simulation(x, scores, scores_history, candidates, runner, pbil: PBIL):
# Tạo mặt nạ được load vào, True = 1; False = 0
    mask = {tls_id: bool(x[i]) for i, tls_id in enumerate(candidates)}
    res = runner.run(mask)

    # Tính toán điểm số
    score = pbil.calculate_score(res)
    print(f"[+] Process {x}: Completed -> Score: {score}")

    # Lưu kết quả vào danh sách trong quần thể
    scores.append((x, float(score)))

    # Lưu kết quả vào danh sách lịch sử
    scores_history.append((x, float(score)))

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

    # Khởi tạo cache lưu trữ các kết quả score của toàn bộ lịch sử -> Sử dụng mp.Manager().list() để chia sẻ giữa các tiến trình
    scores_history = mp.Manager().list() # [([1, 0, 1], 98), ...]

    # Khởi tạo lịch sử và biến tốt nhất
    best_hist = []
    best_overall = None

    for g in range(pbil_cfg.Gmax):
        # Lấy mẫu quần thể
        pop = pbil.sample_population()

        # Xóa những cá thể giống nhau
        pop = list(set(tuple(x.tolist()) for x in pop))

        # Khởi tạo danh sách điểm số của từng cá thể trong quần thể -> Sử dụng mp.Manager().list() để chia sẻ giữa các tiến trình
        scores_list  = mp.Manager().list()

        # Khởi tạo danh sách tiến trình
        processes = []

        # Chạy mô phỏng cho từng cá thể trong quần thể
        for x in pop:
            # Kiểm tra xem cá thể đã chạy chưa trong lịch sử
            for s in scores_history:
                if s[0] == x:
                    # Chạy rồi thì add vào list score quần thể
                    scores_list.append(s)
                    print(f"[+] Process {len(processes)}: {x} -> Skipped (already run) -> Score: {s[1]}")
                    break
            else:
                # Chưa chạy thì khởi tạo tiến trình mới
                p = mp.Process(target=_run_simulation, args=(x, scores_list, scores_history, candidates, runner, pbil))
                processes.append(p)
                print(f"[+] Process {len(processes)}: {x} -> Running ...")
                p.start()

        for p in processes:
            p.join()

        # Chuyển đổi danh sách điểm số thành định dạng mong muốn
        scores = list(scores_list)

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

        # Kiểm tra hội tụ
        if pbil.converged(best_hist, eps=pbil_cfg.convergence_eps):
            break

    # Chuyển đổi cache lưu trữ các kết quả score của toàn bộ lịch sử thành dạng list mong muốn
    scores_history = list(scores_history)

    # Lấy ra các cấu hình tốt nhất
    # best_configs = [s[0] for s in scores_history if s[1] == min(scores_history, key=lambda x: x[1])[1]]
    best_configs = {
        "score": min(scores_history, key=lambda x: x[1])[1],
        "list_configs": []
    }
    for s in scores_history:
        if s[1] == best_configs["score"]:
            best_configs["list_configs"].append(s[0])

    # In ra màn hình các cấu hình tốt nhất
    print(f"List best configurations: {best_configs}")

    # Lưu vào thư mục chạy
    _save(os.path.join(run_dir, "scores_history.json"), scores_history)
    _save(os.path.join(run_dir, "best_configs.json"), best_configs)

    print("Run saved to:", run_dir)

if __name__ == "__main__":
    main()
