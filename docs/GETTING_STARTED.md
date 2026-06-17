# 🚀 快速开始指南

## 准备工作

### 1. 安装 Python 依赖

在项目根目录打开命令行，运行：

```bash
pip install -r config/requirements.txt
```

> 💡 如果下载速度太慢，可以使用国内镜像：
> ```bash
> pip install -r config/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
> ```

### 2. 验证依赖安装

```bash
python check_deps.py
```

如果所有依赖都正确安装，会显示：
```
✓ Flask
✓ Flask-CORS
✓ PyWebView
✓ Pillow
✓ python-dateutil

✓ 所有依赖都已正确安装!
```

## 启动应用

### 📌 推荐方式（4 选 1）

#### 方式 1️⃣：从项目根目录启动（最直接）

```bash
cd c:\Users\IT20240802\Desktop\照片整理
python src\BlurArc.py
```

#### 方式 2️⃣：双击启动脚本（最方便）

在项目根目录中找到 `启动相册.bat`，双击运行。

或从命令行：
```bash
启动相册.bat
```

#### 方式 3️⃣：使用 Python 启动脚本

```bash
python 启动相册.py
```

#### 方式 4️⃣：从 scripts 文件夹启动

```bash
scripts\启动BlurArc.bat
```

## 故障排除

### 问题 1: Python 找不到模块

```
ModuleNotFoundError: No module named 'flask'
```

**解决方案**：安装依赖
```bash
pip install -r config/requirements.txt
```

### 问题 2: 端口被占用

```
Address already in use
```

**原因**：应用使用 5000 端口，可能被其他程序占用

**解决方案**：
- 关闭其他使用 5000 端口的应用
- 或在代码中修改端口（编辑 `backend/api_server.py`）

### 问题 3: 找不到应用文件

```
can't open file 'BlurArc.py': [Errno 2] No such file or directory
```

**原因**：从错误的目录启动

**解决方案**：确保在项目根目录启动，或使用上面推荐的方式

### 问题 4: 防火墙阻止

应用需要在本地使用 5000 端口，如果防火墙阻止了，需要允许。

## 项目结构

```
照片整理/
├── src/BlurArc.py      <- 应用主文件
├── 启动相册.bat             <- 推荐启动脚本
├── 启动相册.py              <- Python 启动脚本
├── scripts/                 <- 其他启动脚本
├── config/requirements.txt  <- 依赖列表
└── docs/                    <- 详细文档
```

## 应用功能

启动后，应用将：

1. ✅ 检查配置（首次启动会提示设置相册路径）
2. ✅ 启动 Flask API 服务器（端口 5000）
3. ✅ 打开 PyWebView 窗口
4. ✅ 显示 Blur Arc 界面

## 常用操作

- **浏览相册**：左侧目录树，点击查看照片
- **导入照片**：点击"导入"按钮，选择照片源
- **修改设置**：点击右上角齿轮图标
- **全屏预览**：点击照片卡片

## 更多帮助

查看详细文档：

- `docs/QUICK_REFERENCE.md` - 快速参考
- `docs/PROJECT_SUMMARY.md` - 项目总结
- `docs/PHASE5_WEBVIEW_COMPLETE.md` - 完整指南

---

**版本**: v0.5.0 PyWebView  
**更新时间**: 2026-03-23  
**状态**: ✅ 生产级
