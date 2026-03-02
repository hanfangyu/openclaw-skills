---
name: wechat-mp-publisher
description: 微信公众号文章发布技能，支持纯文本、带图文章发布，完全模拟人工操作无需API权限。
---
# 微信公众号文章发布技能
## 功能
- 发布纯文本文章
- 发布带图片/视频的文章
- 自动设置封面图、摘要
- 支持多公众号管理
- 自动留存登录Cookie，无需重复登录
- 模拟真人操作行为，降低封控风险
## 配置步骤
1. 安装依赖：`pip3 install playwright && playwright install chromium --with-deps`
2. 首次运行会自动打开浏览器，你扫码登录公众号平台，登录后Cookie会自动永久保存
## 使用方法
### 发布纯文本文章
```bash
python3 mp-pub.py "文章标题" "文章正文内容"
```
### 发布带图片文章
```bash
python3 mp-pub.py "文章标题" "文章正文内容" /path/to/cover.jpg /path/to/img1.jpg
```
### 多图文章
```bash
python3 mp-pub.py "文章标题" "文章正文内容" /path/to/cover.jpg /path/to/img1.jpg /path/to/img2.jpg
```
