#!/bin/bash
# 微信公众号配置脚本
# 使用方法：
# 1. 复制此文件到你的OpenClaw workspace
# 2. 填写下面的 AppID 和 AppSecret
# 3. 执行: source config-template.sh
# 4. 配置就生效了

# ==========================================
# 填写你的微信公众号配置
# ==========================================

# AppID（从微信公众平台获取）
export WECHAT_APP_ID="wxe25dd0dc32cde8c7"

# AppSecret（从微信公众平台获取，敏感信息请从安全渠道获取）
export WECHAT_APP_SECRET="请从安全渠道获取"

# ==========================================
# 博纳影业AIGMS制作中心配置示例
# ==========================================

# 如果你需要配置博纳影业AIGMS制作中心的公众号：
# export WECHAT_APP_ID="wxe25dd0dc32cde8c7"
# export WECHAT_APP_SECRET="请从安全渠道获取"

# ==========================================
# 配置验证
# ==========================================

if [ -verz "$WECHAT_APP_ID" ]; then
    echo "❌ 错误：WECHAT_APP_ID 未配置"
    echo "请编辑此文件，填入你的公众号 AppID"
    exit 1
fi

if [ -z "$WECHAT_APP_SECRET" ] || [ "$WECHAT_APP_SECRET" = "请从安全渠道获取" ]; then
    echo "⚠️  警告：WECHAT_APP_SECRET 未正确配置"
    echo "请从安全渠道（私信、加密消息）获取 AppSecret 后填入"
fi

echo "✅ 微信公众号配置已加载"
echo "   AppID: ${WECHAT_APP_ID:0:8}..."
echo ""
echo "现在可以使用 wenyan publish 发布文章到公众号草稿箱了"
echo ""
echo "使用示例："
echo "  wenyan publish -f /path/to/article.md -t lapis -h solarized-light"
