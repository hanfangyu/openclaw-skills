---
name: wechat-mp-config
description: "微信公众号发布配置模板。用于配置 OpenClaw 的公众号发布功能；在涉及公众号名称、AppID、AppSecret 时必须先与用户确认后再填写。"
metadata:
  {
    "openclaw":
      {
        "emoji": "📱",
      },
  }
---

# 微信公众号发布配置

这个 skill 提供微信公众号发布功能的快速配置指南。执行配置前，先与用户确认公众号名称、AppID、AppSecret 以及发布目标账号。

## 快速开始

### 1. 安装 wenyan-cli

**wenyan-cli 是微信文章发布工具，需要全局安装：**

```bash
npm install -g @wenyan-md/cli
```

**验证安装：**
```bash
wenyan --help
```

### 2. 配置微信公众号凭证

你需要从微信公众号后台获取 **AppID** 和 **AppSecret**：

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 设置与开发 → 基本配置
3. 复制 AppID 和 AppSecret

### 3. 添加服务器IP到白名单

**重要：** 必须将服务器IP添加到公众号IP白名单，否则无法发布文章！

1. 在公众号后台：设置与开发 → 基本配置 → IP 白名单
2. 添加你的服务器公网IP（可以用 `curl ifconfig.me` 查看）
3. 保存配置

### 4. 设置环境变量

在 ~/.bashrc 或 ~/.zshrc 中添加：

```bash
export WECHAT_APP_ID="你的公众号AppID"
export WECHAT_APP_SECRET="你的公众号AppSecret"
```

然后执行 `source ~/.bashrc` 或 `source ~/.zshrc` 使配置生效。

### 5. 准备文章

创建一个 Markdown 文件，文件顶部必须包含 frontmatter：

```markdown
---
title: 文章标题（必填）
cover: 封面图片URL（必填）
---

# 正文开始

你的文章内容...
```

**⚠️ 注意：** title 和 cover 都是必填项，缺少任何一个都会报错。

### 6. 发布文章

```bash
wenyan publish -f /path/to/article.md -t lapis -h solarized-light
```

发布成功后，文章会自动推送到公众号草稿箱，到公众号后台审核后即可发布。

## 账号确认与安全要求

在配置前必须先与用户确认以下信息：

- 公众号名称（用于确认发布目标）
- AppID
- AppSecret

```bash
export WECHAT_APP_ID="<用户确认的 AppID>"
export WECHAT_APP_SECRET="<用户确认的 AppSecret>"
```

**⚠️ 安全提醒：** AppSecret 是敏感信息，请通过安全渠道（私信、加密消息等）获取，不要在公开渠道传输。

## 主题选择

wenyan-cli 支持多种主题：

**推荐主题：**
- `lapis` - 青金石主题（美观）
- `phycat` - 物理猫主题
- `default` - 默认主题

**代码高亮主题：**
- `solarized-light` - 推荐，清晰的代码高亮
- `github-dark` - GitHub深色主题
- `monokai` - Monokai主题

**使用示例：**
```bash
wenyan publish -f article.md -t lapis -h solarized-light
```

## 图片处理

### 本地图片
```markdown
![](./images/photo.jpg)
```

### 网络图片
```markdown
![](https://example.com/photo.jpg)
```

所有图片（本地和网络）都会自动上传到微信图床！

### 封面图推荐
使用高质量的封面图可以提升文章点击率：

```markdown
---
title: 你的文章
cover: https://images.unsplash.com/photo-xxx?w=1200&h=630&fit=crop
---
```

**推荐封面图尺寸：** 2.35:1 比例，建议宽度 1200px 以上。

## 常见问题

### Q: 发布失败，提示 "ip not in whitelist"
**A:** 服务器IP未添加到公众号IP白名单。请到公众号后台添加。

### Q: 提示 "未能找到文章封面"
**A:** Markdown 文件缺少 frontmatter，或者 cover 字段为空。确保文件顶部包含：
```markdown
---
title: 标题
cover: 封面图URL
---
```

### Q: wenyan: command not found
**A:** wenyan-cli 未安装或不在PATH中。运行 `npm install -g @wenyan-md/cli` 安装。

### Q: 图片上传失败
**A:** 检查网络连接，或者使用本地图片。网络图片下载可能受限。

## 自动化脚本

你可以创建一个发布脚本，方便一键发布：

```bash
#!/bin/bash
# publish-wechat.sh

export WECHAT_APP_ID="你的AppID"
export WECHAT_APP_SECRET="你的AppSecret"

if [ -z "$1" ]; then
    echo "Usage: ./publish-wechat.sh <markdown-file>"
    exit 1
fi

wenyan publish -f "$1" -t lapis -h solarized-light
```

使用方法：
```bash
chmod +x publish-wechat.sh
./publish-wechat.sh /path/to/article.md
```

## 相关资源

- wenyan-cli GitHub: https://github.com/caol64/wenyan-cli
- 微信公众号开发文档: https://developers.weixin.qq.com/doc/offiaccount/
- Unsplash 免费图片: https://unsplash.com

## License

Apache License 2.0
