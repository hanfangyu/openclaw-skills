import sys
import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

COOKIE_PATH = Path(__file__).parent / "wechat_mp_cookies.json"
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
    if len(sys.argv) < 3:
        print("❌ 使用方法：python3 mp-pub.py <文章标题> <文章正文> [封面图路径 图片路径...]")
        return

    title = sys.argv[1]
    content = sys.argv[2]
    images = sys.argv[3:] if len(sys.argv) > 3 else []

    with sync_playwright() as p:
        # 服务器无图形界面，全程无头模式运行
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1920, "height": 1080})
        
        # 加载已有Cookie
        if load_cookies(context):
            print("✅ 已加载历史登录信息")
        
        page = context.new_page()
        
        # 打开公众号平台
        page.goto("https://mp.weixin.qq.com/")
        random_delay(2, 4)
        
        # 检查是否需要登录
        if page.url.startswith("https://mp.weixin.qq.com/") and ("登录" in page.title() or "login" in page.url.lower()):
            print("🔑 检测到需要登录，正在尝试扫码登录...")
            # 等待二维码区域加载（微信公众号可能有多种登录方式）
            try:
                page.wait_for_selector("img.qrcode, div.qrcode_img, img[alt*='二维码']", timeout=5000)
                qrcode_path = Path(__file__).parent / "login_qrcode.png"
                page.screenshot(path=qrcode_path)
                print(f"✅ 登录二维码已保存到 {qrcode_path}")
                
                # 发送二维码到Discord私信
                import subprocess
                msg_cmd = [
                    "openclaw", "message", "send",
                    "--channel", "discord",
                    "--to", "user:1089470658276229140",
                    "--message", "🔑 微信公众号登录二维码，请扫码登录~",
                    "--media", str(qrcode_path)
                ]
                subprocess.run(msg_cmd, capture_output=True, text=True)
                print("✅ 二维码已发送到你的Discord私信")
            except:
                print("⚠️ 未找到二维码元素，尝试等待手动登录...")
            
            # 等待登录完成（检测URL变化）
            page.wait_for_url("https://mp.weixin.qq.com/cgi-bin/home*", timeout=120000)
            save_cookies(context)
            random_delay(3, 5)
        
        # 点击"新建群发"或"图文消息"
        print("✍️ 准备发布文章...")
        try:
            # 尝试点击新建群发按钮
            new_msg_btn = page.locator("a:has-text('新建群发'), button:has-text('新建图文')").first
            new_msg_btn.click()
            random_delay(2, 3)
        except:
            # 如果找不到，尝试点击左侧菜单的图文消息
            menu_btn = page.locator("a[href*='appMsg'], div.menu-item:has-text('图文消息')").first
            menu_btn.click()
            random_delay(2, 3)
        
        # 输入标题
        title_input = page.locator("input[placeholder*='标题'], input.edui-editor-not-imp-title").first
        title_input.fill(title)
        random_delay(1, 2)
        
        # 输入正文内容
        content_input = page.locator("div.edui-editor-body, div.weui-desktop-editor__content").first
        content_input.fill(content)
        random_delay(2, 3)
        
        # 上传封面图
        if images:
            print("🖼️ 正在上传图片...")
            for i, img_path in enumerate(images):
                try:
                    # 尝试找到上传按钮
                    upload_btn = page.locator("input[type='file']").first
                    upload_btn.set_input_files(img_path)
                    print(f"✅ 图片 {i+1} 上传中...")
                    random_delay(2, 4)
                except Exception as e:
                    print(f"⚠️ 图片 {i+1} 上传失败：{e}")
        
        # 点击预览或发布
        try:
            # 优先点击预览，确认无误后再发布
            preview_btn = page.locator("button:has-text('预览')").first
            preview_btn.click()
            print("📋 文章已生成预览，请在公众号平台手动确认发布")
        except:
            print("✅ 文章内容已填入，请在公众号平台手动确认发布")
        
        print("💡 提示：文章已准备就绪，请前往公众号平台检查内容并手动点击发布")
        browser.close()

if __name__ == "__main__":
    main()
