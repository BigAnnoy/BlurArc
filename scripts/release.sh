#!/bin/bash

# Blur Arc 发布脚本
# 功能：
# 1. 检查 Git 状态
# 2. 创建 tag
# 3. 触发构建
# 4. 创建 GitHub Release
# 5. 上传构建产物

# 使用方法：
# bash scripts/release.sh

set -e

# 配置
REPO_NAME="blurarc/blurarc"
VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.5.0")
CHANGELOG_FILE="CHANGELOG.md"

echo "=========================================="
echo "Blur Arc 发布脚本 v1.0"
echo "=========================================="
echo "版本：$VERSION"
echo ""

# 1. 检查 Git 状态
echo "1. 检查 Git 状态..."
if [ -n "$(git status --porcelain)" ]; then
    echo "✗ 工作目录有未提交的更改，请先提交或stash"
    exit 1
fi
echo "✓ 工作目录干净"

# 2. 检查远程仓库
echo "2. 检查远程仓库..."
git fetch origin
echo "✓ 远程仓库已同步"

# 3. 确认发布
echo "3. 确认发布..."
echo "即将发布版本：$VERSION"
read -p "确认发布？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "发布已取消"
    exit 1
fi

# 4. 创建 Git tag（如果不存在）
echo "4. 处理 Git tag..."
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "  Tag $VERSION 已存在，跳过创建"
else
    echo "  创建 tag：$VERSION"
    git tag -a "$VERSION" -m "Release $VERSION"
    git push origin "$VERSION"
fi

# 5. 构建
echo "5. 触发构建..."
echo "请在 CI/CD 完成构建后继续"
echo "构建完成后，运行以下命令上传产物："
echo "  gh release upload $VERSION dist/* --repo $REPO_NAME"
echo ""
read -p "构建完成并已上传产物？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "发布流程已暂停，请在构建完成后继续"
    exit 1
fi

# 6. 创建 GitHub Release
echo "6. 创建 GitHub Release..."
if command -v gh &> /dev/null; then
    # 生成发布说明
    RELEASE_NOTES="## 安装说明\n\n下载对应平台的安装包并运行。\n\n## 系统要求\n\n- Windows 10/11 或 macOS 10.14+\n- Python 3.11+\n\n## 更新内容\n\n请查看 CHANGELOG.md"

    gh release create "$VERSION" \
        --title "Blur Arc $VERSION" \
        --notes "$RELEASE_NOTES" \
        --repo "$REPO_NAME"
    echo "✓ Release 已创建"
else
    echo "⚠ gh CLI 未安装，请手动创建 Release"
    echo "访问：https://github.com/$REPO_NAME/releases/new?tag=$VERSION"
fi

echo ""
echo "=========================================="
echo "✓ 发布完成！"
echo "=========================================="
echo "版本：$VERSION"
echo "Release：https://github.com/$REPO_NAME/releases/tag/$VERSION"
