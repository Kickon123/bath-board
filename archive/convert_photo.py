"""
露天風呂の写真をアニメ風に変換するスクリプト

使い方:
  python convert_photo.py 写真.jpg
  → static/bg.jpg が生成される

Replicate API を使う場合（高品質）:
  REPLICATE_API_TOKEN=xxxx python convert_photo.py 写真.jpg --api
"""
import sys
import os
import cv2
import numpy as np
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "static" / "bg.jpg"


def anime_local(img: np.ndarray) -> np.ndarray:
    """OpenCVによるカートゥーン/アニメ風変換（ローカル・無料）"""

    # 1) 彩度を上げる（アニメっぽい鮮やかな色）
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.5, 0, 255)
    hsv[..., 2] = np.clip(hsv[..., 2] * 1.05, 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 2) バイラテラルフィルタを重ねがけ（エッジを残しながら色面を滑らかに）
    smooth = img.copy()
    for _ in range(5):
        smooth = cv2.bilateralFilter(smooth, 9, 75, 75)

    # 3) エッジ検出
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(
        cv2.medianBlur(gray, 7), 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY, 9, 4
    )
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # 4) 滑らかな色面 × エッジ（線画）を合成
    result = cv2.bitwise_and(smooth, edges)

    return result


def anime_replicate(image_path: str) -> np.ndarray:
    """Replicate API（AnimeGAN2）で高品質変換"""
    import replicate, requests, tempfile

    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError(
            "REPLICATE_API_TOKEN 環境変数を設定してください\n"
            "取得: https://replicate.com/account/api-tokens"
        )

    with open(image_path, "rb") as f:
        output = replicate.run(
            "bryandlee/animegan2-pytorch:42f5de5d7db97e81e57ea0f3eb44a75e",
            input={"image": f, "face_detector": False}
        )

    img_data = requests.get(output).content
    arr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def main():
    args = sys.argv[1:]
    if not args:
        print("使い方: python convert_photo.py 写真.jpg [--api]")
        sys.exit(1)

    image_path = args[0]
    use_api    = "--api" in args

    if not Path(image_path).exists():
        print(f"ファイルが見つかりません: {image_path}")
        sys.exit(1)

    print(f"変換中: {image_path}")

    if use_api:
        print("Replicate API を使用（高品質）...")
        result = anime_replicate(image_path)
    else:
        print("ローカル変換を使用...")
        img    = cv2.imread(image_path)
        # 横幅1200pxに縮小（重すぎる場合）
        h, w   = img.shape[:2]
        if w > 1200:
            scale = 1200 / w
            img   = cv2.resize(img, (1200, int(h * scale)))
        result = anime_local(img)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(OUTPUT_PATH), result, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"完了 → {OUTPUT_PATH}")
    print("サーバーを再起動するとマップ背景に反映されます")


if __name__ == "__main__":
    main()
