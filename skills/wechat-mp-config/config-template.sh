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

# AppID（从微信公众平台获取，必须先与用户确认）
export WECHAT_APP_ID="<请填写用户确认的 AppID>"

# AppSecret（从微信公众平台获取，必须先与用户确认；敏感信息请从安全渠道获取）
export WECHAT_APP_SECRET="<请填写用户确认的 AppSecret>"

# 公众号名称（用于确认发布目标账号，可选但强烈建议）
export WECHAT_MP_NAME="<请填写用户确认的公众号名称>"

# ==========================================
# 配置验证
# ==========================================

if [ -z "$WECHAT_APP_ID" ] || [ "$WECHAT_APP_ID" = "<请填写用户确认的 AppID>" ]; then
    echo "❌ 错误：WECHAT_APP_ID 未配置"
    echo "请编辑此文件，填入用户确认的公众号 AppID"
    exit 1
fi

if [ -z "$WECHAT_APP_SECRET" ] || [ "$WECHAT_APP_SECRET" = "<请填写用户确认的 AppSecret>" ]; then
    echo "⚠️  警告：WECHAT_APP_SECRET 未正确配置"
    echo "请从安全渠道获取用户确认的 AppSecret 后填入"
fi

if [ -z "$WECHAT_MP_NAME" ] || [ "$WECHAT_MP_NAME" = "<请填写用户确认的公众号名称>" ]; then
    echo "⚠️  警告：WECHAT_MP_NAME 未配置"
    echo "建议填写用户确认的公众号名称，避免误投递到错误账号"
fi

echo "✅ 微信公众号配置已加载"
echo "   公众号: ${WECHAT_MP_NAME}"
echo "   AppID: ${WECHAT_APP_ID:0:8}..."
echo ""
echo "现在可以使用 wenyan publish 发布文章到公众号草稿箱了"
echo ""
echo "使用示例："
echo "  wenyan publish -f /path/to/article.md -t lapis -h solarized-light"
