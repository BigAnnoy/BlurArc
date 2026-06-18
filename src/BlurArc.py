"""
Blur Arc - PyWebView 应用主程序

将 Flask API 服务器和 PyWebView 窗口集成在一起
"""

import sys
import os
import time
import threading
import logging
import urllib.parse
from pathlib import Path
from subprocess import Popen, DEVNULL

# 可选导入 PyWebView
try:
    import webview
    webview_available = True
except ImportError:
    webview = None
    webview_available = False

# ─── 路径适配：兼容 PyInstaller 打包和直接运行两种模式 ───────────
if getattr(sys, 'frozen', False):
    # 打包后：所有资源在 sys._MEIPASS 目录下
    _MEIPASS = getattr(sys, '_MEIPASS', None)
    if _MEIPASS:
        _BASE = Path(_MEIPASS)
    else:
        # 降级方案：使用可执行文件所在目录
        _BASE = Path(sys.executable).parent
else:
    # 直接运行：资源在项目根目录
    _BASE = Path(__file__).parent.parent

# 项目根目录（用于用户数据，如 .config/）
# 打包后可执行文件旁边的目录作为数据根目录
if getattr(sys, 'frozen', False):
    project_root = Path(sys.executable).parent
else:
    project_root = Path(__file__).parent.parent

backend_dir = _BASE / 'backend'
frontend_dir = _BASE / 'frontend'

# 添加 _BASE 到 Python 路径，这样可以正确导入 backend 包
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

# 创建日志过滤器 - 忽略 PyWebView 的序列化错误
class PyWebViewErrorFilter(logging.Filter):
    """过滤 PyWebView 的路径序列化错误
    
    屏蔽所有关于 WindowsPath 对象属性的错误，这些是无害的，只是 PyWebView
    试图序列化 pathlib.Path 对象时的内省尝试。
    """
    def filter(self, record):
        msg = record.getMessage()
        # 忽略所有 Path 对象序列化错误（_hash, _drv, _root 等）
        if "'WindowsPath' object has no attribute" in msg:
            return False
        if "Error while processing" in msg and "._" in msg:
            return False
        return True

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 添加过滤器到所有日志处理器
for handler in logging.root.handlers:
    handler.addFilter(PyWebViewErrorFilter())

# 也为 pywebview 日志添加过滤器
webview_logger = logging.getLogger('pywebview')
webview_logger.addFilter(PyWebViewErrorFilter())

class AlbumAppAPI:
    """暴露给前端的 Python API"""
    
    def __init__(self):
        self.config = None
        self.import_thread = None
        self._load_config()
    
    # 移除 __getstate__ 方法，让 PyWebView 能够正确序列化对象方法
    
    def _load_config(self):
        """加载配置"""
        try:
            from backend.config_manager import ConfigManager
            self.config = ConfigManager()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
    
    def get_config(self):
        """获取配置信息"""
        if not self.config:
            return {'error': '配置管理器未初始化'}
        
        try:
            all_config = self.config.get_all_config()
            return {
                'album_path': self.config.get_album_path(),
                'created_at': all_config.get('created_at'),
                'last_import': self.config.get_last_import(),
                'is_first_run': self.config.is_first_run()
            }
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return {'error': str(e)}
    
    def select_album_path(self):
        """选择相册路径（通过文件对话框）"""
        try:
            logger.info("前端请求选择相册路径")
            # 调用 select_folder() 让用户选择文件夹
            path = self.select_folder()
            if path:
                logger.info(f"用户选择的相册路径: {path}")
                return {'path': path}
            else:
                logger.info("用户取消了文件夹选择")
                return {'path': None}
        except Exception as e:
            logger.error(f"文件对话框错误: {e}")
            return {'error': str(e)}
    
    def get_system_info(self):
        """获取系统信息"""
        try:
            import platform
            return {
                'platform': platform.system(),
                'python_version': platform.python_version(),
                'processor': platform.processor()
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {'error': str(e)}
    
    def open_import_dialog(self):
        """打开导入对话框"""
        try:
            logger.info("前端请求打开导入对话框")
            return {'status': 'ok'}
        except Exception as e:
            logger.error(f"打开导入对话框失败: {e}")
            return {'error': str(e)}
    
    def select_folder(self):
        """选择文件夹 - 供前端调用"""
        logger.info("select_folder called")
        try:
            # 使用tkinter的文件夹选择器，它提供了更好的用户体验和可调整大小的界面
            import tkinter as tk
            from tkinter import filedialog
            from pathlib import Path
            
            # 创建一个隐藏的Tk根窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            root.attributes('-topmost', True)  # 确保对话框在最前面
            
            try:
                # 显示文件夹选择对话框
                # BUG-038：将 root.destroy() 移入 finally，确保无论如何都能清理 Tk 窗口
                path = filedialog.askdirectory(
                    title="选择文件夹",
                    initialdir=str(Path.home() / "Pictures")
                )
            finally:
                root.destroy()  # 确保 Tk 根窗口始终被销毁，不留残留
            
            if path:
                logger.info(f"Selected: {path}")
                return path
            else:
                logger.info("User cancelled")
                return None
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    def send_toast(self, title: str, message: str):
        """发送 Windows 桌面通知（Toast）- 供前端调用
        
        导入完成后在系统托盘区弹出原生通知，告知用户导入结果。
        若 win10toast 未安装或非 Windows 平台，静默降级不报错。
        """
        import sys
        import threading
        
        def _show():
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    title=title,
                    msg=message,
                    duration=5,
                    threaded=True,
                )
            except ImportError:
                # win10toast 未安装，降级：仅记录日志
                logger.info(f"[Toast] {title}: {message}")
            except Exception as e:
                logger.warning(f"桌面通知发送失败: {e}")
        
        if sys.platform == 'win32':
            threading.Thread(target=_show, daemon=True).start()
        
        return {'status': 'ok'}

    def open_file(self, file_path):
        """打开文件 - 供前端调用"""
        logger.info(f"open_file called with path: {file_path}")
        try:
            import os
            import platform
            import subprocess
            
            if platform.system() == 'Windows':
                # Windows 系统使用 os.startfile（天然安全，不经过 shell）
                os.startfile(file_path)
                logger.info(f"Successfully opened file: {file_path}")
                return {'success': True, 'message': '文件已打开'}
            elif platform.system() == 'Darwin':
                # macOS：使用参数列表形式，避免 shell 注入
                subprocess.run(['open', file_path], check=False)
                logger.info(f"Successfully opened file: {file_path}")
                return {'success': True, 'message': '文件已打开'}
            else:
                # Linux：使用参数列表形式，避免 shell 注入
                subprocess.run(['xdg-open', file_path], check=False)
                logger.info(f"Successfully opened file: {file_path}")
                return {'success': True, 'message': '文件已打开'}
                
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            return {'success': False, 'error': str(e)}

def start_flask_server():
    """在线程中启动 Flask 服务器"""
    try:
        logger.info("🔄 Flask 服务器：正在启动...")
        
        # 等待一下，确保主线程已准备好
        time.sleep(0.5)
        
        # 导入并运行 Flask 应用
        logger.info("📦 Flask 服务器：导入应用模块...")
        from backend.api_server import app
        logger.info("✅ Flask 服务器：应用模块导入成功")
        
        logger.info("🚀 Flask 服务器：启动服务，监听 127.0.0.1:5000")
        logger.info("📝 后端 API 文档:")
        logger.info("  - 健康检查: GET http://127.0.0.1:5000/api/health")
        logger.info("  - 相册统计: GET http://127.0.0.1:5000/api/album/stats")
        logger.info("  - 目录树: GET http://127.0.0.1:5000/api/album/tree")
        
        # 在线程中运行（不会阻塞 PyWebView）
        # threaded=True 提升并发处理能力，避免多请求时单线程阻塞
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except OSError as e:
        # BUG-036：端口被占用（errno 10048 on Windows / 98 on Linux）时给出明确提示
        if 'Address already in use' in str(e) or getattr(e, 'errno', 0) in (98, 10048):
            logger.error(f"❌ Flask 服务器：端口 5000 已被占用！请关闭占用该端口的程序后重试。({e})")
        else:
            logger.error(f"❌ Flask 服务器：网络错误: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"❌ Flask 服务器：启动失败: {e}", exc_info=True)

def main():
    """主程序"""
    logger.info("=" * 60)
    logger.info("Blur Arc - PyWebView 版本")
    logger.info("=" * 60)
    
    # 初始化数据库（创建表结构、执行迁移）
    try:
        from backend.database import init_db
        init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
    
    # 启动 Flask 服务器（后台线程）
    flask_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_thread.start()
    
    # 等待 Flask 服务器启动（端口探测，最多 30 秒，低端机或首次解压时需要更长时间）
    logger.info("⏳ 等待 Flask 服务器启动...")
    import socket
    _deadline = time.time() + 30  # 延长到 30s，避免 PyInstaller 首次解压启动过慢
    flask_ready = False
    while time.time() < _deadline:
        try:
            with socket.create_connection(('127.0.0.1', 5000), timeout=0.5):
                flask_ready = True
                break
        except OSError:
            time.sleep(0.2)
    
    # 构建本地等待页面（Flask 未就绪时显示）
    # 此页面不依赖 Flask，独立运行，轮询 /api/health 成功后自动跳转
    _waiting_page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blur Arc - 启动中</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #1f1f1f;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    text-align: center;
  }}
  h2 {{ margin-bottom: 16px; font-weight: 400; font-size: 20px; }}
  .spinner {{
    width: 40px; height: 40px;
    border: 3px solid #3a3a3a;
    border-top-color: #4a9eff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 20px;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .status {{ font-size: 13px; color: #888; margin-top: 8px; }}
  .retry-count {{ color: #4a9eff; }}
</style>
</head>
<body>
  <div class="spinner"></div>
  <h2>正在启动服务<span id="dots"></span></h2>
  <p class="status">请稍候… (<span class="retry-count" id="retries">0</span>/20)</p>
  <script>
(function() {{
  var dots = 0, retries = 0, maxRetries = 20;
  var dotsEl = document.getElementById('dots');
  var retriesEl = document.getElementById('retries');
  
  // 动态省略号动画
  setInterval(function() {{
    dots = (dots + 1) % 4;
    dotsEl.textContent = '.'.repeat(dots);
  }}, 500);
  
  function checkBackend() {{
    if (retries >= maxRetries) {{
      document.querySelector('.status').innerHTML = '服务启动超时，请检查日志或重启应用';
      document.querySelector('.status').style.color = '#e07070';
      return;
    }}
    retries++;
    retriesEl.textContent = retries;
    fetch('http://127.0.0.1:5000/api/health')
      .then(function(r) {{ return r.ok ? r.json() : Promise.reject(); }})
      .then(function() {{
        window.location.replace('http://127.0.0.1:5000');
      }})
      .catch(function() {{
        setTimeout(checkBackend, 1500);
      }});
  }}
  checkBackend();
}})();
  </script>
</body>
</html>"""
    
    # BUG-036：端口探测失败时的处理
    if not flask_ready:
        logger.warning("⚠ Flask 服务器 30 秒内未就绪，加载本地等待页面...")
        logger.warning("   等待页面将自动轮询服务状态，请留意应用日志中的错误信息")
        # 使用本地等待页面作为 URL（不依赖 Flask）
        _load_url = f"data:text/html;charset=utf-8,{urllib.parse.quote(_waiting_page)}"
    else:
        logger.info("✅ Flask 服务器已就绪，地址: http://127.0.0.1:5000")
        _load_url = 'http://127.0.0.1:5000'
    
    # 创建 PyWebView 窗口
    try:
        logger.info("🔧 初始化 AlbumAppAPI...")
        api = AlbumAppAPI()
        logger.info("✅ AlbumAppAPI 初始化完成")
        
        # 关键修复：使用 Flask 服务前端（而不是直接加载本地文件）
        # 这样 PyWebView 能正确注入 API 对象
        logger.info("🪟 创建 PyWebView 窗口...")
        window = webview.create_window(
            title='Blur Arc v0.5.1',
            url=_load_url,  # Flask 就绪则直接加载；未就绪则显示本地等待页面
            width=1400,
            height=900,
            resizable=True,
            background_color='#1f1f1f',  # 与暗色主题背景一致，防止切换时闪白
            js_api=api,
            maximized=True  # 默认最大化窗口
        )
        
        logger.info("✅ PyWebView 窗口已创建")
        logger.info("🚀 启动 PyWebView 主循环...")
        logger.info("📝 按 F12 打开浏览器开发者工具查看详细日志")
        webview.start(debug=False)  # 禁用开发者工具
        
    except Exception as e:
        logger.error(f"❌ PyWebView 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
