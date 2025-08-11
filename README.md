# ATSC-PBIL (Scaffold)

Pluggable **controllers** (Max-Pressure, Webster, etc.) + **PBIL** selection (upper level) over SUMO.

## Quick start

1. Install Python 3.10+ and SUMO (ensure `sumo` and `traci` are available; on Windows, run from the SUMO console/Anaconda where `traci` is on PYTHONPATH).
2. Install project (editable):  
   ```bash
   pip install -e .
   ```
3. Put a small SUMO network under `data/input/sumo/` (e.g. `network.net.xml`, `demand.rou.xml`).
4. Build graph metadata:
   ```bash
   build-graph --net data/input/sumo/network.net.xml                --out data/processed/graph.json                --candidates-out data/processed/tls_candidates.json
   ```
5. Copy and edit config:
   ```bash
   cp configs/experiment.example.json configs/experiment.json
   ```
6. Baselines then PBIL:
   ```bash
   run-baselines --config configs/experiment.json
   run-pbil --config configs/experiment.json
   ```

## Notes
- All results are JSON under `data/results/runs/<timestamp>/`.
- Controllers live in `src/controllers/` and are loaded via a simple registry.
- `sim_runner` doesn't know anything about controller internals; it only applies `ControllerAction`s.


atsc_pbil/
├─ pyproject.toml            # dependencies, entry points
├─ README.md                 # cách chạy, mô tả kịch bản
├─ configs/
│  ├─ experiment.example.json
│  └─ logging.yaml
├─ data/
│  ├─ input/sumo/            # *.net.xml, *.rou.xml, *.add.xml
│  ├─ processed/
│  │  ├─ graph.json          # xuất từ bước tiền xử lý networkx
│  │  ├─ tls_candidates.json # danh sách TLS ứng viên + thuộc tính
│  │  └─ baseline_metrics.json # metrics baseline (No-ATSC, All-ATSC)
│  └─ results/
│     └─ runs/2025-08-08_11-22-33/
│        ├─ p_vec_gen_000.json
│        ├─ population_gen_000.json
│        ├─ scores_gen_000.json
│        ├─ best_overall.json          # {config, score, meta}
│        └─ run_config_snapshot.json   # log lại cấu hình chạy
├─ src/
│  ├─ core/
│  │  ├─ pbil.py              # thuật toán PBIL (upper)
│  │  ├─ selection.py         # chọn/cắt Nmax, sinh quần thể
│  │  ├─ evaluation.py        # tính objective từ log mô phỏng
│  │  ├─ convergence.py       # CR, Gmax, dừng sớm
│  │  └─ utils_io.py          # load/save JSON, seed, path helpers
│  ├─ controllers/                   # 🎯 Dedicated controller module
│  │  ├─ __init__.py
│  │  ├─ base_controller.py          # Abstract base class
│  │  ├─ max_pressure.py             # Max Pressure implementation
│  │  ├─ webster.py                  # Webster timing implementation  
│  │  ├─ fixed_time.py               # Fixed-time controller
│  │  ├─ actuated.py                 # Vehicle-actuated controller
│  │  ├─ adaptive_controller.py      # Generic adaptive interface
│  ├─ sim/
│  │  ├─ mp_controller.py     # Max-Pressure controller (TraCI)
│  │  ├─ sim_runner.py        # chạy SUMO, khởi tạo, warmup, log
│  │  └─ extractors.py        # đọc *.net.xml → networkx (từ get_link.py)
│  ├─ interfaces/
│  │  └─ types.py             # dataclass cấu hình, DTO
│  ├─ cli/
│  │  ├─ build_graph.py       # tạo graph.json & tls_candidates.json
│  │  ├─ run_baselines.py     # No-ATSC / All-ATSC
│  │  └─ run_pbil.py          # entrypoint chính
│  └─ tests/
│     ├─ test_pbil.py
│     ├─ test_selection.py
│     └─ test_extractors.py
└─ scripts/
   └─ plot_results.ipynb      # (tùy chọn)
