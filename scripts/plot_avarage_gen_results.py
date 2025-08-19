import json
import glob
import numpy as np
import matplotlib.pyplot as plt

# Đọc tất cả các file scores_gen_*.json trong thư mục
file_list = sorted(glob.glob("scores_gen_*.json"))

gen_ids = []
mean_scores = []

for filename in file_list:
    gen_id = int(filename.split("_")[-1].split(".")[0])
    gen_ids.append(gen_id)
    
    # Đọc dữ liệu
    with open(filename, "r") as f:
        data = json.load(f)
    
    # Xử lý tùy theo cấu trúc dữ liệu trong file
    scores = []
    for item in data:
        if isinstance(item, dict):  
            # trường hợp {"arr": [...], "score": xxx}
            scores.append(item["score"])
        elif isinstance(item, list) and len(item) == 2:
            # trường hợp [ [...], score ]
            scores.append(item[1])
        else:
            # fallback: nếu chỉ là số
            scores.append(item)
    
    mean_scores.append(np.mean(scores))

# Vẽ biểu đồ
plt.figure(figsize=(8,6))
plt.plot(gen_ids, mean_scores, marker="o", linestyle="-")

plt.xlabel("Gen", fontsize=12)
plt.ylabel("Trung bình Score", fontsize=12)
plt.title("Sự cải thiện trung bình Score theo Gen", fontsize=14)

plt.grid(True, linestyle="--", alpha=0.6)
plt.show()
