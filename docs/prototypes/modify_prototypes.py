#!/usr/bin/env python3
"""修改4个原型文件，满足用户需求：
1. 手机版：移除状态栏的logo，标题栏只显示logo+Blur Arc
2. 平板版：移除状态栏的logo，在内容区顶部添加标题栏
3. Logo支持亮色/暗色模式（通过CSS filter）
"""
import re, os

BASE = r"F:\AI\Frame_Album\docs\prototypes"

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def get_logo_b64(html):
    """从HTML中提取logo的base64数据"""
    # 找第一个data:image/png;base64,的img标签
    m = re.search(r'<img src="data:image/png;base64,([^"]+)"', html)
    if m:
        return m.group(1)
    return None

# ========== 手机版修改 ==========
def modify_mobile(html, is_dark):
    """
    修改手机版原型：
    1. 移除状态栏的logo
    2. 标题栏只显示logo + "Blur Arc"，不显示tab名称
    """
    # 1. 移除状态栏的img标签
    # 状态栏格式：<div class="status-bar"> ... <img src="data:..."> ... </div>
    # 找到status-bar里的img并移除
    html = re.sub(
        r'(<div class="status-bar">.*?)(<img src="data:image/png;base64,[^"]*"[^>]*>)(.*?</div>)',
        r'\1\3',
        html,
        flags=re.DOTALL
    )
    
    # 2. 修改标题栏：只保留logo + Blur Arc
    # 找到app-bar，在里面添加文字
    # 当前格式：<div class="app-bar"><img ...></div>
    # 目标格式：<div class="app-bar"><img ...><span>Blur Arc</span></div>
    
    def replace_app_bar(m):
        img_tag = m.group(1)  # 整个img标签
        return f'<div class="app-bar">{img_tag}<span style="margin-left:10px;font-size:17px;font-weight:600;letter-spacing:0.3px;">Blur Arc</span></div>'
    
    html = re.sub(
        r'<div class="app-bar">(<img[^>]+>)\s*</div>',
        replace_app_bar,
        html
    )
    
    # 3. 移除JavaScript里的tab名称切换逻辑
    # 删除：const titles = { album:'Blur Arc 相册', ... }; document.getElementById('appBarTitle')...
    html = re.sub(
        r"const titles = \{[^}]+\};\s*document\.getElementById\('appBarTitle'\)\.textContent = titles\[tab\];",
        "",
        html
    )
    
    # 4. 在CSS里为app-bar的img添加样式（适配亮色/暗色）
    # 添加CSS：app-bar img { height: 28px; width: auto; }
    # 对于暗色主题，logo是青色，可见
    # 对于亮色主题，需要让logo颜色适配
    
    if not is_dark:
        # 亮色主题：添加CSS让logo变成深色
        # 在</style>前添加
        css_addition = """
    .app-bar img { height: 28px; width: auto; filter: brightness(0) saturate(100%); }
"""
        html = html.replace('</style>', css_addition + '  </style>')
    else:
        # 暗色主题：logo保持原色（青色）
        css_addition = """
    .app-bar img { height: 28px; width: auto; }
"""
        html = html.replace('</style>', css_addition + '  </style>')
    
    return html

# ========== 平板版修改 ==========
def modify_tablet(html, is_dark):
    """
    修改平板版原型：
    1. 移除状态栏的logo
    2. 在main-area顶部添加标题栏（logo + Blur Arc）
    """
    # 1. 移除状态栏的img标签
    html = re.sub(
        r'(<div class="status-bar">.*?)(<img src="data:image/png;base64,[^"]*"[^>]*>)(.*?</div>)',
        r'\1\3',
        html,
        flags=re.DOTALL
    )
    
    # 2. 在main-area里添加标题栏
    # main-area的结构：
    # <div class="main-area">
    #   <!-- Album content --> or other content
    # 
    # 我们需要在main-area的开头添加一个app-bar标题栏
    
    # 先提取logo的base64
    logo_b64 = get_logo_b64(html)
    
    if logo_b64:
        # 创建标题栏HTML
        # 注意：平板版有相册/上传/设置三个tab，标题栏应该只在相册tab显示
        # 但是用户说"加个标题栏，标题栏里放logo和blur Arc"
        # 我理解是：在main-area顶部常驻显示标题栏
        
        title_bar = f'''
      <div class="main-app-bar" style="height:52px;display:flex;align-items:center;justify-content:center;gap:10px;border-bottom:0.5px solid var(--border);flex-shrink:0;background:var(--bg-card);">
        <img src="data:image/png;base64,{logo_b64[:100]}" style="height:28px;width:auto;{'filter:brightness(0) saturate(100%);' if not is_dark else ''}">
        <span style="font-size:17px;font-weight:600;letter-spacing:0.3px;color:var(--text-primary);">Blur Arc</span>
      </div>'''
        
        # 将标题栏插入到main-area的开头
        # 找到 <div class="main-area"> 后面的内容
        html = re.sub(
            r'(<div class="main-area">)',
            r'\1' + title_bar,
            html
        )
    
    return html

# ========== 主程序 ==========
files = [
    ("mobile/mobile-app-v3-dark.html", True),
    ("mobile/mobile-app-v3-light.html", False),
    ("tablet/tablet-app-v3-dark.html", True),
    ("tablet/tablet-app-v3-light.html", False),
]

for fname, is_dark in files:
    path = os.path.join(BASE, fname)
    print(f"Processing: {fname}")
    
    html = read_file(path)
    
    if "mobile" in fname:
        new_html = modify_mobile(html, is_dark)
    else:
        new_html = modify_tablet(html, is_dark)
    
    write_file(path, new_html)
    print(f"  Done: {fname}")

print("\nAll done!")
