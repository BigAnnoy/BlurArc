import re

print('=== 验证HTML中的logo嵌入 ===')
print()

files = [
    'mobile/mobile-app-v3-dark.html',
    'mobile/mobile-app-v3-light.html',
    'tablet/tablet-app-v3-dark.html',
    'tablet/tablet-app-v3-light.html',
]

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有base64嵌入的logo
        has_base64 = 'data:image/png;base64,' in content
        
        # 检查是否还有文件路径引用
        has_file_ref = '../img/logo_' in content
        
        filename = filepath.split('/')[-1]
        
        if has_base64:
            # 统计base64长度
            b64_matches = re.findall(r'data:image/png;base64,([^"]+)', content)
            if b64_matches:
                b64_len = len(b64_matches[0])
                print(f'✅ {filename}: base64 embedded, {b64_len} chars')
            else:
                print(f'⚠️  {filename}: has base64 marker but no data')
        elif has_file_ref:
            print(f'⚠️  {filename}: still has file reference (not base64)')
        else:
            print(f'❌ {filename}: no logo found at all')
        
    except FileNotFoundError:
        print(f'❌ {filepath}: file not found')

print()
print('=== 检查mobile dark的实际内容 ===')
with open('mobile/mobile-app-v3-dark.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找第一个img标签
img_match = re.search(r'<img[^>]+>', content)
if img_match:
    img_tag = img_match.group(0)
    print(f'First img tag in mobile dark:')
    if len(img_tag) > 200:
        print(f'  {img_tag[:200]}...')
    else:
        print(f'  {img_tag}')

print()
print('完成！如果验证通过，请刷新浏览器预览。')
