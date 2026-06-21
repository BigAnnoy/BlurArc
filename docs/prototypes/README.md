# UI 原型目录

> **工作流约定：以后任何 UI 修改，必须先在此目录设计原型，确认后再实施代码。**

## 目录结构

```
prototypes/
├── mobile/       # 手机端原型
├── tablet/       # 平板端原型
└── desktop/      # 桌面端原型
```

## 命名规范

```
<platform>/<feature>-v<version>[-<theme>].html

示例：
mobile/album-v3-dark.html
mobile/album-v3-light.html
tablet/album-v3-dark.html
```

- **platform**: `mobile` / `tablet` / `desktop`
- **feature**: 功能页面名称（如 `album`、`upload`、`settings`）
- **version**: 版本号（`v1`、`v2`、`v3`...），每次大改递增
- **theme**: 可选，`dark` / `light`，同时有暗色和亮色时分别建文件

## 工作流程

1. **设计原型** — 在 `prototypes/<platform>/` 下新建 HTML 文件，用纯 HTML/CSS 模拟目标 UI
2. **预览确认** — 浏览器打开原型文件，与用户确认设计细节
3. **生成方案** — 根据确认的原型生成技术实现方案文档（放 `docs/superpowers/specs/`）
4. **实施代码** — 按方案逐步实施，实施完成后原型保留作为视觉参考

## 现有原型

| 文件 | 说明 |
|------|------|
| `mobile/mobile-app-v2.html` | 手机端 v2（旧版） |
| `mobile/mobile-app-v3-dark.html` | 手机端 v3 暗色主题 |
| `mobile/mobile-app-v3-light.html` | 手机端 v3 亮色主题 |
| `tablet/tablet-app-v3-dark.html` | 平板端 v3 暗色主题 |
| `tablet/tablet-app-v3-light.html` | 平板端 v3 亮色主题 |
