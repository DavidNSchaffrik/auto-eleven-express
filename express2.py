import asyncio
import os
import time
from pathlib import Path

import nodriver as uc
import pyautogui

TARGET_URL = (
    "https://new.express.adobe.com/tools/animate-from-audio/"
    "?referrer=https%3A%2F%2Fwww.google.com%2F"
    "&url=%2Fexpress%2Fcreate%2Fanimation"
    "&placement=ax-columns"
    "&locale=en-us"
    "&contentRegion=us"
    "&ecid=64933212606299682780882149920396435823"
    "&%24web_only=true"
    "&_branch_match_id=1519572697194797383"
    "&_branch_referrer=H4sIAAAAAAAAAyWOT2sDIRTEP0287Z%2FoZqsFKaUQcm0PvRbXvOxK1CdPt%2BbUz15LYQ7DwG9mtlJSfh4Gc8UFcjJ0T5hLV2HpTUq9d%2FE%2BwPD5fQ70Xi6ny%2FJCcAMiIL39oQfxeuDnplprvyKuHnqLoQXMYiwQywesDqPeMwPrrnqelBD8yOdx5krNkj%2FJUUp%2BnJTio1DzJE6SC5a8sRAars2js%2Bj3EDPzaI0HDbFrbTt53WbgkQhybs4SmALNmOiCKW2U%2FfyfdXH9Wghrbq%2FfNsIAvw2tiwn3AAAA"
)

AUTOMATION_PROFILE = r"C:\Users\david\AppData\Local\ChromeAutomation\express_profile"
OUTPUT_DIR = "video_output"

pyautogui.FAILSAFE = True  # slam mouse to top-left corner to abort


# JS: click the "browse" sp-link (for="file-input") inside shadow DOM
CLICK_BROWSE_JS = r"""
(() => {
    function deepQuery(root, predicate) {
        const stack = [root];
        while (stack.length) {
            const node = stack.pop();
            if (!node) continue;

            if (node.nodeType === Node.ELEMENT_NODE && predicate(node)) {
                return node;
            }

            if (node.shadowRoot) {
                stack.push(node.shadowRoot);
            }

            const children = node.children;
            if (children && children.length) {
                for (let i = 0; i < children.length; i++) {
                    stack.push(children[i]);
                }
            }
        }
        return null;
    }

    try {
        const browseLink = deepQuery(document, el =>
            el.tagName === "SP-LINK" &&
            el.getAttribute("for") === "file-input"
        );

        if (!browseLink) {
            throw new Error("browse sp-link not found");
        }

        browseLink.click();
        return { ok: true };
    } catch (e) {
        return { ok: false, reason: String(e) };
    }
})();
"""

# JS: click the download button via your full path
CLICK_DOWNLOAD_JS = r"""
(() => {
    try {
        const host1 = document.querySelector("body > x-app-entry-point-wrapper");
        if (!host1 || !host1.shadowRoot) throw new Error("no x-app-entry-point-wrapper");
        const sr1 = host1.shadowRoot;

        const host2 = sr1.querySelector("hz-context-provider-locator > x-app-ui-entry-point");
        if (!host2 || !host2.shadowRoot) throw new Error("no x-app-ui-entry-point");
        const sr2 = host2.shadowRoot;

        const host3 = sr2.querySelector("x-quick-action-tools-view");
        if (!host3 || !host3.shadowRoot) throw new Error("no x-quick-action-tools-view");
        const sr3 = host3.shadowRoot;

        const host4 = sr3.querySelector("quick-action-component");
        if (!host4 || !host4.shadowRoot) throw new Error("no quick-action-component");
        const sr4 = host4.shadowRoot;

        const host5 = sr4.querySelector("qa-app-root > qa-app > qa-animate-from-audio-editor");
        if (!host5 || !host5.shadowRoot) throw new Error("no qa-animate-from-audio-editor");
        const sr5 = host5.shadowRoot;

        const host6 = sr5.querySelector("div > div > qa-workspace > qa-export");
        if (!host6 || !host6.shadowRoot) throw new Error("no qa-export");
        const sr6 = host6.shadowRoot;

        const btn = sr6.querySelector("#downloadExportOption");
        if (!btn) throw new Error("no #downloadExportOption");

        btn.click();
        return { ok: true };
    } catch (e) {
        return { ok: false, reason: String(e) };
    }
})();
"""

async def wait_for_download_button(tab, timeout: int = 300):
    """
    Wait until the download button is enabled:
    sp-button[data-testid="qa-download-export-button"]:not([disabled])
    """
    js = r"""
    (() => {
        const btn = document
          .querySelector("body > x-app-entry-point-wrapper")
          ?.shadowRoot
          ?.querySelector("hz-context-provider-locator > x-app-ui-entry-point")
          ?.shadowRoot
          ?.querySelector("x-quick-action-tools-view")
          ?.shadowRoot
          ?.querySelector("quick-action-component")
          ?.shadowRoot
          ?.querySelector("qa-app-root > qa-app > qa-animate-from-audio-editor")
          ?.shadowRoot
          ?.querySelector("div > div > qa-workspace > qa-export")
          ?.shadowRoot
          ?.querySelector('#downloadExportOption');

        if (!btn) return false;
        return !btn.hasAttribute("disabled");
    })();
    """

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ready = await tab.evaluate(js, return_by_value=True)
        except Exception:
            ready = False

        if ready:
            return True

        await asyncio.sleep(1.5)

    return False


async def wait_for_new_download_file(download_dir: Path, before_files: set, timeout: int = 300) -> Path | None:
    deadline = time.time() + timeout

    while time.time() < deadline:
        current_files = {f for f in os.listdir(download_dir)}
        new_files = current_files - before_files

        if new_files:
            # Ignore temp Chrome files
            candidates = [
                download_dir / name
                for name in new_files
                if not name.endswith(".crdownload")
            ]
            if candidates:
                newest = max(candidates, key=lambda p: p.stat().st_mtime)
                return newest

        await asyncio.sleep(1.5)

    return None


async def main():
    file_path = input("Enter path to the file you want to upload: ").strip()
    if not file_path:
        print("[!] No file path provided, aborting.")
        return

    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        print(f"[!] File does not exist: {file_path}")
        return

    print(f"[+] Will upload: {file_path}")

    os.makedirs(AUTOMATION_PROFILE, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = Path(OUTPUT_DIR).resolve()

    browser = await uc.start(
        headless=False,
        expert=True,
        user_data_dir=AUTOMATION_PROFILE,
        browser_args=["--start-maximized"],
    )

    try:
        tab = await browser.get(TARGET_URL, new_tab=True)
        await tab.set_window_state(state="maximized")

        # Tell Chrome to download into OUTPUT_DIR
        await tab.set_download_path(str(output_path))

        print("[*] Waiting for page to load UI...")
        await asyncio.sleep(10)

        print("[*] Clicking 'browse' link via JS (sp-link for='file-input')...")
        try:
            result = await tab.evaluate(CLICK_BROWSE_JS, return_by_value=True)
            print("Browse click JS result:", result)
        except Exception as e:
            print(f"[!] Failed to click 'browse' via JS: {e}")
            return

        print("[*] Waiting for file dialog, then typing path with PyAutoGUI...")
        await asyncio.sleep(1.5)
        pyautogui.write(file_path, interval=0.01)
        pyautogui.press("enter")
        print("[+] File path sent to OS dialog. Waiting for processing...")

        # Wait for the Download button to become enabled
        print("[*] Waiting for Download button to become enabled...")
        ready = await wait_for_download_button(tab, timeout=300)
        if not ready:
            print("[!] Download button never became enabled within timeout.")
            return

        # Snapshot files before clicking download
        before_files = set(os.listdir(output_path))

        print("[*] Download button enabled. Clicking via JS...")
        click_res = await tab.evaluate(CLICK_DOWNLOAD_JS, return_by_value=True)
        print("Download click JS result:", click_res)

        # Wait for new file to appear in OUTPUT_DIR
        print("[*] Waiting for downloaded file to appear...")
        downloaded = await wait_for_new_download_file(output_path, before_files, timeout=300)
        if not downloaded:
            print("[!] No new downloaded file detected within timeout.")
            return

        clean_name = os.path.splitext(os.path.basename(file_path))[0]
        dest = output_path / f"{clean_name}_video.mp4"
        downloaded.rename(dest)
        print(f"[+] Download saved to: {dest}")

        await asyncio.sleep(10)

    finally:
        try:
            browser.stop()
        except Exception:
            pass


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
