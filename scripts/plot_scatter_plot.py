import json
import matplotlib.pyplot as plt

# Đọc dữ liệu từ file JSON
with open("../data/results/runs/pbil_run/scores_history.json", "r") as f:
    data = json.load(f)

# Chuyển dữ liệu sang dạng sum và score
sums = [sum(arr) for arr, score in data]
scores = [score for arr, score in data]

# Vẽ scatter plot
plt.figure(figsize=(8,6))
plt.scatter(sums, scores, alpha=0.6, edgecolor='k')

# Thêm nhãn và tiêu đề
plt.xlabel("Sum của mảng (số lượng 1)", fontsize=12)
plt.ylabel("Score (càng thấp càng tốt)", fontsize=12)
plt.title("Scatter plot: Sum vs Score", fontsize=14)

# Hiển thị biểu đồ
plt.show()
