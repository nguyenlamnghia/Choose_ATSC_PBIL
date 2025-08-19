import json
import pandas as pd
import matplotlib.pyplot as plt

# Đọc dữ liệu từ file JSON
with open("../data/results/runs/pbil_run/scores_history.json", "r") as f:
    data = json.load(f)

# Tạo DataFrame
rows = [{"sum": sum(arr), "score": score} for arr, score in data]
df = pd.DataFrame(rows)

# Lấy min(score) cho mỗi sum
df_min = df.groupby("sum", as_index=False)["score"].min()

# Vẽ line plot
plt.figure(figsize=(8,6))
plt.plot(df_min["sum"], df_min["score"], marker="o", linestyle="-")

# Thêm nhãn và tiêu đề
plt.xlabel("Sum của mảng (số lượng 1)", fontsize=12)
plt.ylabel("Min Score (càng thấp càng tốt)", fontsize=12)
plt.title("Min Score theo Sum", fontsize=14)

# Hiển thị biểu đồ
plt.show()
