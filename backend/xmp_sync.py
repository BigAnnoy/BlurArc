"""
XMP 元数据同步模块
实现照片描述字段的双向同步（XMP ↔ DB）
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 尝试导入 XMP 库
try:
    from libxmp import XMPFiles, XMPMeta, XMPConst
    XMP_AVAILABLE = True
except ImportError:
    try:
        import pyexiv2
        XMP_AVAILABLE = True
    except ImportError:
        XMP_AVAILABLE = False
        logger.warning("XMP 库不可用，将仅使用 DB 存储描述")


class XMPSyncError(Exception):
    """XMP 同步错误"""
    pass


def read_xmp_description(photo_path: str) -> Optional[str]:
    """
    从照片 XMP 元数据读取描述
    
    Args:
        photo_path: 照片文件路径
        
    Returns:
        描述文本，如果不存在或读取失败则返回 None
    """
    if not XMP_AVAILABLE:
        return None
    
    try:
        path = Path(photo_path)
        if not path.exists():
            logger.warning(f"照片文件不存在: {photo_path}")
            return None
        
        # 使用 libxmp
        if 'libxmp' in globals():
            xmp_file = XMPFiles(file_path=str(path), open_forupdate=False)
            xmp = xmp_file.get_xmp()
            if xmp:
                desc = xmp.get_property(XMPConst.NS_DC, 'description')
                xmp_file.close_file()
                return desc if desc else None
        
        # 使用 pyexiv2
        elif 'pyexiv2' in globals():
            metadata = pyexiv2.ImageMetadata(str(path))
            metadata.read()
            desc = metadata.get('Xmp.dc.description')
            return desc.value if desc else None
    
    except Exception as e:
        logger.error(f"读取 XMP 描述失败: {photo_path}, 错误: {e}")
    
    return None


def write_xmp_description(photo_path: str, description: str) -> Tuple[bool, str]:
    """
    将描述写入照片 XMP 元数据
    
    Args:
        photo_path: 照片文件路径
        description: 要写入的描述文本
        
    Returns:
        (success, message): 是否成功，以及结果消息
    """
    if not XMP_AVAILABLE:
        return False, "XMP 库不可用，仅保存到数据库"
    
    try:
        path = Path(photo_path)
        if not path.exists():
            return False, f"照片文件不存在: {photo_path}"
        
        # 检查文件是否可写
        if not path.stat().st_mode & 0o200:
            return False, "原图为只读，仅保存到数据库"
        
        # 使用 libxmp
        if 'libxmp' in globals():
            xmp_file = XMPFiles(file_path=str(path), open_forupdate=True)
            xmp = xmp_file.get_xmp()
            if xmp is None:
                xmp = XMPMeta()
            
            # 写入描述
            if description:
                xmp.set_property(XMPConst.NS_DC, 'description', description)
            else:
                # 如果描述为空，删除该属性
                xmp.delete_property(XMPConst.NS_DC, 'description')
            
            # 保存
            xmp_file.put_xmp(xmp)
            xmp_file.close_file()
            return True, "已同步到 XMP 和数据库"
        
        # 使用 pyexiv2
        elif 'pyexiv2' in globals():
            metadata = pyexiv2.ImageMetadata(str(path))
            metadata.read()
            
            if description:
                metadata['Xmp.dc.description'] = description
            else:
                del metadata['Xmp.dc.description']
            
            metadata.write()
            return True, "已同步到 XMP 和数据库"
    
    except PermissionError:
        return False, "原图为只读，仅保存到数据库"
    except Exception as e:
        logger.error(f"写入 XMP 描述失败: {photo_path}, 错误: {e}")
        return False, f"写入 XMP 失败: {str(e)}，仅保存到数据库"


def read_xmp_title(photo_path: str) -> Optional[str]:
    """
    从照片 XMP 元数据读取标题
    
    Args:
        photo_path: 照片文件路径
        
    Returns:
        标题文本，如果不存在或读取失败则返回 None
    """
    if not XMP_AVAILABLE:
        return None
    
    try:
        path = Path(photo_path)
        if not path.exists():
            return None
        
        # 使用 libxmp
        if 'libxmp' in globals():
            xmp_file = XMPFiles(file_path=str(path), open_forupdate=False)
            xmp = xmp_file.get_xmp()
            if xmp:
                title = xmp.get_property(XMPConst.NS_DC, 'title')
                xmp_file.close_file()
                return title if title else None
        
        # 使用 pyexiv2
        elif 'pyexiv2' in globals():
            metadata = pyexiv2.ImageMetadata(str(path))
            metadata.read()
            title = metadata.get('Xmp.dc.title')
            return title.value if title else None
    
    except Exception as e:
        logger.error(f"读取 XMP 标题失败: {photo_path}, 错误: {e}")
    
    return None


def write_xmp_title(photo_path: str, title: str) -> Tuple[bool, str]:
    """
    将标题写入照片 XMP 元数据
    
    Args:
        photo_path: 照片文件路径
        title: 要写入的标题文本
        
    Returns:
        (success, message): 是否成功，以及结果消息
    """
    if not XMP_AVAILABLE:
        return False, "XMP 库不可用，仅保存到数据库"
    
    try:
        path = Path(photo_path)
        if not path.exists():
            return False, f"照片文件不存在: {photo_path}"
        
        # 检查文件是否可写
        if not path.stat().st_mode & 0o200:
            return False, "原图为只读，仅保存到数据库"
        
        # 使用 libxmp
        if 'libxmp' in globals():
            xmp_file = XMPFiles(file_path=str(path), open_forupdate=True)
            xmp = xmp_file.get_xmp()
            if xmp is None:
                xmp = XMPMeta()
            
            # 写入标题
            if title:
                xmp.set_property(XMPConst.NS_DC, 'title', title)
            else:
                xmp.delete_property(XMPConst.NS_DC, 'title')
            
            # 保存
            xmp_file.put_xmp(xmp)
            xmp_file.close_file()
            return True, "已同步到 XMP 和数据库"
        
        # 使用 pyexiv2
        elif 'pyexiv2' in globals():
            metadata = pyexiv2.ImageMetadata(str(path))
            metadata.read()
            
            if title:
                metadata['Xmp.dc.title'] = title
            else:
                del metadata['Xmp.dc.title']
            
            metadata.write()
            return True, "已同步到 XMP 和数据库"
    
    except PermissionError:
        return False, "原图为只读，仅保存到数据库"
    except Exception as e:
        logger.error(f"写入 XMP 标题失败: {photo_path}, 错误: {e}")
        return False, f"写入 XMP 失败: {str(e)}，仅保存到数据库"
