# 微信公众号发布配置 Skill

快速在OpenClaw上配置微信公众号发布功能，支持一键发布Markdown文章到公众号草稿箱。

## 快速开始（5分钟配置）

### 步骤1：安装wenyan-cli

```bash
npm install -g @wenyan-md/cli
```

### 步骤2：配置公众号凭证

编辑 `config-template.sh`，填入你的公众号AppID和AppSecret：

```bash
export WECHAT_APP_ID="你的AppID"
export WECHAT_APP_SECRET="你的AppSecret"
```

### 步骤3：添加服务器IP到白名单

1. 查看服务器公网IP：`curl ifconfig.me`
2. 登录[微信公众平台](https://mp.weixin.qq.com/)
3. 设置与开发 → 基本配置 → IP 白名单 → 添加IP

### 步骤4：加载配置

```bash
source config-template.sh
```

### 步骤5：发布文章

```bash
wenyan publish -f /path/to/article.md -t lapis -h solarized-light
```

文章会自动推送到公众号草稿箱，到后台审核后即可发布。

## 文章格式要求

Markdown文件顶部必须包含frontmatter：

```markdown
---
title: 文章标题（必填）
cover: 封面图片URL（必填）
---

# 正文开始

你的内容...
```

## 常用命令

### 验证配置
```bash
source config-template.sh
echo $WECHAT_APP_ID
```

### 发布文章（默认主题）
```bash
wenyan publish -f article.md -t lapis -h solarized-light
```

### 发布文章（指定主题）
```bash
wenyan publish -f article.md -t phycat -h github-dark
```

## 主题推荐

- **lapis + solarized-light** - 青金石主题，适合技术文章
- **phycat + github-dark** - 物理猫主题，适合开发文章
- **default + monokai** - 默认主题，适合通用文章

## 配置原则（必须先确认）

请勿预置任何固定公众号名称或凭证。

每次配置前必须与用户确认：

- 公众号名称（确认发布目标）
- AppID
- AppSecret

```bash
export WECHAT_APP_ID="<用户确认的 AppID>"
export WECHAT_APP_SECRET="<用户确认的 AppSecret>"
```

**⚠️ 重要：** AppSecret 请通过私信等安全渠道获取，不要在公开渠道传输。

## 故障排查

### 发布失败：ip not in whitelist
**原因：** 服务器IP未添加到公众号IP白名单
**解决：** 到公众号后台添加IP

### 发布失败：未能找到文章封面
**原因：** Markdown缺少frontmatter或cover字段
**解决：** 确保文件顶部包含title和cover

### wenyan: command not found
**原因：** wenyan-cli未安装
**解决：** 运行 `npm install -g @wenyan-md/cli`

### 图片下载失败
**原因：** 网络图片URL无法访问
**解决：** 使用本地图片或其他网络图片

## 安全提醒

- AppSecret是敏感信息，不要在公开渠道传输
- 配置文件建议添加到 .gitignore
- 定期更换AppSecret提高安全性

## 相关链接

- [wenyan-cli文档](https://github.com/caol64/wenyan-cli)
- [微信公众平台](https://mp.weixin.qq.com/)
- [公众号开发文档](https://developers.weixin.qq.com/doc/offiaccount/)

## License

Apache License 2.0
