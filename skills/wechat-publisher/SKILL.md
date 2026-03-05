---
name: wechat-publisher
description: "一键发布 Markdown 到微信公众号草稿箱。基于 wenyan-cli，支持多主题、代码高亮、图片自动上传。"
metadata:
  {
    "openclaw":
      {
        "emoji": "📱",
      },
  }
---

# wechat-publisher

**一键发布 Markdown 文章到微信公众号草稿箱**

基于 [wenyan-cli](https://github.com/caol64/wenyan-cli) 封装的 OpenClaw skill。

## 功能

- ✅ Markdown 自动转换为微信公众号格式
- ✅ 自动上传图片到微信图床
- ✅ 一键推送到草稿箱
- ✅ 多主题支持（代码高亮、Mac 风格代码块）
- ✅ 支持本地和网络图片

## 快速开始

### 1. 安装 wenyan-cli

**wenyan-cli 需要全局安装：**

```bash
npm install -g @wenyan-md/cli
```

**验证安装：**
```bash
wenyan --help
```

> **注意：** publish.sh 脚本会自动检测并安装 wenyan-cli（如果未安装）

### 2. 配置 API 凭证

API 凭证已保存在 `/Users/leebot/.openclaw/workspace/TOOLS.md`

确保环境变量已设置：
```bash
export WECHAT_APP_ID=your_wechat_app_id
export WECHAT_APP_SECRET=your_wechat_app_secret
```

**重要：** 确保你的 IP 已添加到微信公众号后台的白名单！

配置方法：https://yuzhi.tech/docs/wenyan/upload

### 3. 准备 Markdown 文件

文件顶部**必须**包含完整的 frontmatter（wenyan 强制要求）：

```markdown
---
title: 文章标题（必填！）
cover: https://example.com/cover.jpg  # 封面图（必填！）
---

# 正文开始

你的内容...
```

**⚠️ 关键发现（实测）：**
- `title` 和 `cover` **都是必填字段**！
- 缺少任何一个都会报错："未能找到文章封面"
- 虽然文档说"正文有图可省略cover"，但实际测试必须提供 cover
- 所有图片（本地/网络）都会自动上传到微信图床

**推荐封面图来源：**
```markdown
# 方案1: 相对路径（推荐，便于分享）
cover: ./assets/default-cover.jpg

# 方案2: 绝对路径
cover: /Users/bruce/photos/cover.jpg

# 方案3: 网络图片
cover: https://your-cdn.com/image.jpg
```

**💡 提示：** 使用相对路径时，从 Markdown 文件所在目录开始计算。

### 4. 发布文章

**方式 1: 使用 publish.sh 脚本**
```bash
cd /Users/leebot/.openclaw/workspace/wechat-publisher
./scripts/publish.sh /path/to/article.md
```

**方式 2: 直接使用 wenyan-cli**
```bash
wenyan publish -f article.md -t lapis -h solarized-light
```

**方式 3: 在 OpenClaw 中使用**
```
"帮我发布这篇文章到微信公众号" + 附带 Markdown 文件路径
```

## 主题选项

wenyan-cli 支持多种主题：

**内置主题：**
- `default` - 默认主题
- `lapis` - 青金石（推荐）
- `phycat` - 物理猫
- 更多主题见：https://github.com/caol64/wenyan-core/tree/main/src/assets/themes

**代码高亮主题：**
- `atom-one-dark` / `atom-one-light`
- `dracula`
- `github-dark` / `github`
- `monokai`
- `solarized-dark` / `solarized-light` (推荐)
- `xcode`

**使用示例：**
```bash
# 使用 lapis 主题 + solarized-light 代码高亮
wenyan publish -f article.md -t lapis -h solarized-light

# 使用 phycat 主题 + GitHub 代码高亮
wenyan publish -f article.md -t phycat -h github

# 关闭 Mac 风格代码块
wenyan publish -f article.md -t lapis --no-mac-style

# 关闭链接转脚注
wenyan publish -f article.md -t lapis --no-footnote
```

## 自定义主题

### 临时使用自定义主题
```bash
wenyan publish -f article.md -c /path/to/custom-theme.css
```

### 安装自定义主题（永久）
```bash
# 从本地文件安装
wenyan theme --add --name my-theme --path /path/to/theme.css

# 从网络安装
wenyan theme --add --name my-theme --path https://example.com/theme.css

# 使用已安装的主题
wenyan publish -f article.md -t my-theme

# 删除主题
wenyan theme --rm my-theme
```

### 列出所有主题
```bash
wenyan theme -l
```

## 工作流程

1. **准备内容** - 用 Markdown 写作
2. **运行脚本** - 一键发布到草稿箱
3. **审核发布** - 到公众号后台审核并发布

## Markdown 格式要求

### 必需的 Frontmatter

**⚠️ 关键（实测结果）：wenyan-cli 强制要求完整的 frontmatter！**

```markdown
---
title: 文章标题（必填！）
cover: 封面图片URL或路径（必填！）
---
```

**示例 1：相对路径（推荐）**
```markdown
---
title: 我的技术文章
cover: ./assets/cover.jpg
---

# 正文...
```

**示例 2：绝对路径**
```markdown
---
title: 我的技术文章
cover: /Users/bruce/photos/cover.jpg
---

# 正文...
```

**示例 3：网络图片**
```markdown
---
title: 我的技术文章
cover: https://example.com/cover.jpg
---

# 正文...
```

**❌ 错误示例（会报错）：**

```markdown
# 只有 title，没有 cover
---
title: 我的文章
---

错误信息：未能找到文章封面
```

```markdown
# 完全没有 frontmatter
# 我的文章

错误信息：未能找到文章封面
```

**💡 重要发现：**
- 虽然 wenyan 官方文档说"正文有图片可省略cover"
- 但**实际测试必须提供 cover**，否则报错
- title 和 cover **缺一不可**

### 图片支持
- ✅ 本地路径：`![](./images/photo.jpg)`
- ✅ 绝对路径：`![](/Users/bruce/photo.jpg)`
- ✅ 网络图片：`![](https://example.com/photo.jpg)`

所有图片会自动上传到微信图床！

### 代码块
````markdown
```python
def hello():
    print("Hello, WeChat!")
```
````

会自动添加代码高亮和 Mac 风格装饰。

## 推荐发布流程（白名单频繁变动场景）

当运行环境在内网、出口 IP 经常变化时，优先使用“中转机发布”流程，避免反复改公众号白名单。

### 标准执行入口（OpenClaw）

- 若工作区已提供 `publish-gzh.sh`，优先统一使用：

```bash
./publish-gzh.sh ./tmp/<article>.md
```

- 该脚本建议采用“单 SSH 会话上传+发布”，减少交互失败。

### 流程

1. 准备一台出口相对稳定的发布中转机（可内网机或固定公网 IP 机器）
2. 在中转机安装 Node/npm 与 `@wenyan-md/cli`
3. 在中转机配置 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`
4. 用 SSH key 配置免密登录（推荐，避免多会话重复输密码）
5. 由本地将 Markdown 同步到中转机，再在中转机执行 `wenyan publish`

### 参考命令（单 SSH 会话方式，减少交互问题）

```bash
ssh root@<relay-ip> "mkdir -p ~/gzh-publish && cat > ~/gzh-publish/article.md && cd ~/gzh-publish && WECHAT_APP_ID='***' WECHAT_APP_SECRET='***' wenyan publish -f article.md -t lapis -h solarized-light" < ./article.md
```

### SSH 免密配置（推荐）

```bash
# 本机生成 key（如不存在）
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519

# 把公钥拷到中转机
ssh-copy-id -i ~/.ssh/id_ed25519.pub -p 22 root@<relay-ip>

# 验证免密（应直接返回，不再提示 password）
ssh -o BatchMode=yes -p 22 root@<relay-ip> 'echo key-login-ok'
```

### 实战注意事项

- 若报 `invalid ip ... not in whitelist`：说明当前出口 IP 未加白名单
- 若报 `wenyan: command not found`：中转机未安装 `@wenyan-md/cli`
- 若报 `ERR_REQUIRE_ESM`（Node18 常见）：升级 Node 至 20+（建议 22 LTS）
- 若报 `Host key verification failed`：先写入 `~/.ssh/known_hosts`
- 若报 `未能找到文章标题`：补齐 frontmatter 的 `title`
- 若报 `未能找到文章封面`：补齐 frontmatter 的 `cover`
- 若仍提示密码：重新执行 `ssh-copy-id` 或检查 `~/.ssh/authorized_keys` 权限

## 故障排查

### 1. 上传失败：IP 不在白名单

**错误信息：** `ip not in whitelist`

**解决方法：**
1. 获取你的公网 IP：`curl ifconfig.me`
2. 登录微信公众号后台：https://mp.weixin.qq.com/
3. 开发 → 基本配置 → IP 白名单 → 添加你的 IP

### 2. wenyan-cli 未安装

**错误信息：** `wenyan: command not found`

**解决方法：**
```bash
npm install -g @wenyan-md/cli
```

### 3. 环境变量未设置

**错误信息：** `WECHAT_APP_ID is required`

**解决方法：**
```bash
export WECHAT_APP_ID=your_wechat_app_id
export WECHAT_APP_SECRET=your_wechat_app_secret
```

或在 `~/.zshrc` / `~/.bashrc` 中永久添加。

### 4. Frontmatter 缺失

**错误信息：** `title is required in frontmatter`

**解决方法：** 在 Markdown 文件顶部添加：
```markdown
---
title: 你的文章标题
---
```

## 参考资料

- wenyan-cli GitHub: https://github.com/caol64/wenyan-cli
- wenyan 官网: https://wenyan.yuzhi.tech
- 微信公众号 API 文档: https://developers.weixin.qq.com/doc/offiaccount/
- IP 白名单配置: https://yuzhi.tech/docs/wenyan/upload

## 更新日志

### 2026-02-05 - v1.0.0
- ✅ 初始版本
- ✅ 基于 wenyan-cli 封装
- ✅ 支持一键发布到草稿箱
- ✅ 多主题支持
- ✅ 自动图片上传

## License

Apache License 2.0 (继承自 wenyan-cli)
