import cairosvg

src = r'F:\AI\Frame_Album\blurarc_app\assets\logo\blur_arc_logo_light.svg'
dst = r'F:\AI\Frame_Album\blurarc_app\assets\logo\icon_512_light.png'

# 将 SVG 渲染为 512x512 PNG，保持透明背景
cairosvg.svg2png(url=src, write_to=dst, output_width=512, output_height=512)
print(f'Saved {dst} (512x512)')
