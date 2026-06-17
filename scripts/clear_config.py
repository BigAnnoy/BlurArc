#!/usr/bin/env python3
"""
清除相册配置脚本

此脚本用于清除 Blur Arc 应用的所有配置信息，包括：
- 相册路径设置
- 导入历史
- 应用设置

执行此脚本后，应用将恢复到首次启动状态，需要重新选择相册路径。
"""

import os
import sys
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_config_paths():
    """
    获取配置文件和目录的路径
    """
    # 脚本位于scripts目录，需要向上两级到达项目根目录
    project_root = Path(__file__).parent.parent
    config_dir = project_root / ".config"
    config_file = config_dir / "config.json"
    return config_dir, config_file


def clear_config():
    """
    清除配置文件和目录
    """
    config_dir, config_file = get_config_paths()
    
    logger.info("📋 正在检查配置文件...")
    
    # 检查配置文件是否存在
    if not config_file.exists():
        logger.info("✅ 配置文件不存在，无需清除")
        return True
    
    try:
        # 删除配置文件
        config_file.unlink()
        logger.info(f"🗑️  已删除配置文件: {config_file}")
        
        # 如果配置目录为空，则删除配置目录
        if config_dir.exists() and not any(config_dir.iterdir()):
            config_dir.rmdir()
            logger.info(f"🗑️  已删除空配置目录: {config_dir}")
        
        logger.info("✅ 配置已成功清除")
        logger.info("📝 下次启动应用时，需要重新选择相册路径")
        return True
        
    except Exception as e:
        logger.error(f"❌ 清除配置失败: {e}")
        return False


def main():
    """
    主函数
    """
    logger.info("=" * 60)
    logger.info("📸 Blur Arc - 清除配置脚本")
    logger.info("=" * 60)
    
    # 提示用户确认
    confirm = input("⚠️  此操作将清除所有配置信息，确定要继续吗？(y/N): ")
    if confirm.lower() != 'y':
        logger.info("🚫 操作已取消")
        return 0
    
    # 执行清除操作
    if clear_config():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
