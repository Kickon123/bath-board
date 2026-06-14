import cv2
import numpy as np

src = cv2.imread("static/base3.png")
h, w = src.shape[:2]  # 996, 1580

# "Pollo.ai" は右上角にある白いテキスト
# 画像右端から約19%、上端から約8% の範囲をマスクして除去
x1 = int(w * 0.81)
y1 = 0
x2 = w
y2 = int(h * 0.08)

mask = np.zeros((h, w), dtype=np.uint8)
mask[y1:y2, x1:x2] = 255

# INPAINT_TELEA でテキスト周辺のピクセルから自然に補完
result = cv2.inpaint(src, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

out_path = "static/base3.png"
cv2.imwrite(out_path, result)
print(f"保存完了: {out_path}  ({w}x{h}px)")
