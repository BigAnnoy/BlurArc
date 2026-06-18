"""
Blur Arc 海报生成脚本
- 设计哲学: docs/posters/design-philosophy.md (Silent Cartography)
- 输出: docs/posters/poster.png  (1600 x 2400, portrait 2:3)
- 字体: 优先使用 Noto Sans SC + Noto Serif SC + Consolas
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path
import math
import os

# ---------- 画布与配色 ----------
W, H = 1600, 2400
NAVY      = (14, 27, 44)       # 深夜蓝 #0E1B2C
NAVY_DEEP = (8, 16, 28)
GOLD      = (200, 168, 101)    # 暖金 #C8A865
GOLD_SOFT = (170, 145, 90)
PAPER     = (244, 241, 234)    # 纸白 #F4F1EA
MIST      = (138, 149, 165)    # 雾灰 #8A95A5
RULE      = (74, 88, 110)      # 冷灰分隔线

FONT_DIR = Path(r"C:\Windows\Fonts")

def font(name, size, idx=0):
    """载入字体，找不到则降级到默认"""
    p = FONT_DIR / name
    if p.exists():
        return ImageFont.truetype(str(p), size, index=idx)
    # 降级
    for cand in ["NotoSansSC-VF.ttf", "arial.ttf", "calibri.ttf"]:
        cp = FONT_DIR / cand
        if cp.exists():
            return ImageFont.truetype(str(cp), size)
    return ImageFont.load_default()

def cn_sans(size, weight=0):
    return font("NotoSansSC-VF.ttf", size, weight)

def cn_serif(size, weight=0):
    return font("NotoSerifSC-VF.ttf", size, weight)

def mono(size, bold=False):
    name = "consolab.ttf" if bold else "consola.ttf"
    return font(name, size)

def sans(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    return font(name, size)

# ---------- 画布 ----------
img = Image.new("RGB", (W, H), NAVY_DEEP)
draw = ImageDraw.Draw(img, "RGBA")

# 顶部柔光: 从中心向下淡出的暗金晕
for r in range(800, 0, -10):
    alpha = int(8 * (1 - r / 800))
    if alpha <= 0:
        continue
    draw.ellipse(
        [W // 2 - r, int(H * 0.18) - r, W // 2 + r, int(H * 0.18) + r],
        fill=(*GOLD_SOFT, alpha),
    )

# 底部柔光
for r in range(900, 0, -10):
    alpha = int(6 * (1 - r / 900))
    if alpha <= 0:
        continue
    draw.ellipse(
        [W // 2 - r, int(H * 0.82) - r, W // 2 + r, int(H * 0.82) + r],
        fill=(*GOLD_SOFT, alpha),
    )

# ---------- 页眉 ----------
M_L, M_R, M_T, M_B = 110, 110, 110, 110

# 顶部小印
draw.text((M_L, M_T), "B L U R   A R C",
          fill=PAPER, font=sans(22, bold=True), anchor="lt")
draw.text((M_L, M_T + 36), "A   S I L E N T   A R C H I V E",
          fill=MIST, font=mono(13), anchor="lt")

# 右上: 卷号 + 日期 + 帧计数
meta_lines = [
    "EDITION  01",
    "MMXXVI",
    "FRAME  24 / 36",
]
x_meta = W - M_R
y_meta = M_T
for line in meta_lines:
    bbox = draw.textbbox((0, 0), line, font=mono(13))
    w = bbox[2] - bbox[0]
    draw.text((x_meta - w, y_meta), line, fill=MIST, font=mono(13), anchor="lt")
    y_meta += 22

# 顶部金色细分隔线
draw.line([(M_L, 200), (W - M_R, 200)], fill=GOLD, width=1)
draw.line([(M_L, 200), (M_L + 90, 200)], fill=GOLD, width=3)

# ---------- 主视觉：层叠相框（contact sheet 现代变体） ----------
# 几何中心偏左下
cx, cy = 480, 1380
# 7 个相框，从大到小、从最透明到最实
frame_specs = [
    # (w, h, dx, dy, rot_deg, fill_alpha, stroke_alpha)
    (920, 660,  -40, -20,  -3.2, 22,  60),
    (820, 590,   20,  10,   1.8, 32,  80),
    (730, 525,  -15,  25,  -1.0, 44, 110),
    (640, 460,   30, -18,   2.4, 60, 150),
    (550, 395,  -20,  15,  -0.6, 80, 200),
    (470, 338,   18,  10,   0.8, 110, 240),
    (390, 280,    0,   0,   0.0, 200, 255),  # 最前
]

frame_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

for i, (fw, fh, dx, dy, rot, fa, sa) in enumerate(frame_specs):
    # 单个相框
    pad = 6
    fi = Image.new("RGBA", (fw + pad * 2, fh + pad * 2), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fi)
    # 内纸面
    fd.rectangle(
        [pad, pad, pad + fw, pad + fh],
        fill=(*PAPER, fa),
    )
    # 边框
    fd.rectangle(
        [pad, pad, pad + fw, pad + fh],
        outline=(*GOLD, sa),
        width=1,
    )
    # 顶部索引 (像底片序号)
    idx_label = f"{i+1:02d}"
    fd.text((pad + 14, pad + 10), idx_label, fill=(*GOLD, sa), font=mono(16))
    # 顶部右侧: 小尺寸
    if i == len(frame_specs) - 1:
        # 最前一张里放一个抽象山景
        # 天空
        fd.rectangle(
            [pad, pad, pad + fw, pad + int(fh * 0.55)],
            fill=(*MIST, int(fa * 0.3)),
        )
        # 山 (用两个梯形)
        m1 = [
            (pad, pad + int(fh * 0.55)),
            (pad + int(fw * 0.45), pad + int(fh * 0.30)),
            (pad + int(fw * 0.80), pad + int(fh * 0.55)),
        ]
        fd.polygon(m1, fill=(*NAVY, int(fa * 0.5)))
        m2 = [
            (pad + int(fw * 0.40), pad + int(fh * 0.55)),
            (pad + int(fw * 0.75), pad + int(fh * 0.35)),
            (pad + fw, pad + int(fh * 0.55)),
            (pad + fw, pad + fh),
            (pad, pad + fh),
        ]
        fd.polygon(m2, fill=(*NAVY_DEEP, int(fa * 0.85)))
        # 太阳
        sd = int(fw * 0.06)
        sx, sy = pad + int(fw * 0.30), pad + int(fh * 0.36)
        fd.ellipse([sx - sd, sy - sd, sx + sd, sy + sd],
                   fill=(*GOLD, int(fa * 0.9)))

    # 旋转后贴到主层
    fi = fi.rotate(rot, resample=Image.BICUBIC, expand=True)
    px = cx + dx - fi.size[0] // 2
    py = cy + dy - fi.size[1] // 2
    frame_layer.alpha_composite(fi, (px, py))

img.paste(frame_layer, (0, 0), frame_layer)

# 在最前相框上再画一道微金边 (强调)
front_w, front_h = 390, 280
front_pad = 6
front_rect = [
    cx - front_w // 2 - 4,
    cy - front_h // 2 - 4,
    cx + front_w // 2 + 4,
    cy + front_h // 2 + 4,
]
draw.rectangle(front_rect, outline=GOLD, width=2)

# ---------- 右侧标题区 ----------
tx = 980
ty = 280

# 一行小印记
draw.text((tx, ty), "— A   S I L E N T   M A N I F E S T O",
          fill=GOLD, font=mono(18), anchor="lt")
ty += 56

# 主标 1: Blur
f_blur = sans(190, bold=True)
draw.text((tx, ty), "Blur", fill=PAPER, font=f_blur, anchor="lt")
ty += 175

# 主标 2: Arc
f_arc = sans(190, bold=True)
draw.text((tx, ty), "Arc.", fill=GOLD, font=f_arc, anchor="lt")
# Arc 下方金线
arc_bbox = draw.textbbox((0, 0), "Arc.", font=f_arc)
arc_w = arc_bbox[2] - arc_bbox[0]
draw.line([(tx, ty + 185), (tx + arc_w, ty + 185)],
          fill=GOLD, width=2)
ty += 230

# 中文副标
f_zh = cn_serif(56)
draw.text((tx, ty), "静 默 整 理", fill=PAPER, font=f_zh, anchor="lt")
ty += 86

# 英文副标
f_sub = cn_serif(28)
draw.text((tx, ty), "Let photographs return to their order.",
          fill=MIST, font=f_sub, anchor="lt")
ty += 50

# 引文
f_quote = cn_serif(20)
draw.text((tx, ty), "「 数据不离机，按拍摄日期自动归档。 」",
          fill=GOLD_SOFT, font=f_quote, anchor="lt")

# ---------- 三个特征条 ----------
fy = 1700
# 分隔线
draw.line([(M_L, fy - 30), (W - M_R, fy - 30)], fill=RULE, width=1)

cols = [
    {
        "no":   "01",
        "en":   "L O C A L",
        "cn":   "本 地 运 行",
        "sub":  "无云端依赖",
    },
    {
        "no":   "02",
        "en":   "P R I V A T E",
        "cn":   "隐 私 零 泄 露",
        "sub":  "数据全程留于本机",
    },
    {
        "no":   "03",
        "en":   "D E D U P",
        "cn":   "智 能 去 重",
        "sub":  "MD5 精确比对 + 大小预筛",
    },
]
col_w = (W - M_L - M_R) / 3
for i, c in enumerate(cols):
    cx0 = M_L + i * col_w
    # 编号
    draw.text((cx0, fy), c["no"], fill=GOLD, font=mono(28, bold=True), anchor="lt")
    # 英文标题
    draw.text((cx0, fy + 42), c["en"], fill=PAPER, font=mono(18, bold=True), anchor="lt")
    # 中文
    draw.text((cx0, fy + 80), c["cn"], fill=PAPER, font=cn_sans(30), anchor="lt")
    # 副描述
    draw.text((cx0, fy + 130), c["sub"], fill=MIST, font=cn_serif(18), anchor="lt")
    # 列分隔
    if i < 2:
        x_div = cx0 + col_w - 1
        draw.line([(x_div, fy), (x_div, fy + 150)], fill=RULE, width=1)

# ---------- 底部签条 ----------
sy = H - 220
draw.line([(M_L, sy), (W - M_R, sy)], fill=GOLD, width=1)
draw.line([(M_L, sy), (M_L + 60, sy)], fill=GOLD, width=3)

# 中部品牌签条
draw.text((M_L, sy + 32), "让 照 片 回 归 秩 序",
          fill=PAPER, font=cn_serif(46), anchor="lt")
draw.text((M_L, sy + 100), "Blur Arc · 让 36 张底片各归其位。",
          fill=GOLD_SOFT, font=cn_serif(20), anchor="lt")

# 右侧: 坐标式元数据
right_meta = [
    "ARCHIVE   2026",
    "v 0.5.0  ·  MIT",
    "github.com/BigAnnoy/BlurArc",
]
ry = sy + 28
for line in right_meta:
    bbox = draw.textbbox((0, 0), line, font=mono(15))
    w = bbox[2] - bbox[0]
    draw.text((W - M_R - w, ry), line, fill=MIST, font=mono(15), anchor="lt")
    ry += 22

# 最底部签名号
sig_text = "N°  0001  /  0001"
bbox = draw.textbbox((0, 0), sig_text, font=mono(12))
w = bbox[2] - bbox[0]
draw.text((W - M_R - w, H - 60), sig_text, fill=GOLD_SOFT, font=mono(12), anchor="lt")

# ---------- 保存 ----------
out = Path("f:/AI/Frame_Album/docs/posters/poster.png")
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out, "PNG", optimize=True)

# 额外: 缩略图供快速预览
thumb = img.copy()
thumb.thumbnail((800, 1200))
thumb.save(out.with_name("poster-thumb.png"), "PNG", optimize=True)

# 导出为 JPEG (海报印刷常用)
img.convert("RGB").save(out.with_suffix(".jpg"), "JPEG",
                       quality=92, optimize=True, progressive=True)

print(f"OK -> {out}")
print(f"OK -> {out.with_suffix('.jpg')}")
print(f"OK -> {out.with_name('poster-thumb.png')}")
print(f"Size: {os.path.getsize(out)/1024:.1f} KB (PNG)")
print(f"Size: {os.path.getsize(out.with_suffix('.jpg'))/1024:.1f} KB (JPG)")
