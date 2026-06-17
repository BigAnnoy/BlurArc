"""
诊断脚本：检查配置管理器和相册路径状态
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config_manager import ConfigManager

print("=" * 60)
print("配置诊断工具")
print("=" * 60)

config = ConfigManager()

print(f"\n1. 配置文件路径: {config.CONFIG_FILE}")
print(f"2. 配置文件存在: {config.CONFIG_FILE.exists()}")

album_path = config.get_album_path()
print(f"\n3. 当前相册路径: {album_path}")

if album_path:
    path_obj = Path(album_path)
    print(f"4. 路径是否存在: {path_obj.exists()}")
    print(f"5. 是否为目录: {path_obj.is_dir()}")
    print(f"6. 绝对路径: {path_obj.absolute()}")
else:
    print("4. ⚠️ 相册路径为 None")

print(f"\n7. 是否首次运行: {config.is_first_run()}")
print(f"\n8. 完整配置:")
import json
print(json.dumps(config.get_all_config(), indent=2, ensure_ascii=False))

print("\n" + "=" * 60)
if album_path:
    print("✅ 配置正常，相册路径有效")
else:
    print("❌ 配置异常，相册路径未设置或无效")
print("=" * 60)
