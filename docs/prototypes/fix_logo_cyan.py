import base64
from PIL import Image
import os
import re

print('=== 用青色重新生成暗色主题的logo ===')
print()

# 1. 读取原始icon
icon_path = '../icon.ico'
if not os.path.exists(icon_path):
    icon_path = '../../icon.ico'
if not os.path.exists(icon_path):
    print('ERROR: icon.ico not found!')
    exit(1)

img = Image.open(icon_path)
img.load()
img.seek(0)  # 取最大尺寸帧
img_rgba = img.convert('RGBA')
w, h = img_rgba.size

print(f'Original icon size: {w}x{h}')

# 2. 生成logo
os.makedirs('img', exist_ok=True)

# 亮色主题用：深色logo（原始颜色）
img_rgba.resize((28, 28), Image.LANCZOS).save('img/logo_dark_28.png')
img_rgba.resize((32, 32), Image.LANCZOS).save('img/logo_dark_32.png')
print('✅ Saved logo_dark (dark color for light theme)')

# 暗色主题用：青色logo（而不是白色）
cyan_logo_28 = Image.new('RGBA', (28, 28), (0,0,0,0))
cyan_logo_32 = Image.new('RGBA', (32, 32), (0,0,0,0))

img_28 = img_rgba.resize((28, 28), Image.LANCZOS)
img_32 = img_rgba.resize((32, 32), Image.LANCZOS)

for x in range(28):
    for y in range(28):
        r, g, b, a = img_28.getpixel((x, y))
        if a > 10:
            # 用青色 (34, 211, 238) 代替白色
            cyan_logo_28.putpixel((x, y), (34, 211, 238, a))

for x in range(32):
    for y in range(32):
        r, g, b, a = img_32.getpixel((x, y))
        if a > 10:
            cyan_logo_32.putpixel((x, y), (34, 211, 238, a))

cyan_logo_28.save('img/logo_cyan_28.png')
cyan_logo_32.save('img/logo_cyan_32.png')
print('✅ Saved logo_cyan (cyan color #22d3ee for dark theme)')

# 3. 转换为base64
def img_to_base64(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

logos = {
    'dark_28': img_to_base64('img/logo_dark_28.png'),
    'cyan_28': img_to_base64('img/logo_cyan_28.png'),
    'dark_32': img_to_base64('img/logo_dark_32.png'),
    'cyan_32': img_to_base64('img/logo_cyan_32.png'),
}

print(f'\nLogo base64 lengths:')
for key, value in logos.items():
    print(f'  {key}: {len(value)} chars')

# 4. 更新所有8个HTML文件
files = {
    # 暗色主题 → 青色logo
    'mobile/mobile-app-v3-dark.html': ('cyan_28', '28x28'),
    'mobile/mobile-app-connect-dark.html': ('cyan_28', '28x28'),
    'tablet/tablet-app-v3-dark.html': ('cyan_32', '32x32'),
    'tablet/tablet-app-connect-dark.html': ('cyan_32', '32x32'),
    # 亮色主题 → 深色logo
    'mobile/mobile-app-v3-light.html': ('dark_28', '28x28'),
    'mobile/mobile-app-connect-light.html': ('dark_28', '28x28'),
    'tablet/tablet-app-v3-light.html': ('dark_32', '32x32'),
    'tablet/tablet-app-connect-light.html': ('dark_32', '32x32'),
}

print(f'\n=== 更新HTML文件 ===')

for filepath, (logo_key, size) in files.items():
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logo_b64 = logos[logo_key]
        
        # 直接替换所有包含base64的img标签
        # 找到所有img标签
        imgs = re.findall(r'<img[^>]+>', content)
        
        new_imgs = []
        for img in imgs:
            if 'base64,' in img or '../img/logo_' in img:
                # 这是logo img，需要替换
                # 提取style属性
                style_match = re.search(r'style="[^"]*"', img)
                style = style_match.group(0) if style_match else ''
                
                new_img = f'<img src="data:image/png;base64,{logo_b64}" {style} />'
                new_imgs.append((img, new_img))
        
        # 执行替换
        new_content = content
        for old_img, new_img in new_imgs:
            new_content = new_content.replace(old_img, new_img)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'✅ {filepath.split("/")[-1]}: updated with {logo_key} logo')
        else:
            print(f'⚠️  {filepath.split("/")[-1]}: no logo img found to replace')
            
    except FileNotFoundError:
        print(f'❌ {filepath}: file not found')

print(f'\n=== 验证结果 ===')

# 验证所有文件
for filepath in files.keys():
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有base64嵌入的logo
        has_base64 = 'data:image/png;base64,' in content
        
        # 检查是否还有文件路径引用
        has_file_ref = '../img/logo_' in content
        
        filename = filepath.split('/')[-1]
        
        if has_base64 and not has_file_ref:
            print(f'✅ {filename}: base64 embedded correctly')
        elif has_file_ref:
            print(f'⚠️  {filename}: still has file reference')
        else:
            print(f'❌ {filename}: no logo found')
            
    except FileNotFoundError:
        print(f'❌ {filepath}: file not found')

print(f'\n完成！暗色主题现在使用青色logo (#22d3ee)，应该能清晰显示了。')
print(f'请刷新浏览器预览。')
