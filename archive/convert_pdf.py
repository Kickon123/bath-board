"""
PDFを背景画像に変換するスクリプト
使い方: python convert_pdf.py
→ static/bg.png が生成される
"""
import sys
from pathlib import Path

BASE_DIR   = Path(__file__).parent
PDF_PATH   = BASE_DIR / "湯畑レイアウト.pdf"
OUT_PATH   = BASE_DIR / "static" / "bg.png"

def convert():
    if not PDF_PATH.exists():
        print(f"[NG] PDFが見つかりません: {PDF_PATH}")
        print("     bath_system フォルダに「湯畑レイアウト.pdf」を置いてください")
        sys.exit(1)

    import fitz  # pymupdf
    print(f"変換中: {PDF_PATH.name}")
    doc  = fitz.open(str(PDF_PATH))
    page = doc[0]

    # 高解像度で変換（3倍ズーム）
    mat = fitz.Matrix(3, 3)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(OUT_PATH))

    print(f"[OK] 変換完了: {OUT_PATH}")
    print(f"     サイズ: {pix.width} x {pix.height} px")

if __name__ == "__main__":
    convert()
