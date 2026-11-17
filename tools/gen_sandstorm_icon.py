"""生成沙尘暴 buff 图标 fx/sandstorm.png（Pillow，一次性脚本）。

风格对齐现有 buff 图标（fx/charm.png / lock.png / sacred_fire.png）：
  128x128 方形、半透明深色底、金色描边、中心符号。
沙尘暴 = 沙黄棕底 + 金色方框 + 中心三道旋转的沙暴漩涡 + 飘散沙粒。

用法：D:/pytools/python.exe tools/gen_sandstorm_icon.py
"""
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 128

# 配色（对齐圣火的棕底 + 金框）
BG = (92, 72, 44, 205)          # 沙棕半透明底
FRAME = (214, 170, 72, 255)     # 金框（和圣火同色系）
SWIRL = (240, 205, 110, 255)    # 漩涡主色：亮沙金
SWIRL_DARK = (170, 125, 50, 255)
SAND = (225, 190, 95, 255)      # 飘散沙粒


def main():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 底 + 金框（仿圣火：内缩 4px 的方框）
    d.rectangle([4, 4, SIZE - 5, SIZE - 5], fill=BG)
    d.rectangle([4, 4, SIZE - 5, SIZE - 5], outline=FRAME, width=4)
    d.rectangle([12, 12, SIZE - 13, SIZE - 13], outline=(120, 90, 45, 255), width=2)

    cx, cy = SIZE // 2, SIZE // 2

    # 三道旋转的沙暴弧：用点阵画螺旋，从内到外半径增大、角度旋转
    for arm in range(3):
        base_angle = arm * 2 * math.pi / 3
        pts = []
        for t in range(0, 100):
            frac = t / 99.0
            radius = 8 + frac * 40
            angle = base_angle + frac * 2.4          # 旋转 2.4 弧度
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            pts.append((x, y))
        # 画成有粗细的线：Pillow 的 line 用 joint="curve"
        d.line(pts, fill=SWIRL_DARK, width=7, joint="curve")
        d.line(pts, fill=SWIRL, width=3, joint="curve")

    # 中心小沙眼
    d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=SWIRL, outline=SWIRL_DARK, width=2)

    # 四周飘散的沙粒（点缀，仿圣火的小火星）
    for (px, py, r) in [(22, 30, 3), (104, 26, 2), (30, 100, 2), (102, 104, 3),
                        (64, 18, 2), (18, 66, 2), (110, 64, 2), (64, 112, 2)]:
        d.ellipse([px - r, py - r, px + r, py + r], fill=SAND)

    out = os.path.join(ROOT, "fx", "sandstorm.png")
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
