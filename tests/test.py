# run_libsumo.py
import argparse
import libsumo as traci  # API giống TraCI nhưng chạy nội bộ, không qua socket

def run(cfg_path: str, step_length: float | None, max_steps: int | None) -> int:
    # Các tùy chọn cơ bản, thiên về tốc độ
    opts = [
        "-c", cfg_path,
        "--no-step-log", "true",
        "--duration-log.disable", "true",
        "--quit-on-end", "true"
    ]
    if step_length is not None:
        opts += ["--step-length", str(step_length)]

    # Nạp mô phỏng trực tiếp (không khởi động tiến trình sumo/sumo-gui)
    traci.load(opts)

    steps = 0
    try:
        # Chạy cho tới khi không còn phương tiện/sự kiện dự kiến trong hàng đợi
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
    finally:
        traci.close()
    return steps


def main():
    parser = argparse.ArgumentParser(description="Run a .sumocfg with libsumo")
    parser.add_argument("-c", "--config", required=True, help="Đường dẫn tới file .sumocfg")
    parser.add_argument("--step-length", type=float, default=None,
                        help="Độ dài bước mô phỏng (giây), ví dụ 0.5 hoặc 1.0")
    parser.add_argument("--max-steps", type=int, default=None,
                        help="Giới hạn số bước (tùy chọn)")
    args = parser.parse_args()

    total = run(args.config, args.step_length, args.max_steps)
    print(f"Finished after {total} simulation steps")

if __name__ == "__main__":
    main()
