import asyncio
import os
import time
import json
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
COOKIES_FILE = "cookies.txt"  # must contain JSON list of cookie dicts compatible with nodriver

# NEW: persistent "do not repeat" list
PROCESSED_LIST_FILE = "processed_files.json"

# Hard-coded Download button coordinates (from get_pos.py)
DOWNLOAD_BTN_X = 1024
DOWNLOAD_BTN_Y = 305

pyautogui.FAILSAFE = True  # slam mouse to top-left corner to abort


def load_processed_list() -> set[str]:
    """
    Load the set of already-processed mp3 basenames from disk.
    Returns an empty set if the file doesn't exist or is invalid.
    """
    path = Path(PROCESSED_LIST_FILE)
    if not path.is_file():
        return set()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(str(x) for x in data)
        return set()
    except Exception as e:
        print(f"[!] Failed to load processed list from {path}: {e}")
        return set()


def save_processed_list(processed: set[str]) -> None:
    """
    Save the set of processed mp3 basenames to disk as JSON.
    """
    path = Path(PROCESSED_LIST_FILE)
    try:
        path.write_text(json.dumps(sorted(processed)), encoding="utf-8")
        print(f"[+] Saved processed list to {path} ({len(processed)} entries).")
    except Exception as e:
        print(f"[!] Failed to save processed list to {path}: {e}")


# JS helper used by "wait until enabled"
FIND_DOWNLOAD_BTN_JS = r"""
function findDownloadButton() {
    function deepSearch(root) {
        const stack = [root];
        while (stack.length) {
            const node = stack.pop();
            if (!node) continue;

            if (node.nodeType === Node.ELEMENT_NODE) {
                const el = /** @type {HTMLElement} */ (node);
                const getAttr = (name) => el.getAttribute ? el.getAttribute(name) : null;

                const dataTestId = getAttr("data-testid") || "";
                const id = el.id || "";
                const tag = (el.tagName || "").toUpperCase();
                const text = (el.textContent || "").toLowerCase();

                let isCandidate = false;

                if (dataTestId === "qa-download-export-button") {
                    isCandidate = true;
                } else if (id === "downloadExportOption") {
                    isCandidate = true;
                } else if (
                    (tag === "SP-BUTTON" || tag === "BUTTON") &&
                    text.includes("download")
                ) {
                    isCandidate = true;
                }

                // try to skip hidden stuff
                if (isCandidate) {
                    const visible = !!(el.offsetParent || el.getClientRects().length);
                    if (visible) {
                        return el;
                    }
                }
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

    return deepSearch(document);
}
"""


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
        return true;
    } catch (e) {
        return false;
    }
})();
"""


# JS: return true when download button exists and is enabled
WAIT_DOWNLOAD_READY_JS = (
    FIND_DOWNLOAD_BTN_JS
    + r"""
(() => {
    try {
        const btn = findDownloadButton();
        if (!btn) return false;
        if (btn.hasAttribute("disabled")) return false;
        if (btn.getAttribute("aria-disabled") === "true") return false;
        return true;
    } catch (e) {
        return false;
    }
})();
"""
)


async def wait_for_download_button(tab, timeout: int = 300) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ready = await tab.evaluate(WAIT_DOWNLOAD_READY_JS, return_by_value=True)
        except Exception:
            ready = False

        if bool(ready):
            return True

        await asyncio.sleep(1.5)

    return False


async def wait_for_new_download_file(
    download_dir: Path, before_files: set, timeout: int = 300
) -> Path | None:
    deadline = time.time() + timeout

    while time.time() < deadline:
        current_files = {f for f in os.listdir(download_dir)}
        new_files = current_files - before_files

        if new_files:
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


async def load_cookies_from_file(browser, cookies_file: str):
    """
    Load cookies from cookies_file (JSON list of cookie dicts) and inject
    them into the Adobe domain so the session is logged in.
    """
    path = Path(cookies_file)
    if not path.is_file():
        print(f"[*] No cookies file found at {path}, continuing without injecting cookies.")
        return

    try:
        raw = path.read_text(encoding="utf-8")
        cookies = json.loads(raw)
    except Exception as e:
        print(f"[!] Failed to read/parse cookies from {path}: {e}")
        return

    try:
        # Open Adobe domain tab to apply cookies
        tab = await browser.get("https://new.express.adobe.com/", new_tab=True)
        await tab.set_cookies(cookies)
        print(f"[+] Injected {len(cookies)} cookies from {path}. Reloading page to apply them...")
        await tab.reload()
        await asyncio.sleep(3)
        # Optional: close this tab; cookies are stored in the profile and shared
        await tab.close()
    except Exception as e:
        print(f"[!] Failed to inject cookies into browser: {e}")


async def process_single_file(browser, file_path: str, output_path: Path) -> bool:
    """
    Process a single mp3 file and download the resulting video.
    Returns True if a video was successfully created and saved, False otherwise.
    """
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        print(f"[!] File does not exist (skipping): {file_path}")
        return False

    print(f"[+] Processing file: {file_path}")

    tab = await browser.get(TARGET_URL, new_tab=True)
    await tab.set_window_state(state="maximized")

    # Focus Chrome window: click center of primary screen
    await asyncio.sleep(3)
    screen_width, screen_height = pyautogui.size()
    print("[*] Clicking center of screen to focus Chrome/Adobe tab...")
    pyautogui.click(screen_width // 2, screen_height // 2)

    # Tell Chrome to download into OUTPUT_DIR
    await tab.set_download_path(str(output_path))

    print("[*] Waiting for page to load UI...")
    await asyncio.sleep(10)

    print("[*] Clicking 'browse' link via JS (sp-link for='file-input')...")
    try:
        browse_ok = await tab.evaluate(CLICK_BROWSE_JS, return_by_value=True)
        print("Browse click JS returned:", browse_ok)
        if not browse_ok:
            print("[!] Failed to click 'browse' via JS. Skipping this file.")
            return False
    except Exception as e:
        print(f"[!] Exception when clicking 'browse' via JS: {e}")
        return False

    print("[*] Waiting for file dialog, then typing path with PyAutoGUI...")
    await asyncio.sleep(1.5)
    pyautogui.write(file_path, interval=0.01)
    pyautogui.press("enter")
    submitted_at = time.time()
    print("[+] File path sent to OS dialog. Waiting for processing...")

    # Wait for the Download button to become enabled (DOM-level ready)
    print("[*] Waiting for Download button to become enabled (DOM)...")
    ready = await wait_for_download_button(tab, timeout=300)
    print("[*] wait_for_download_button =>", ready)
    if not ready:
        print("[!] Download button never became enabled within timeout. Skipping this file.")
        return False

    # Ensure at least ~60 seconds have passed since the file was submitted
    now = time.time()
    elapsed = now - submitted_at
    min_total_delay = 60.0  # seconds since submission
    remaining = max(0.0, min_total_delay - elapsed)

    if remaining > 0:
        print(
            f"[*] Waiting an extra {remaining:.1f} seconds so total time since submission "
            f"is ~{min_total_delay}s..."
        )
        await asyncio.sleep(remaining)
    else:
        # still give a small safety margin even if 60s already elapsed
        print("[*] 60+ seconds already passed since submission; waiting extra 5 seconds for safety...")
        await asyncio.sleep(5)

    # Snapshot files before we start hitting Download
    before_files = set(os.listdir(output_path))

    print(
        f"[*] Repeatedly clicking hard-coded Download button position "
        f"({DOWNLOAD_BTN_X}, {DOWNLOAD_BTN_Y}) (up to 50 attempts)..."
    )
    max_attempts = 50
    downloaded: Path | None = None

    for attempt in range(1, max_attempts + 1):
        print(f"[*] Attempt {attempt}/{max_attempts}: click Download...")
        pyautogui.moveTo(DOWNLOAD_BTN_X, DOWNLOAD_BTN_Y, duration=0.25)
        pyautogui.click()

        print("[*] Checking for new download after click...")
        downloaded = await wait_for_new_download_file(
            output_path,
            before_files,
            timeout=15,  # per-attempt timeout
        )
        if downloaded:
            print("[*] Detected new downloaded file.")
            break

        await asyncio.sleep(2)

    if not downloaded:
        print("[!] Reached maximum attempts without detecting a downloaded file.")
        return False

    clean_name = os.path.splitext(os.path.basename(file_path))[0]
    dest = output_path / f"{clean_name}_video.mp4"
    downloaded.rename(dest)
    print(f"[+] Download saved to: {dest}")

    # Wait 10 seconds after this file is done before moving on to the next
    print("[*] Waiting 10 seconds before moving to the next file...")
    await asyncio.sleep(10)

    return True


async def main():
    folder_path = input("Enter path to the folder containing mp3 files: ").strip()
    if not folder_path:
        print("[!] No folder path provided, aborting.")
        return

    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        print(f"[!] Folder does not exist: {folder_path}")
        return

    # Collect all .mp3 files in the folder
    mp3_files = [
        os.path.join(folder_path, name)
        for name in os.listdir(folder_path)
        if name.lower().endswith(".mp3")
    ]
    mp3_files.sort()

    if not mp3_files:
        print(f"[!] No .mp3 files found in folder: {folder_path}")
        return

    print(f"[+] Found {len(mp3_files)} mp3 file(s) in folder.")

    # Load persistent "do not repeat" list
    processed = load_processed_list()
    if processed:
        print(f"[+] Loaded {len(processed)} already-processed file(s) from {PROCESSED_LIST_FILE}.")

    # Filter out files that were already processed
    to_process = []
    for f in mp3_files:
        base = os.path.basename(f)
        if base in processed:
            print(f"[*] Skipping already-processed file: {base}")
        else:
            to_process.append(f)

    if not to_process:
        print("[*] All mp3 files in this folder are already processed according to the list.")
        return

    print(f"[+] {len(to_process)} mp3 file(s) remaining to process after skipping repeats.")

    os.makedirs(AUTOMATION_PROFILE, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = Path(OUTPUT_DIR).resolve()

    browser = await uc.start(
        headless=False,
        expert=True,
        user_data_dir=AUTOMATION_PROFILE,
        browser_args=["--start-maximized"],
    )

    # NEW: load and inject cookies at the start
    await load_cookies_from_file(browser, COOKIES_FILE)

    try:
        for file_path in to_process:
            base_name = os.path.basename(file_path)

            print("\n==============================")
            print(f"[*] Starting new file: {file_path}")
            print("==============================")
            try:
                success = await process_single_file(browser, file_path, output_path)
            except Exception as e:
                print(f"[!] Unhandled exception while processing {file_path}: {e}")
                success = False

            if success:
                # Add to persistent "do not repeat" list
                processed.add(base_name)
                save_processed_list(processed)
            else:
                print(f"[!] Processing failed or incomplete for {file_path}; not adding to skip list.")
    finally:
        try:
            browser.stop()
        except Exception:
            pass

    try:
        input("Done processing all files. Press Enter to exit...")
    except EOFError:
        pass


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
