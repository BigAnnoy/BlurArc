# 📦 依赖安装指南

## 快速安装

在项目根目录运行以下命令：

```bash
pip install -r config/requirements.txt
```

## 依赖列表

| 包名 | 版本 | 说明 |
|------|------|------|
| Flask | 2.3.0 | Web 框架 |
| Flask-CORS | 4.0.0 | 跨域资源共享 |
| PyWebView | 6.1 | Web 视图框架 |
| Pillow | 10.0.0 | 图像处理库 |
| python-dateutil | 2.8.2 | 日期时间工具 |

## 验证安装

### 方式 1: 运行检查脚本

```bash
python check_deps.py
```

### 方式 2: 手动检查

```bash
python -c "import flask, flask_cors, webview, PIL, dateutil; print('All OK')"
```

## 常见问题

### Q1: pip 下载速度太慢

**解决方案**：使用国内镜像

```bash
# 使用阿里云镜像
pip install -r config/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 使用清华大学镜像
pip install -r config/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用官方镜像（较慢）
pip install -r config/requirements.txt
```

### Q2: 报错 "No module named 'webview'"

**原因**：未安装依赖

**解决方案**：
```bash
pip install -r config/requirements.txt
python check_deps.py  # 验证
```

### Q3: 某个包安装失败

**解决方案**：逐个安装依赖

```bash
pip install flask==2.3.0
pip install flask-cors==4.0.0
pip install pywebview==6.1
pip install pillow==10.0.0
pip install python-dateutil==2.8.2
```

### Q4: 版本冲突

如果你有其他项目需要不同版本的包，建议使用虚拟环境：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安装依赖
pip install -r config/requirements.txt
```

## 升级依赖

如果需要升级某个包：

```bash
pip install --upgrade flask
pip install --upgrade pywebview
```

## 卸载依赖

```bash
pip uninstall -r config/requirements.txt -y
```

## 导出当前环境

如果后续对依赖进行了更改，可以导出：

```bash
pip freeze > config/requirements.txt
```

---

**安装完成后**，可以启动应用：

```bash
python src/BlurArc.py
```

或双击 `启动相册.bat` 脚本。
