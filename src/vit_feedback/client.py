import os
import time
import shutil
import logging
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

from vit_feedback.captcha import solve_captcha_base64

logger = logging.getLogger(__name__)

PORTAL_URL = "https://vtopregcc.vit.ac.in/endfeedback/"

def find_browser_executable() -> Optional[str]:
    """Auto-detect Chromium-based browser executable on the system (e.g. NixOS Brave)."""
    candidates = [
        "/run/current-system/sw/bin/brave",
        "/run/current-system/sw/bin/google-chrome",
        "/run/current-system/sw/bin/chromium",
        shutil.which("brave"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("google-chrome-stable"),
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None

class VitFeedbackClient:
    """Manages browser session, cookie isolation, and authentication for VIT Feedback."""

    def __init__(self, browser_path: Optional[str] = None, headless: bool = True):
        self.browser_path = browser_path or find_browser_executable()
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_logged_in: bool = False
        self.all_already_posted: bool = False

    def is_logged_in(self) -> bool:
        return self._is_logged_in

    def get_page(self) -> Page:
        if not self._page:
            self.start()
        return self._page

    def start(self):
        """Start Playwright browser and fresh context."""
        if self._browser and self._page:
            return
        logger.info("Starting Playwright (headless=%s, browser_path=%s)", self.headless, self.browser_path)
        self._playwright = sync_playwright().start()
        launch_args = {"headless": self.headless}
        if self.browser_path:
            launch_args["executable_path"] = self.browser_path
        
        self._browser = self._playwright.chromium.launch(**launch_args)
        self._context = self._browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._page = self._context.new_page()

    def clear_session(self):
        """Clear all session cookies and local state to prevent multi-tab conflicts."""
        if self._context:
            self._context.clear_cookies()
        if self._page:
            try:
                self._page.evaluate("""() => {
                    localStorage.clear();
                    sessionStorage.clear();
                }""")
            except Exception:
                pass

    def navigate_to_login(self):
        """Navigate to portal root and ensure the clean login form is displayed."""
        page = self.get_page()
        self.clear_session()
        logger.info("Navigating to %s", PORTAL_URL)
        page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(1)

        # Check if portal greeted with Multi-Tab or Session Expired banner
        content = page.content()
        if "Multiple Tabs Access prevented" in content or "Session Expired" in content:
            logger.info("Detected session banner. Clearing session and refreshing...")
            self.clear_session()
            page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(1)

        # If a login button on expired form exists, submit it to reach the real form
        submit_btn = page.query_selector('input[type="submit"][value="Login"]')
        if submit_btn:
            submit_btn.click()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1)

        page.wait_for_selector("#studLogin", timeout=15000)

    def _extract_and_solve_captcha(self) -> str:
        page = self.get_page()
        page.wait_for_selector("#captcha_id", timeout=10000)
        captcha_src = page.evaluate("document.getElementById('captcha_id').src")
        return solve_captcha_base64(captcha_src)

    def _refresh_and_wait_new_captcha(self) -> str:
        """Trigger captcha refresh via AJAX and wait for the new image and unblockUI."""
        page = self.get_page()
        try:
            new_src = page.evaluate("""() => {
                return new Promise((resolve) => {
                    const oldSrc = document.getElementById('captcha_id') ? document.getElementById('captcha_id').src : '';
                    if (typeof doRefreshCaptcha === 'function') {
                        doRefreshCaptcha();
                    }
                    const interval = setInterval(() => {
                        const img = document.getElementById('captcha_id');
                        const unblocked = document.querySelector('.blockUI') === null;
                        if (img && img.src && img.src !== oldSrc && unblocked) {
                            clearInterval(interval);
                            resolve(img.src);
                        }
                    }, 200);
                    setTimeout(() => {
                        clearInterval(interval);
                        resolve(document.getElementById('captcha_id') ? document.getElementById('captcha_id').src : '');
                    }, 8000);
                });
            }""")
            return new_src or ""
        except Exception as e:
            logger.warning("Error refreshing captcha: %s", e)
            return ""

    def _dismiss_sweetalert_if_any(self) -> Optional[str]:
        """Dismiss swal popup if present and return the title text."""
        page = self.get_page()
        try:
            title = page.evaluate("""() => {
                const h2 = document.querySelector('.sweet-alert h2');
                if (h2 && h2.offsetParent !== null) {
                    const text = h2.innerText;
                    const okBtn = document.querySelector('.sweet-alert button.confirm');
                    if (okBtn) okBtn.click();
                    return text;
                }
                return null;
            }""")
            if title:
                time.sleep(0.5)
                return title
        except Exception:
            pass
        return None

    def login(self, username: str, password: str, max_retries: int = 8) -> bool:
        """Log in with username and password, automatically solving the captcha."""
        self.navigate_to_login()
        page = self.get_page()

        for attempt in range(1, max_retries + 1):
            logger.info("Login attempt %d/%d for user %s", attempt, max_retries, username)
            
            # Dismiss any lingering alerts
            self._dismiss_sweetalert_if_any()

            # Ensure fields exist
            page.fill("#userName", username)
            page.fill("#password", password)

            # Solve captcha
            captcha_val = self._extract_and_solve_captcha()
            
            # Refresh if OCR didn't yield exactly 6 characters
            refreshes = 0
            while len(captcha_val) != 6 and refreshes < 4:
                logger.info("Captcha '%s' length is %d (needs 6). Refreshing...", captcha_val, len(captcha_val))
                self._refresh_and_wait_new_captcha()
                captcha_val = self._extract_and_solve_captcha()
                refreshes += 1

            logger.info("Submitting with captcha: %s", captcha_val)
            page.fill("#captchaString", captcha_val)

            # Click login button
            page.click('button[type="submit"]')
            time.sleep(2.0)

            # Check if sweetalert popped up
            alert_text = self._dismiss_sweetalert_if_any()
            if alert_text:
                logger.warning("SweetAlert dialog appeared: '%s'", alert_text)
                if "already posted" in alert_text.lower():
                    logger.info("All feedback for this semester has already been completed!")
                    self._is_logged_in = True
                    self.all_already_posted = True
                    return True
                elif "Invalid Captcha" in alert_text or "Enter Captcha" in alert_text or "Not valid" in alert_text:
                    logger.info("Refreshing captcha for next attempt...")
                    self._refresh_and_wait_new_captcha()
                    time.sleep(0.5)
                    continue
                elif "Invalid" in alert_text and ("User" in alert_text or "Password" in alert_text):
                    raise ValueError(f"Portal rejected credentials: {alert_text}")

            # Verify if dashboard loaded
            sign_out = page.query_selector("button:has-text('Sign out')")
            if sign_out and sign_out.is_visible():
                logger.info("Login successful!")
                self._is_logged_in = True
                return True

            if page.query_selector("text='FEEDBACK - CLASS WISE'"):
                logger.info("Login successful (detected feedback table)!")
                self._is_logged_in = True
                return True

        self._is_logged_in = False
        raise RuntimeError(f"Login failed after {max_retries} attempts.")

    def logout(self):
        """Log out and release session."""
        if self._page and self._is_logged_in:
            try:
                sign_out = self._page.query_selector("button:has-text('Sign out')")
                if sign_out and sign_out.is_visible():
                    sign_out.click()
                    time.sleep(1)
                else:
                    self._page.evaluate("if (typeof location !== 'undefined') location.href='processLogout';")
            except Exception as e:
                logger.warning("Logout warning: %s", e)
        self._is_logged_in = False
        self.clear_session()

    def close(self):
        """Close browser and stop Playwright."""
        self.logout()
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None
