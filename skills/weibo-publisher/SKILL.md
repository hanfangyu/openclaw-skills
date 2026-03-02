---
name: weibo-publisher
description: 微博自动发布技能，支持纯文本、带图微博发布，完全模拟真人操作无需API权限。
---
# 微博自动发布技能
## 功能
- 发布纯文本微博
- 发布带图片/视频的微博
- 自动留存登录Cookie，无需重复登录
- 模拟真人操作行为，随机延迟，降低封控风险
## 配置步骤
1. 安装依赖：`pip3 install playwright && playwright install chromium`
2. 首次运行会自动打开浏览器，你扫码登录微博网页版即可，登录后Cookie会自动永久保存，后续不用再登录
## 使用方法
### 发布纯文本微博
```bash
python3 weibo-pub.py "你要发布的微博内容"
```
### 发布带图片/视频的微博
```bash
python3 weibo-pub.py "你要发布的微博内容" /absolute/path/to/your/image.jpg
```
### 发布多张图片
```bash
python3 weibo-pub.py "你要发布的微博内容" /path/to/img1.jpg /path/to/img2.jpg /path/to/img3.jpg
```
