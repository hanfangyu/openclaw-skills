import sys
import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIE_PATH = Path(__file__).parent / "weibo_cookies.json"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def save_cookies(context):
    cookies = context.cookies()
    with open(COOKIE_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print("✅ 登录信息已保存，后续无需重复登录")

def load_cookies(context):
    if not COOKIE_PATH.exists():
        return False
    with open(COOKIE_PATH, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)
    return True

def random_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

def main():
    if len(sys.argv) < 2:
        print("❌ 使用方法：python3 weibo-pub.py <微博内容> [图片路径1 图片路径2 ...]")
        return

    content = sys.argv[1]
    images = sys.argv[2:] if len(sys.argv) > 2 else []

    with sync_playwright() as p:
        # 服务器无图形界面，全程无头模式运行
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1920, "height": 1080})
        
        # 加载已有Cookie
        if load_cookies(context):
            print("✅ 已加载历史登录信息")
        
        page = context.new_page()
        
        # 打开微博首页
        page.goto("https://weibo.com/")
        random_delay(2, 4)
        
        # 检查是否需要登录
        if page.url.startswith("https://passport.weibo.com/") or "登录" in page.title():
            print("🔑 检测到需要登录，正在截取登录二维码...")
            # 切换到扫码登录
            try:
                qrcode_tab = page.locator("text=扫码登录")
                if qrcode_tab.is_visible():
                    qrcode_tab.click()
                    random_delay(1, 2)
            except:
                pass
            
            # 等待二维码加载（尝试多种选择器）
            qrcode_selectors = [
                "img.qrcode-img",
                "img[alt*='二维码']",
                "div.qrcode_img img",
                "canvas[class*='qrcode']"
            ]
            qrcode_found = False
            for selector in qrcode_selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    qrcode_img = page.locator(selector)
                    qrcode_path = Path(__file__).parent / "login_qrcode.png"
                    qrcode_img.screenshot(path=qrcode_path)
                    print(f"✅ 登录二维码已保存到 {qrcode_path}")
                    qrcode_found = True
                    break
                except:
                    continue
            
            # 如果找不到特定元素，截图整个登录页面
            if not qrcode_found:
                qrcode_path = Path(__file__).parent / "login_page.png"
                page.screenshot(path=qrcode_path, full_page=True)
                print(f"✅ 登录页面已截图保存到 {qrcode_path}")
            
            # 发送二维码到Discord私信
            import subprocess
            msg_cmd = [
                "openclaw", "message", "send",
                "--channel", "discord",
                "--to", "user:1089470658276229140",
                "--message", "🔑 微博登录二维码，请扫码登录~",
                "--media", str(qrcode_path)
            ]
            subprocess.run(msg_cmd, capture_output=True, text=True)
            print("✅ 二维码已发送到你的Discord私信")
            print("⏳ 等待扫码登录中，请在2分钟内完成...")
            # 等待登录完成，直到跳转到首页
            try:
                page.wait_for_url("https://weibo.com/*", timeout=180000)
                save_cookies(context)
                print("✅ 登录成功！")
            except:
                print("⏰ 等待登录超时，请稍后重试")
                browser.close()
                return
            # 删除临时二维码
            if qrcode_path.exists():
                qrcode_path.unlink()
            random_delay(3, 5)
        
        # 点击右上角写微博按钮
        print("✍️ 准备发布内容...")
        publish_btn = page.locator("a[title='写微博']")
        publish_btn.click()
        random_delay(2, 3)
        # 切换到输入框
        edit_box = page.locator("textarea.Form_input_2gtXx")
        edit_box.click()
        random_delay(1, 2)
        
        # 输入内容，逐字输入模拟真人
        for char in content:
            edit_box.type(char, delay=random.randint(50, 150))
        random_delay(2, 3)
        
        # 上传图片
        if images:
            print("🖼️ 正在上传图片...")
            upload_btn = page.locator("input[type='file']").first
            upload_btn.set_input_files(images)
            # 等待图片上传完成
            page.wait_for_selector("div[class*='upload_progress']", state="hidden", timeout=30000)
            random_delay(2, 4)
        
        # 点击发送按钮
        send_btn = page.locator("button:has-text('发送')").first
        send_btn.click()
        print("🚀 正在提交发布...")
        
        # 等待发送成功
        page.wait_for_selector("div:has-text('发布成功')", timeout=10000)
        random_delay(1, 2)
        
        # 获取最新微博链接
        page.goto("https://weibo.com/myprofile")
        random_delay(2, 3)
        latest_weibo = page.locator("div[class*='wb_main'] a[href*='/status/']").first
        weibo_url = latest_weibo.get_attribute("href")
        if weibo_url and not weibo_url.startswith("http"):
            weibo_url = "https:" + weibo_url
        
        print(f"✅ 微博发布成功！链接：{weibo_url}")
        
        browser.close()

if __name__ == "__main__":
    main()
