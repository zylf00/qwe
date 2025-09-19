import time
import asyncio
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
import random

# 登录信息
EMAIL = "qq2629965614@gmail.com"
PASSWORD = "Lhp123456789"
LOGIN_URL = "https://dashboard.katabump.com/auth/login"
RENEW_URL = "https://dashboard.katabump.com/servers/edit?id=124653"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# CDP 补丁代码，直接嵌入在 Python 脚本中
CDP_PATCH_JS = r"""
(() => {
    Object.defineProperty(MouseEvent.prototype, 'screenX', {
        value: 100,
        writable: false,
        configurable: true
    });
    Object.defineProperty(MouseEvent.prototype, 'screenY', {
        value: 100,
        writable: false,
        configurable: true
    });
})();
"""

# 使用 DrissionPage 完成所有操作
async def main_with_drissionpage():
    # 使用 DrissionPage 启动一个全新的、独立的会话
    options = (
        ChromiumOptions()
        .auto_port()
        .incognito(True)
        .set_user_agent(UA)
        .set_argument('--no-sandbox')
        .set_argument('--disable-gpu')
        .set_argument('--disable-dev-shm-usage')
    )
    
    # 核心修改：移除 .headless()，让浏览器以有头模式运行
    page = ChromiumPage(options)
    
    # 注入 CDP 补丁函数
    def inject_cdp_patch(page):
        try:
            page.run_js(CDP_PATCH_JS)
            logger.info("CDP 补丁注入成功！")
        except Exception as e:
            logger.error(f"注入 CDP 补丁时发生错误: {e}")

    try:
        # 访问登录页面
        logger.info("开始登录...")
        page.get(LOGIN_URL)

        # 增加智能等待，确保页面元素加载完成
        page.wait.ele_displayed('#login-form', timeout=60)
        
        # 注入 CDP 补丁以修复指纹问题
        inject_cdp_patch(page)
        
        # 查找登录按钮
        login_btn = page.ele('#submit', timeout=10)
        
        # 输入邮箱和密码
        page.ele('#email', timeout=10).input(EMAIL)
        page.ele('#password', timeout=10).input(PASSWORD)
        
        # 点击登录按钮
        logger.info("正在点击登录按钮...")
        login_btn.click()
        time.sleep(5)

        # 确认是否登录成功
        if "dashboard" not in page.url:
            logger.error("登录失败，未跳转到仪表盘页面")
            page.get_screenshot(path='login_error_screenshot.png')
            return
        
        logger.info("登录成功，跳转到仪表盘")
        
        # 跳转到续期页面
        page.get(RENEW_URL)
        
        # 增加续期按钮的智能等待
        renew_btn = page.ele("css:button.btn.btn-outline-primary", timeout=30)
        
        # 完成续期操作
        logger.info("正在执行续期操作...")
        renew_btn.click()

        # 核心修复：处理 Turnstile 验证
        logger.info("等待 25 秒以确保确认弹窗和 Turnstile 加载...")
        await asyncio.sleep(25)
        
        logger.info("正在使用 shadow-root 逻辑查找 Turnstile 勾选框...")
        
        # 查找包含 Turnstile 信息的 div
        challenge_solution = page.ele("xpath://*[@name='cf-turnstile-response']", timeout=60)
        
        if challenge_solution:
            challenge_wrapper = challenge_solution.parent()
            
            if challenge_wrapper and challenge_wrapper.shadow_root:
                challenge_iframe = challenge_wrapper.shadow_root.ele("tag:iframe", timeout=10)
                
                if challenge_iframe:
                    logger.info("找到 iframe，正在切换并点击...")
                    # 关键修复: 恢复为与你当前库版本兼容的 API
                    page.change_to_frame(challenge_iframe)
                    
                    checkbox = page.ele("css:input[type='checkbox']", timeout=10)
                    
                    if checkbox:
                        logger.info("找到勾选框，正在进行模拟点击...")
                        
                        checkbox.click()
                        time.sleep(5)
                        
                        logger.success("Turnstile 验证通过！")
                    else:
                        logger.error("未找到 Turnstile 勾选框。")
                    
                    # 切换回主页面
                    # 关键修复: 恢复为与你当前库版本兼容的 API
                    page.change_to_main()
                else:
                    logger.error("未在 shadow-root 中找到 iframe。")
            else:
                logger.error("未找到包含 shadow-root 的 div。")
        else:
            logger.error("未找到 'cf-turnstile-response' 元素。")
            page.get_screenshot(path='turnstile_not_found.png')
            return
        
        time.sleep(5)
        
        logger.success("续期完成！")

        logger.info("正在截取续期成功后的页面截图...")
        try:
            page.get_screenshot(path='success_screenshot.png')
            logger.success("已保存续期成功截图到 success_screenshot.png")
        except Exception as se:
            logger.error(f"无法保存续期成功截图: {se}")

    except Exception as e:
        logger.error(f"脚本执行过程中发生错误: {e}")
        logger.warning("脚本发生错误，正在尝试保存调试信息...")
        try:
            page.get_screenshot(path='error_screenshot.png')
            logger.error(f"已保存页面截图到 error_screenshot.png")
        except Exception as se:
            logger.error(f"无法保存截图: {se}")

    finally:
        page.close()

# 运行主函数
if __name__ == "__main__":
    asyncio.run(main_with_drissionpage())
