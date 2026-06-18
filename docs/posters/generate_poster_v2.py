"""
Blur Arc 海报 v2 - 稳健版
- 配色与软件一致 (来自 frontend/tailwind.config.js):
  PAGE #f4f7f9, CARD #ffffff, PRIMARY #0891b2
- 把 3 张软件截图嵌入 (docs/screenshots/ 下找不到即自动 UI mockup)
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import os, math

PAGE      = (244, 247, 249)
CARD      = (255, 255, 255)
PRIMARY   = (  8, 145, 178)
PRIMARY_H = ( 14, 116, 144)
PRIMARY_L = (224, 247, 250)
BORDER    = (216, 226, 232)
BORDER_S  = (184, 200, 212)
TEXT_P    = ( 26,  42,  58)
TEXT_S    = ( 90, 106, 122)
TEXT_T    = (138, 154, 170)

SHOTS_DIR = Path("f:/AI/Frame_Album/docs/screenshots")
OUT_DIR   = Path("f:/AI/Frame_Album/docs/posters")
FONT_DIR  = Path(r"C:\Windows\Fonts")

W, H = 1600, 2400

# ============ 字体 ============
def _f(path, size, idx=0):
    p = FONT_DIR / path
    if p.exists():
        try: return ImageFont.truetype(str(p), size, index=idx)
        except Exception: pass
    for cand in ["NotoSansSC-VF.ttf", "arial.ttf"]:
        cp = FONT_DIR / cand
        if cp.exists():
            try: return ImageFont.truetype(str(cp), size)
            except Exception: pass
    return ImageFont.load_default()

def sans(size, bold=False):
    return _f("arialbd.ttf" if bold else "arial.ttf", size)
def mono(size, bold=False):
    return _f("consolab.ttf" if bold else "consola.ttf", size)
def zh_sans(size, bold=False):
    for n in ["NotoSansSC-VF.ttf", "msyh.ttc", "simhei.ttf"]:
        try: return _f(n, size, 1 if bold and (n == "msyh.ttc" or n == "simhei.ttf") else 0)
        except Exception: continue
    return _f("arialbd.ttf" if bold else "arial.ttf", size)
def zh_serif(size, bold=False):
    for n in ["NotoSerifSC-VF.ttf", "msyh.ttc", "simhei.ttf"]:
        try: return _f(n, size, 1 if bold and (n == "msyh.ttc" or n == "simhei.ttf") else 0)
        except Exception: continue
    return _f("arialbd.ttf" if bold else "arial.ttf", size)

# ============ 辅助 ============
def tw(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def rrect_mask(ww, hh, r):
    m = Image.new("L", (max(1, ww), max(1, hh)), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, max(0, ww - 1), max(0, hh - 1)],
                                         radius=min(r, min(ww, hh) // 2), fill=255)
    return m

def rrect(im, box, fill, radius=12, outline=None, outline_w=1):
    x1, y1, x2, y2 = box
    ww, hh = max(1, x2 - x1), max(1, y2 - y1)
    layer = Image.new("RGBA", (ww, hh), (*fill, 255))
    mask = rrect_mask(ww, hh, radius)
    # 描边
    if outline:
        od = ImageDraw.Draw(layer)
        oc = outline if len(outline) == 4 else (*outline, 255)
        od.rounded_rectangle([0, 0, ww - 1, hh - 1],
                            radius=min(radius, min(ww, hh) // 2),
                            outline=oc, width=outline_w)
    base = im if im.mode == "RGBA" else im.convert("RGBA")
    base.paste(layer, (x1, y1), mask)
    return base

def rrect_bg(im, box, fill, radius=12):
    """纯色填充圆角矩形 (不处理 alpha 合成, 更快)"""
    x1, y1, x2, y2 = box
    ww, hh = max(1, x2 - x1), max(1, y2 - y1)
    patch = Image.new("RGB", (ww, hh), fill)
    mask = rrect_mask(ww, hh, radius)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    im.paste(patch, (x1, y1), mask)
    return im

def add_shadow(img_rgba, box, radius=18, softness=5, opacity=0.18, offs=(3, 6)):
    x1, y1, x2, y2 = box
    ww, hh = x2 - x1 + softness * 4, y2 - y1 + softness * 4
    s = Image.new("RGBA", (ww, hh), (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle(
        [softness, softness, ww - softness, hh - softness],
        radius=radius, fill=(10, 30, 50, int(255 * opacity)))
    s = s.filter(ImageFilter.GaussianBlur(radius=softness))
    img_rgba.paste(s, (x1 - softness + offs[0], y1 - softness + offs[1]), s)
    return img_rgba

# ============ UI mockups ============
def make_welcome_mock(ww, hh):
    im = Image.new("RGB", (ww, hh), PAGE)
    d = ImageDraw.Draw(im)

    # 相机图标
    cw, ch = int(ww * 0.22), int(ww * 0.13)
    cx, cy = ww // 2, int(hh * 0.35)
    # 机身
    im = rrect_bg(im, [cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2], CARD, radius=int(ch * 0.22))
    d = ImageDraw.Draw(im)
    d.rectangle([cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2],
               outline=BORDER, width=1)
    # 顶部小突起
    tw2 = int(cw * 0.22)
    im = rrect_bg(im, [cx - tw2 // 2, cy - ch // 2 - int(ch * 0.15),
                        cx + tw2 // 2, cy - ch // 2 + 4], CARD, radius=int(ch * 0.1))
    d = ImageDraw.Draw(im)
    d.rectangle([cx - tw2 // 2, cy - ch // 2 - int(ch * 0.15),
                 cx + tw2 // 2, cy - ch // 2 + 4], outline=BORDER, width=1)
    # 镜头
    lr = int(ch * 0.42)
    d.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], fill=PRIMARY_L, outline=PRIMARY, width=3)
    d.ellipse([cx - int(lr * 0.6), cy - int(lr * 0.6),
               cx + int(lr * 0.6), cy + int(lr * 0.6)], fill=PRIMARY, outline=PRIMARY_H, width=2)

    # 标题
    title = "欢迎使用 Blur Arc"
    fs = int(min(ww * 0.045, 42))
    tfont = zh_sans(fs, bold=True)
    tw_, _ = tw(d, title, tfont)
    d.text((cx - tw_ // 2, cy + ch // 2 + 20), title, fill=TEXT_P, font=tfont)

    # 描述
    desc = "让我们开始设置您的相册"
    dfs = int(fs * 0.55)
    df = zh_sans(dfs)
    dw_, _ = tw(d, desc, df)
    d.text((cx - dw_ // 2, cy + ch // 2 + 20 + fs + 10), desc, fill=TEXT_S, font=df)

    # 主按钮
    btn_w = int(ww * 0.45)
    btn_h = int(hh * 0.12)
    by = cy + ch // 2 + 20 + fs + 10 + dfs + 30
    im = rrect_bg(im, [cx - btn_w // 2, by, cx + btn_w // 2, by + btn_h], PRIMARY, radius=int(btn_h * 0.2))
    d = ImageDraw.Draw(im)
    bt = "选择相册文件夹"
    bfs = int(btn_h * 0.38)
    bf = zh_sans(bfs, bold=True)
    bw_, _ = tw(d, bt, bf)
    d.text((cx - bw_ // 2, by + btn_h // 2 - bfs // 2 - 2), bt,
           fill=(255, 255, 255), font=bf)

    # 提示
    hint = "建议选择空文件夹，您可以随时在设置中更改相册路径"
    hfs = max(10, int(btn_h * 0.28))
    hf = zh_sans(hfs)
    hw_, _ = tw(d, hint, hf)
    d.text((cx - hw_ // 2, by + btn_h + 18), hint, fill=TEXT_T, font=hf)

    return im


def make_main_mock(ww, hh):
    im = Image.new("RGB", (ww, hh), PAGE)
    d = ImageDraw.Draw(im)

    sb_w = int(ww * 0.22)
    hbar = max(40, int(hh * 0.07))

    # 顶栏背景
    d.rectangle([0, 0, ww, hbar], fill=CARD)
    d.line([(0, hbar - 1), (ww, hbar - 1)], fill=BORDER, width=1)

    # 顶栏文字
    d.text((int(ww * 0.02), int(hbar * 0.25)), "Blur", fill=TEXT_P, font=sans(int(hbar * 0.5), bold=True))
    arc_w, _ = tw(d, " Arc", sans(int(hbar * 0.5)))
    d.text((int(ww * 0.02) + int(tw(d, "Blur", sans(int(hbar * 0.5), bold=True))[0]) + 4,
            int(hbar * 0.25)),
           " Arc", fill=PRIMARY, font=sans(int(hbar * 0.5)))

    # 顶栏右侧按钮
    bsize = int(hbar * 0.7)
    bx = ww - bsize - int(ww * 0.02)
    im = rrect_bg(im, [bx, (hbar - bsize) // 2, bx + bsize, (hbar - bsize) // 2 + bsize],
                  PAGE, radius=int(bsize * 0.2))
    d = ImageDraw.Draw(im)
    d.rectangle([bx, (hbar - bsize) // 2, bx + bsize, (hbar - bsize) // 2 + bsize], outline=BORDER, width=1)

    # 侧边栏
    d.rectangle([0, hbar, sb_w, hh], fill=CARD)
    d.line([(sb_w - 1, hbar), (sb_w - 1, hh)], fill=BORDER, width=1)

    # 统计卡片 1
    cw, ch_ = int(sb_w * 0.88), int(hh * 0.07)
    cx_s = (sb_w - cw) // 2
    cy_s = hbar + int(hh * 0.025)
    im = rrect_bg(im, [cx_s, cy_s, cx_s + cw, cy_s + ch_], PAGE, radius=int(ch_ * 0.2))
    d = ImageDraw.Draw(im)
    d.rectangle([cx_s, cy_s, cx_s + cw, cy_s + ch_], outline=BORDER, width=1)
    num_f = int(ch_ * 0.6)
    d.text((cx_s + 12, cy_s + int(ch_ * 0.1)), "42", fill=PRIMARY, font=mono(num_f, bold=True))
    lbl_f = int(ch_ * 0.32)
    d.text((cx_s + int(cw * 0.45), cy_s + int(ch_ * 0.3)), "文件", fill=TEXT_S, font=zh_sans(lbl_f))

    # 月份列表 (只画一个高亮项示意)
    row_h = int(hh * 0.05)
    ry = cy_s + ch_ + int(hh * 0.02)
    for i, (mname, mc) in enumerate([("六月", "42"), ("五月", "18"), ("四月", "7")]):
        is_act = (i == 0)
        rx, ry2 = cx_s, ry + i * (row_h + 6)
        if ry2 + row_h > hh - int(hh * 0.15): break
        if is_act:
            im = rrect_bg(im, [rx, ry2, rx + cw, ry2 + row_h], PRIMARY, radius=int(row_h * 0.2))
            d = ImageDraw.Draw(im)
            mf = int(row_h * 0.5)
            d.text((rx + 12, ry2 + int(row_h * 0.25)),
                   f"  {mname}", fill=(255, 255, 255), font=zh_sans(mf, bold=True))
            cw_, _ = tw(d, mc, mono(int(row_h * 0.4)))
            d.text((rx + cw - 12 - cw_, ry2 + int(row_h * 0.3)), mc,
                   fill=(255, 255, 255), font=mono(int(row_h * 0.4)))
        else:
            mf = int(row_h * 0.5)
            d.text((rx + 12, ry2 + int(row_h * 0.25)),
                   f"  {mname}", fill=TEXT_S, font=zh_sans(mf))
            cw_, _ = tw(d, mc, mono(int(row_h * 0.4)))
            d.text((rx + cw - 12 - cw_, ry2 + int(row_h * 0.3)), mc,
                   fill=TEXT_T, font=mono(int(row_h * 0.4)))

    # 底部 "导入照片" 按钮
    bbtn_h = int(hh * 0.07)
    bbtn_w = int(sb_w * 0.88)
    bbx = (sb_w - bbtn_w) // 2
    bby = hh - bbtn_h - int(hh * 0.02)
    im = rrect_bg(im, [bbx, bby, bbx + bbtn_w, bby + bbtn_h], PRIMARY, radius=int(bbtn_h * 0.2))
    d = ImageDraw.Draw(im)
    bt = "导入照片"
    bfs = int(bbtn_h * 0.42)
    bw_, _ = tw(d, bt, zh_sans(bfs, bold=True))
    d.text((bbx + bbtn_w // 2 - bw_ // 2, bby + bbtn_h // 2 - bfs // 2 - 2),
           bt, fill=(255, 255, 255), font=zh_sans(bfs, bold=True))

    # 右侧: "照片 · 42 张"
    rx_start = sb_w + int(ww * 0.02)
    d.text((rx_start, hbar + int(hh * 0.025)),
           "照片 · 42 张", fill=TEXT_P,
           font=zh_sans(int(hbar * 0.45), bold=True))

    # 右侧选择按钮
    rsel_w = int(ww * 0.08)
    rsel_h = int(hbar * 0.75)
    rsx = ww - rsel_w - int(ww * 0.02)
    im = rrect_bg(im, [rsx, hbar + int(hh * 0.022), rsx + rsel_w, hbar + int(hh * 0.022) + rsel_h],
                  CARD, radius=int(rsel_h * 0.2))
    d = ImageDraw.Draw(im)
    d.rectangle([rsx, hbar + int(hh * 0.022), rsx + rsel_w, hbar + int(hh * 0.022) + rsel_h],
                outline=BORDER, width=1)
    st = "选择"
    stf = int(rsel_h * 0.45)
    stw_, _ = tw(d, st, zh_sans(stf))
    d.text((rsx + rsel_w // 2 - stw_ // 2, hbar + int(hh * 0.022) + rsel_h // 2 - stf // 2 - 2),
           st, fill=TEXT_P, font=zh_sans(stf))

    # 照片网格 (4x3)
    gy = hbar + int(hh * 0.1)
    g_area_x1 = sb_w + int(ww * 0.015)
    g_area_x2 = ww - int(ww * 0.015)
    g_area_y1 = gy
    g_area_y2 = hh - int(hh * 0.02)
    gcols, grows = 5, 4
    gap = max(6, int(min(ww, hh) * 0.007))
    cell_w = (g_area_x2 - g_area_x1 - gap * (gcols + 1)) // gcols
    cell_h = (g_area_y2 - g_area_y1 - gap * (grows + 1)) // grows
    if cell_w > 0 and cell_h > 0:
        palette = [
            (200, 230, 240), (180, 210, 235), (220, 225, 235), (195, 205, 225), (215, 235, 245),
            (175, 200, 225), (205, 215, 230), (190, 220, 240), (210, 230, 235), (185, 205, 225),
            (200, 225, 240), (170, 195, 220), (220, 235, 245), (195, 220, 235), (180, 210, 230),
            (205, 225, 240), (215, 230, 242), (190, 215, 235), (200, 220, 238), (175, 205, 225),
        ]
        for r in range(grows):
            for c in range(gcols):
                idx = r * gcols + c
                if idx >= len(palette): break
                px = g_area_x1 + gap + c * (cell_w + gap)
                py = g_area_y1 + gap + r * (cell_h + gap)
                color = palette[idx]
                grad = Image.new("RGB", (cell_w, cell_h), color)
                gd = ImageDraw.Draw(grad)
                for i in range(cell_h):
                    k = i / cell_h
                    col = (int(color[0] * (1 - k * 0.25)),
                           int(color[1] * (1 - k * 0.2)),
                           int(color[2] * (1 - k * 0.15)))
                    gd.line([(0, i), (cell_w, i)], fill=col, width=1)
                mask = rrect_mask(cell_w, cell_h, min(10, cell_w // 8))
                if im.mode != "RGBA":
                    im = im.convert("RGBA")
                im.paste(grad, (px, py), mask)

    return im


def make_import_mock(ww, hh):
    im = Image.new("RGB", (ww, hh), PAGE)
    d = ImageDraw.Draw(im)

    # 整体背景稍暗
    d.rectangle([0, 0, ww, hh], fill=(225, 232, 238))

    # 中央对话框 (比例)
    dw = int(ww * 0.80)
    dh = int(hh * 0.82)
    dx = (ww - dw) // 2
    dy = (hh - dh) // 2

    # 阴影
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    im = add_shadow(im, [dx, dy, dx + dw, dy + dh],
                    radius=int(dh * 0.07), softness=6, opacity=0.22, offs=(3, 6))

    # 对话框主体
    im = rrect_bg(im, [dx, dy, dx + dw, dy + dh], CARD, radius=int(dh * 0.05))
    d = ImageDraw.Draw(im)
    # 描边
    d.rounded_rectangle([dx, dy, dx + dw - 1, dy + dh - 1],
                       radius=int(dh * 0.05), outline=BORDER_S, width=1)

    # 顶部标题区
    head_h = int(dh * 0.12)
    d.text((dx + int(dw * 0.03), dy + int(head_h * 0.35)),
           "预览导入", fill=TEXT_P,
           font=zh_sans(int(head_h * 0.45), bold=True))
    # 关闭按钮
    cb = int(head_h * 0.7)
    cbx = dx + dw - cb - int(dw * 0.03)
    im = rrect_bg(im, [cbx, dy + (head_h - cb) // 2, cbx + cb, dy + (head_h - cb) // 2 + cb],
                  PAGE, radius=int(cb * 0.2))
    d = ImageDraw.Draw(im)
    d.rectangle([cbx, dy + (head_h - cb) // 2, cbx + cb, dy + (head_h - cb) // 2 + cb],
                outline=BORDER, width=1)

    # 分隔线
    sep_y = dy + head_h
    d.line([(dx + int(dw * 0.03), sep_y), (dx + dw - int(dw * 0.03), sep_y)],
           fill=BORDER, width=1)

    # 统计区
    stat_y = sep_y + int(dh * 0.03)
    sfs = int(dh * 0.045)
    d.text((dx + int(dw * 0.03), stat_y), "总文件个数",
           fill=TEXT_S, font=zh_sans(sfs))
    num_w, _ = tw(d, "42", mono(int(sfs * 1.25), bold=True))
    d.text((dx + int(dw * 0.03) + int(dw * 0.10), stat_y - int(sfs * 0.1)),
           "42", fill=PRIMARY, font=mono(int(sfs * 1.25), bold=True))
    d.text((dx + int(dw * 0.03) + int(dw * 0.18), stat_y),
           "总大小", fill=TEXT_S, font=zh_sans(sfs))
    d.text((dx + int(dw * 0.03) + int(dw * 0.24), stat_y - int(sfs * 0.1)),
           "45.3 MB", fill=PRIMARY, font=mono(int(sfs * 1.25), bold=True))

    # 标签页
    tab_y = stat_y + int(dh * 0.08)
    tabs = [("时间线", True), ("已在相册", False), ("文件夹内重复", False)]
    tx_ = dx + int(dw * 0.03)
    for tname, active in tabs:
        tf = zh_sans(sfs, bold=True)
        tw_, _ = tw(d, tname, tf)
        pad = int(sfs * 1.2)
        if active:
            im = rrect_bg(im, [tx_ - pad, tab_y - pad, tx_ + tw_ + pad, tab_y + sfs + pad],
                         CARD, radius=8)
            d = ImageDraw.Draw(im)
            d.rectangle([tx_ - pad, tab_y - pad, tx_ + tw_ + pad, tab_y + sfs + pad],
                       outline=BORDER, width=1)
            d.rectangle([tx_ - pad, tab_y - pad - 2, tx_ + tw_ + pad, tab_y - pad],
                       fill=PRIMARY)
            d.text((tx_, tab_y), tname, fill=TEXT_P, font=tf)
        else:
            d.text((tx_ + pad, tab_y), tname, fill=TEXT_S, font=zh_sans(sfs))
        tx_ += tw_ + pad * 4

    # 内容区
    list_x = dx + int(dw * 0.03)
    list_y = tab_y + sfs + int(dh * 0.05)
    list_w = int(dw * 0.22)
    list_h = int(dh * 0.45)
    list_h = max(30, list_h)
    list_r = int(list_h * 0.04)
    im = rrect_bg(im, [list_x, list_y, list_x + list_w, list_y + list_h],
                 PAGE, radius=list_r)
    d = ImageDraw.Draw(im)
    d.rectangle([list_x, list_y, list_x + list_w, list_y + list_h],
               outline=BORDER, width=1)

    # 日期列表
    row_h = max(24, int(list_h * 0.12))
    ry = list_y + int(list_h * 0.03)
    for idx, (dname, cnt) in enumerate([("2026-06", "42"), ("2026-05", "18"), ("2026-04", "7")]):
        ryy = ry + idx * (row_h + 4)
        if ryy + row_h > list_y + list_h - 8: break
        is_act = (idx == 0)
        rx1 = list_x + 8
        rx2 = list_x + list_w - 8
        if is_act:
            im = rrect_bg(im, [rx1, ryy, rx2, ryy + row_h], PRIMARY, radius=int(row_h * 0.25))
            d = ImageDraw.Draw(im)
            rf = int(row_h * 0.45)
            d.text((rx1 + 10, ryy + int(row_h * 0.28)),
                   dname, fill=(255, 255, 255), font=zh_sans(rf, bold=True))
            cw_, _ = tw(d, cnt, mono(int(row_h * 0.38)))
            d.text((rx2 - 10 - cw_, ryy + int(row_h * 0.32)),
                   cnt, fill=(255, 255, 255), font=mono(int(row_h * 0.38)))
        else:
            rf = int(row_h * 0.45)
            d.text((rx1 + 10, ryy + int(row_h * 0.28)),
                   dname, fill=TEXT_S, font=zh_sans(rf))
            cw_, _ = tw(d, cnt, mono(int(row_h * 0.38)))
            d.text((rx2 - 10 - cw_, ryy + int(row_h * 0.32)),
                   cnt, fill=TEXT_T, font=mono(int(row_h * 0.38)))

    # 右侧预览
    prev_x = list_x + list_w + int(dw * 0.02)
    prev_y = list_y
    prev_w = dx + dw - prev_x - int(dw * 0.03)
    prev_h = list_h
    if prev_w > 20 and prev_h > 20:
        im = rrect_bg(im, [prev_x, prev_y, prev_x + prev_w, prev_y + prev_h],
                     PAGE, radius=list_r)
        d = ImageDraw.Draw(im)
        d.rectangle([prev_x, prev_y, prev_x + prev_w, prev_y + prev_h],
                   outline=BORDER, width=1)
        # 缩略图网格
        gc, gr = 5, 3
        gp = max(4, int(min(prev_w, prev_h) * 0.015))
        icw = (prev_w - gp * (gc + 1)) // gc
        ich = (prev_h - gp * (gr + 1)) // gr
        if icw > 4 and ich > 4:
            pic_palette = [
                (200, 230, 240), (180, 215, 238), (220, 228, 238), (198, 212, 230), (218, 235, 245),
                (178, 202, 228), (208, 222, 236), (192, 222, 242), (212, 232, 238), (188, 210, 228),
                (204, 226, 240), (172, 200, 224), (222, 236, 246), (196, 220, 236), (182, 214, 232),
            ]
            for r_ in range(gr):
                for c_ in range(gc):
                    idx = r_ * gc + c_
                    if idx >= len(pic_palette): break
                    pix = prev_x + gp + c_ * (icw + gp)
                    piy = prev_y + gp + r_ * (ich + gp)
                    color = pic_palette[idx]
                    grad = Image.new("RGB", (icw, ich), color)
                    gd = ImageDraw.Draw(grad)
                    for i in range(ich):
                        k = i / ich
                        col = (int(color[0] * (1 - k * 0.25)),
                               int(color[1] * (1 - k * 0.2)),
                               int(color[2] * (1 - k * 0.15)))
                        gd.line([(0, i), (icw, i)], fill=col, width=1)
                    mask = rrect_mask(icw, ich, min(8, icw // 6))
                    if im.mode != "RGBA":
                        im = im.convert("RGBA")
                    im.paste(grad, (pix, piy), mask)

    # 底部返回/开始导入按钮
    btn_h = int(dh * 0.08)
    by = dy + dh - btn_h - int(dh * 0.03)
    # 返回
    back_w = int(dw * 0.14)
    im = rrect_bg(im, [dx + int(dw * 0.03), by,
                       dx + int(dw * 0.03) + back_w, by + btn_h],
                 PAGE, radius=int(btn_h * 0.2))
    d = ImageDraw.Draw(im)
    d.rectangle([dx + int(dw * 0.03), by,
                 dx + int(dw * 0.03) + back_w, by + btn_h], outline=BORDER, width=1)
    rt = "返回"
    rtf = int(btn_h * 0.42)
    rtw_, _ = tw(d, rt, zh_sans(rtf))
    d.text((dx + int(dw * 0.03) + back_w // 2 - rtw_ // 2,
            by + btn_h // 2 - rtf // 2 - 2),
           rt, fill=TEXT_P, font=zh_sans(rtf))

    # 开始导入
    start_w = int(dw * 0.20)
    sx = dx + dw - start_w - int(dw * 0.03)
    im = rrect_bg(im, [sx, by, sx + start_w, by + btn_h],
                 PRIMARY, radius=int(btn_h * 0.2))
    d = ImageDraw.Draw(im)
    st = "开始导入"
    stf = int(btn_h * 0.42)
    stw_, _ = tw(d, st, zh_sans(stf, bold=True))
    d.text((sx + start_w // 2 - stw_ // 2,
            by + btn_h // 2 - stf // 2 - 2),
           st, fill=(255, 255, 255), font=zh_sans(stf, bold=True))

    return im


def load_or_mock(shot_name, tw_, th_, make_fn):
    candidates = [SHOTS_DIR / shot_name,
                  SHOTS_DIR / shot_name.replace(".png", ".jpg"),
                  SHOTS_DIR / shot_name.replace(".png", ".jpeg")]
    for c in candidates:
        if c.exists() and c.stat().st_size > 0:
            try:
                sim = Image.open(c).convert("RGB")
                sw, sh = sim.size
                ratio = tw_ / th_
                sratio = sw / sh
                if sratio > ratio:
                    nh = th_
                    nw = int(th_ * sratio)
                    sim = sim.resize((nw, nh), Image.LANCZOS)
                    sim = sim.crop([(nw - tw_) // 2, 0, (nw - tw_) // 2 + tw_, nh])
                else:
                    nw = tw_
                    nh = int(tw_ / sratio)
                    sim = sim.resize((nw, nh), Image.LANCZOS)
                    sim = sim.crop([0, (nh - th_) // 2, nw, (nh - th_) // 2 + th_])
                print(f"  📷 使用真实截图: {c.name} ({tw_}x{th_})")
                return sim
            except Exception as e:
                print(f"  [warn] 读取 {c.name} 失败: {e}")
    print(f"  ✏️  {shot_name} 未找到, 使用 UI mockup")
    return make_fn(tw_, th_)


# ============ 组装海报 ============
img = Image.new("RGB", (W, H), PAGE).convert("RGBA")
draw = ImageDraw.Draw(img)

# 顶部一条细青线
draw.rectangle([0, 0, W, 6], fill=PRIMARY)

# 顶部装饰光晕 (几处柔和青色叠加, 让页面不过白)
decor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dd = ImageDraw.Draw(decor)
for cx, cy, r, op in [(W * 0.10, H * 0.02, 600, 0.055),
                      (W * 0.92, H * 0.10, 500, 0.05),
                      (W * 0.78, H * 0.55, 480, 0.035),
                      (W * 0.12, H * 0.68, 520, 0.035)]:
    _r = int(r)
    for step in range(100, 0, -4):
        a = int(255 * op * (step / 100))
        dd.ellipse([cx - _r * step / 100, cy - _r * step / 100,
                     cx + _r * step / 100, cy + _r * step / 100],
                   fill=(*PRIMARY, a))
img = Image.alpha_composite(img, decor)
draw = ImageDraw.Draw(img)

# ------------- 顶部品牌 -------------
margin = 80
draw.text((margin, 48), "Blur", fill=TEXT_P, font=sans(40, bold=True))
draw.text((margin + int(tw(draw, "Blur", sans(40, bold=True))[0]) + 4, 48),
          " Arc", fill=PRIMARY, font=sans(40))
meta = "v 0 . 5 . 0"
mtw, _ = tw(draw, meta, mono(18))
draw.text((W - margin - mtw, 60), meta, fill=TEXT_T, font=mono(18))
draw.line([(margin, 120), (W - margin, 120)], fill=BORDER, width=1)

# ------------- 主标题 -------------
ty = 170
title = "让照片回归秩序"
tfont = zh_serif(108, bold=True)
tw_, _ = tw(draw, title, tfont)
draw.text((W // 2 - tw_ // 2, ty), title, fill=TEXT_P, font=tfont)

en = "Your photos, in their place — locally, privately."
ef = sans(30, bold=True)
ew_, _ = tw(draw, en, ef)
draw.text((W // 2 - ew_ // 2, ty + 120), en, fill=PRIMARY, font=ef)

zh_sub = "完全本地运行 · 隐私零泄露 · 无云端依赖"
zsf = zh_sans(28)
zw_, _ = tw(draw, zh_sub, zsf)
draw.text((W // 2 - zw_ // 2, ty + 170), zh_sub, fill=TEXT_S, font=zsf)

# ------------- 主视觉: 大截图 (主相册浏览) -------------
shot1_w = W - margin * 2
shot1_h = int(H * 0.33)
shot1_x = margin
shot1_y = ty + 240

# 加载/生成
shot_main = load_or_mock("02-main-view.png", shot1_w, shot1_h, make_main_mock)

# 卡片 (带阴影 + 边框)
card_pad = 12
cw_ = shot1_w + card_pad * 2
ch_ = shot1_h + card_pad * 2
img = add_shadow(img, [shot1_x - card_pad, shot1_y - card_pad,
                        shot1_x - card_pad + cw_, shot1_y - card_pad + ch_],
                 radius=22, softness=7, opacity=0.22, offs=(3, 7))

# 卡片底板
card_bg = Image.new("RGB", (cw_, ch_), CARD)
card_mask = rrect_mask(cw_, ch_, 20)
if img.mode != "RGBA":
    img = img.convert("RGBA")
img.paste(card_bg, (shot1_x - card_pad, shot1_y - card_pad), card_mask)
# 边框描边
stroke_layer = Image.new("RGBA", (cw_, ch_), (0, 0, 0, 0))
ImageDraw.Draw(stroke_layer).rounded_rectangle([0, 0, cw_ - 1, ch_ - 1],
                                                 radius=20, outline=(*BORDER_S, 255), width=2)
img.paste(stroke_layer, (shot1_x - card_pad, shot1_y - card_pad), stroke_layer)

# 截图圆角贴入
shot_mask = rrect_mask(shot1_w, shot1_h, 14)
shot_rgba = Image.new("RGBA", (shot1_w, shot1_h), (0, 0, 0, 0))
shot_rgba.paste(shot_main.convert("RGB"), (0, 0))
img.paste(shot_rgba, (shot1_x, shot1_y), shot_mask)
draw = ImageDraw.Draw(img)

# 顶部小徽标
label_text = "①  主相册浏览界面"
llf = mono(18, bold=True)
ltw, _ = tw(draw, label_text, llf)
im = rrect_bg(Image.new("RGB", (ltw + 40, 38), PRIMARY),
              [0, 0, ltw + 40, 38], PRIMARY, radius=8)
ImageDraw.Draw(im).text((20, 10), label_text, fill=(255, 255, 255), font=llf)
if img.mode != "RGBA": img = img.convert("RGBA")
img.paste(im, (shot1_x + 24, shot1_y - 18))
draw = ImageDraw.Draw(img)

# ------------- 两张小截图 -------------
small_w = (W - margin * 2 - 40) // 2
small_h = int(small_w * 0.55)
small_y = shot1_y + shot1_h + 70

for idx, (shot_file, make_fn, title_t, desc_t, num_label) in enumerate([
    ("01-welcome.png", make_welcome_mock,
     "首次启动引导", "选择相册目录 · 一键上手", "②"),
    ("03-import-preview.png", make_import_mock,
     "智能导入预检", "重复检测 · 时间线 · 去重一目了然", "③"),
]):
    sx = margin + idx * (small_w + 40)
    sy = small_y

    # 加载
    simg = load_or_mock(shot_file, small_w, small_h, make_fn)

    # 卡片高度 (截图 + 底部信息带)
    card_h = small_h + 140
    card_w = small_w

    # 阴影
    img = add_shadow(img, [sx - 10, sy - 10, sx - 10 + card_w + 20, sy - 10 + card_h + 20],
                     radius=18, softness=6, opacity=0.18, offs=(3, 6))
    # 卡片底板
    card_mask = rrect_mask(card_w, card_h, 18)
    card_bg = Image.new("RGB", (card_w, card_h), CARD)
    if img.mode != "RGBA": img = img.convert("RGBA")
    img.paste(card_bg, (sx, sy), card_mask)
    # 描边
    stroke = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    ImageDraw.Draw(stroke).rounded_rectangle([0, 0, card_w - 1, card_h - 1],
                                              radius=18, outline=(*BORDER, 255), width=1)
    img.paste(stroke, (sx, sy), stroke)

    # 贴截图 (圆角)
    s_pad = 16
    inner_w = small_w - s_pad * 2
    inner_h = small_h - s_pad
    if inner_w > 20 and inner_h > 20:
        simg2 = simg.resize((inner_w, inner_h), Image.LANCZOS)
        sm = rrect_mask(inner_w, inner_h, 12)
        sr = Image.new("RGBA", (inner_w, inner_h), (0, 0, 0, 0))
        sr.paste(simg2.convert("RGB"), (0, 0))
        img.paste(sr, (sx + s_pad, sy + s_pad), sm)

    draw = ImageDraw.Draw(img)

    # 序号徽标 (圆)
    badge_r = 24
    bcy = sy + small_h + 50
    bcx = sx + 32 + badge_r
    draw.ellipse([bcx - badge_r, bcy - badge_r, bcx + badge_r, bcy + badge_r],
                fill=PRIMARY)
    nf = sans(24, bold=True)
    nw_, _ = tw(draw, num_label, nf)
    draw.text((bcx - nw_ // 2, bcy - 14), num_label, fill=(255, 255, 255), font=nf)

    # 标题
    tf = zh_sans(28, bold=True)
    draw.text((bcx + badge_r + 20, bcy - 14), title_t, fill=TEXT_P, font=tf)

    # 描述
    df = zh_sans(18)
    draw.text((bcx + badge_r + 20, bcy + 20), desc_t, fill=TEXT_S, font=df)

    # 右下箭头
    arrow = "→"
    af = sans(44, bold=True)
    aw_, _ = tw(draw, arrow, af)
    draw.text((sx + card_w - 40 - aw_, bcy + 4), arrow, fill=PRIMARY, font=af)

# ------------- 三列功能亮点 -------------
feat_y = small_y + small_h + 210
# 分隔线 + 标题
draw.line([(margin, feat_y - 60), (W - margin, feat_y - 60)], fill=BORDER, width=1)
draw.ellipse([margin - 6, feat_y - 66, margin + 6, feat_y - 54], fill=PRIMARY)
ft = "核心能力"
ftf = zh_sans(28, bold=True)
draw.text((margin + 24, feat_y - 78), ft, fill=TEXT_P, font=ftf)
en_feat = "CORE  CAPABILITIES"
enfw, _ = tw(draw, en_feat, mono(22, bold=True))
draw.text((W - margin - enfw, feat_y - 76), en_feat, fill=TEXT_T, font=mono(22, bold=True))

fc = 3
f_gap = 40
fw = (W - margin * 2 - f_gap * (fc - 1)) // fc
fh = 260

feat_items = [
    ("LOCAL  ·  本地运行", "数据不离机",
     ["按拍摄日期自动归档到",
      "YYYY-MM 目录结构, 全程",
      "在本机磁盘完成。"],
     ["零云端依赖", "离线可用"]),
    ("PRIVATE  ·  隐私", "隐私零泄露",
     ["不上传、不分析、不收集",
      "任何数据。所有处理在",
      "你的设备上完成。"],
     ["无需账号", "不联网使用"]),
    ("DEDUP  ·  去重", "智能去重",
     ["文件大小预筛 + MD5 精确",
      "比对, 减少 99% 的无效 I/O,",
      "导入时实时检测。"],
     ["实时预检", "去重一目了然"]),
]

for i in range(fc):
    fi = feat_items[i]
    (tag, title_t, descs), pills = (fi[0], fi[1], fi[2]), fi[3]

    cx = margin + i * (fw + f_gap)
    cy = feat_y

    # 阴影
    img = add_shadow(img, [cx - 8, cy - 8, cx + fw + 8, cy + fh + 8],
                     radius=18, softness=6, opacity=0.18, offs=(3, 6))
    # 底板
    cm = rrect_mask(fw, fh, 16)
    cb = Image.new("RGB", (fw, fh), CARD)
    if img.mode != "RGBA": img = img.convert("RGBA")
    img.paste(cb, (cx, cy), cm)
    stroke = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    ImageDraw.Draw(stroke).rounded_rectangle([0, 0, fw - 1, fh - 1],
                                              radius=16, outline=(*BORDER, 255), width=1)
    img.paste(stroke, (cx, cy), stroke)
    # 左侧主色条
    ImageDraw.Draw(img).rectangle([cx, cy, cx + 4, cy + fh], fill=PRIMARY)

    draw = ImageDraw.Draw(img)
    # tag
    draw.text((cx + 32, cy + 28), tag, fill=PRIMARY, font=mono(18, bold=True))
    # title
    draw.text((cx + 32, cy + 58), title_t, fill=TEXT_P, font=zh_sans(36, bold=True))
    # description lines
    ly = cy + 114
    for line in descs:
        draw.text((cx + 32, ly), line, fill=TEXT_S, font=zh_sans(20))
        ly += 30

    # pill badges
    pill_y = cy + fh - 44
    ppx = cx + 32
    for ptext in pills:
        pf = zh_sans(18)
        pw_, _ = tw(draw, ptext, pf)
        pw_total = pw_ + 24
        ph_total = 36
        pm = rrect_mask(pw_total, ph_total, 18)
        pb = Image.new("RGB", (pw_total, ph_total), PRIMARY_L)
        if img.mode != "RGBA": img = img.convert("RGBA")
        img.paste(pb, (ppx, pill_y), pm)
        ImageDraw.Draw(img).text((ppx + 12, pill_y + 8), ptext, fill=PRIMARY, font=pf)
        ppx += pw_total + 14

# ------------- CTA 底部大按钮 -------------
foot_y = feat_y + fh + 80
cta_w = 520
cta_h = 96
cta_x = W // 2 - cta_w // 2
cta_y = foot_y

# 阴影
img = add_shadow(img, [cta_x - 8, cta_y - 8, cta_x + cta_w + 8, cta_y + cta_h + 8],
                 radius=24, softness=7, opacity=0.28, offs=(4, 8))
# 渐变主色按钮
btn = Image.new("RGB", (cta_w, cta_h), PRIMARY)
bd = ImageDraw.Draw(btn)
for i in range(cta_h):
    k = i / cta_h
    col = (int(PRIMARY[0] * (1 - k) + PRIMARY_H[0] * k),
           int(PRIMARY[1] * (1 - k) + PRIMARY_H[1] * k),
           int(PRIMARY[2] * (1 - k) + PRIMARY_H[2] * k))
    bd.line([(0, i), (cta_w, i)], fill=col, width=1)
bm = rrect_mask(cta_w, cta_h, 22)
br = Image.new("RGBA", (cta_w, cta_h), (0, 0, 0, 0))
br.paste(btn, (0, 0))
if img.mode != "RGBA": img = img.convert("RGBA")
img.paste(br, (cta_x, cta_y), bm)

# 文字
draw = ImageDraw.Draw(img)
cta_text = "下载 Blur Arc · 让照片回归秩序"
ctf = zh_sans(32, bold=True)
ctw_, _ = tw(draw, cta_text, ctf)
draw.text((cta_x + cta_w // 2 - ctw_ // 2, cta_y + cta_h // 2 - 32 // 2 - 8),
          cta_text, fill=(255, 255, 255), font=ctf)
small_t = "免费 · 开源 · MIT License"
stf = sans(18)
stw_, _ = tw(draw, small_t, stf)
draw.text((cta_x + cta_w // 2 - stw_ // 2, cta_y + cta_h // 2 + 20),
          small_t, fill=(224, 247, 250, 255), font=stf)
# 箭头
arrow_t = "→"
atf = sans(44, bold=True)
atw_, _ = tw(draw, arrow_t, atf)
draw.text((cta_x + cta_w - atw_ - 30, cta_y + cta_h // 2 - 44 // 2 - 4),
          arrow_t, fill=(255, 255, 255, 230), font=atf)

# ------------- 项目信息 -------------
info_y = cta_y + cta_h + 60
draw.text((margin, info_y), "Blur Arc", fill=TEXT_P, font=sans(32, bold=True))
draw.text((margin, info_y + 44),
          "本地运行 · 隐私零泄露 · 智能去重 · 按拍摄日期自动归档",
          fill=TEXT_S, font=zh_sans(20))
# GitHub
github_line = "github.com/BigAnnoy/BlurArc"
gfw, _ = tw(draw, github_line, mono(20))
draw.text((W - margin - gfw, info_y + 4), github_line,
          fill=PRIMARY, font=mono(20, bold=True))
# platform
plat = "Windows · macOS · Linux"
plw, _ = tw(draw, plat, mono(18))
draw.text((W - margin - plw, info_y + 44), plat, fill=TEXT_T, font=mono(18))

# 底部分隔线 + 版权
base_y = H - 40
draw.line([(margin, base_y - 10), (W - margin, base_y - 10)], fill=BORDER, width=1)
base_text = "© 2026 Blur Arc · 让照片回归秩序  ·  一份安静的本地归档工具"
btw_, _ = tw(draw, base_text, mono(16))
draw.text((W // 2 - btw_ // 2, base_y), base_text, fill=TEXT_T, font=mono(16))

# ============ 输出 ============
OUT_DIR.mkdir(parents=True, exist_ok=True)

png_path = OUT_DIR / "poster-v2.png"
img.save(str(png_path), "PNG", optimize=True)
print(f"\n✅ 海报 PNG: {png_path.name}  ({os.path.getsize(png_path)/1024:.0f} KB)")

jpg_path = OUT_DIR / "poster-v2.jpg"
img.convert("RGB").save(str(jpg_path), "JPEG", quality=92, optimize=True, progressive=True)
print(f"✅ 海报 JPG: {jpg_path.name}  ({os.path.getsize(jpg_path)/1024:.0f} KB)")

thumb = img.copy()
thumb.thumbnail((600, 900))
thumb_path = OUT_DIR / "poster-v2-thumb.png"
thumb.save(str(thumb_path), "PNG", optimize=True)
print(f"✅ 缩略图: {thumb_path.name}")

# 覆盖到 poster.png / poster.jpg (作为项目默认海报)
img.save(str(OUT_DIR / "poster.png"), "PNG", optimize=True)
img.convert("RGB").save(str(OUT_DIR / "poster.jpg"), "JPEG", quality=92, optimize=True, progressive=True)
print(f"✅ 已更新 docs/posters/poster.png 与 poster.jpg")
print(f"   画布尺寸: {W} x {H}")
