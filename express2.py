import asyncio
import nodriver as uc

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


JS_HELPERS = r"""
(() => {
    function deepQuery(root, predicate) {
        const stack = [root];
        while (stack.length) {
            const node = stack.pop();
            if (!node) continue;

            // If it's an element, test it
            if (node.nodeType === Node.ELEMENT_NODE) {
                if (predicate(node)) return node;
            }

            // Traverse shadow root if present
            if (node.shadowRoot) {
                stack.push(node.shadowRoot);
            }

            // Traverse element children
            if (node.children && node.children.length) {
                for (let i = 0; i < node.children.length; i++) {
                    stack.push(node.children[i]);
                }
            } else if (node.childNodes && node.childNodes.length) {
                for (let i = 0; i < node.childNodes.length; i++) {
                    const child = node.childNodes[i];
                    if (child.nodeType === Node.ELEMENT_NODE || child.shadowRoot || (child.childNodes && child.childNodes.length)) {
                        stack.push(child);
                    }
                }
            }
        }
        return null;
    }

    function findEditor() {
        const editor = deepQuery(document, el => el.tagName === "QA-ANIMATE-FROM-AUDIO-EDITOR");
        if (!editor) throw new Error("qa-animate-from-audio-editor not found anywhere");
        if (!editor.shadowRoot) throw new Error("editor has no shadowRoot");
        return editor;
    }

    return { deepQuery, findEditor };
})();
"""


async def main():
    browser = await uc.start(
        headless=False,
        browser_args=["--start-maximized"],
    )

    try:
        tab = await browser.get(TARGET_URL, new_tab=True)
        await tab.set_window_state(state="maximized")

        # Wait for the app to boot; bump if needed
        await asyncio.sleep(20)

        # 1) CLICK THUMBNAIL 317 USING DEEP SEARCH
        js_click_thumb = JS_HELPERS + r"""
        ;(() => {
            try {
                const helpers = (function() {
                    // re-run the helper factory defined above
                    function deepQuery(root, predicate) {
                        const stack = [root];
                        while (stack.length) {
                            const node = stack.pop();
                            if (!node) continue;
                            if (node.nodeType === Node.ELEMENT_NODE && predicate(node)) {
                                return node;
                            }
                            if (node.shadowRoot) stack.push(node.shadowRoot);
                            if (node.children && node.children.length) {
                                for (let i = 0; i < node.children.length; i++) {
                                    stack.push(node.children[i]);
                                }
                            } else if (node.childNodes && node.childNodes.length) {
                                for (let i = 0; i < node.childNodes.length; i++) {
                                    const child = node.childNodes[i];
                                    if (child.nodeType === Node.ELEMENT_NODE || child.shadowRoot || (child.childNodes && child.childNodes.length)) {
                                        stack.push(child);
                                    }
                                }
                            }
                        }
                        return null;
                    }
                    function findEditor() {
                        const editor = deepQuery(document, el => el.tagName === "QA-ANIMATE-FROM-AUDIO-EDITOR");
                        if (!editor) throw new Error("qa-animate-from-audio-editor not found anywhere");
                        if (!editor.shadowRoot) throw new Error("editor has no shadowRoot");
                        return editor;
                    }
                    return { deepQuery, findEditor };
                })();

                const editor = helpers.findEditor();
                const sr5 = editor.shadowRoot;

                const puppets = sr5.querySelector("qa-animate-from-audio-puppets-panel");
                if (!puppets || !puppets.shadowRoot) {
                    throw new Error("qa-animate-from-audio-puppets-panel not found / no shadowRoot");
                }
                const sr6 = puppets.shadowRoot;

                const thumbWrapper = sr6.querySelector("qa-animate-from-audio-thumbnail-grid");
                if (!thumbWrapper || !thumbWrapper.shadowRoot) {
                    throw new Error("qa-animate-from-audio-thumbnail-grid not found / no shadowRoot");
                }
                const sr7 = thumbWrapper.shadowRoot;

                const grid = sr7.querySelector("qa-thumbnail-grid");
                if (!grid || !grid.shadowRoot) {
                    throw new Error("qa-thumbnail-grid not found / no shadowRoot");
                }
                const sr8 = grid.shadowRoot;

                const thumb = sr8.querySelector("qa-thumbnail:nth-child(317)");
                if (!thumb || !thumb.shadowRoot) {
                    throw new Error("qa-thumbnail:nth-child(317) not found / no shadowRoot");
                }
                const thumbSr = thumb.shadowRoot;

                const btn = thumbSr.querySelector("button");
                if (!btn) throw new Error("thumbnail button not found");

                btn.click();
                return { ok: true };
            } catch (e) {
                return { ok: false, reason: String(e) };
            }
        })();
        """

        click_result = await tab.evaluate(js_click_thumb, return_by_value=True)
        print("Thumbnail click result:", click_result)

        await asyncio.sleep(3)

        # 2) SET CHARACTER SCALE TO 42% (value = 0.42)
        js_set_scale = JS_HELPERS + r"""
        ;(() => {
            try {
                const helpers = (function() {
                    function deepQuery(root, predicate) {
                        const stack = [root];
                        while (stack.length) {
                            const node = stack.pop();
                            if (!node) continue;
                            if (node.nodeType === Node.ELEMENT_NODE && predicate(node)) {
                                return node;
                            }
                            if (node.shadowRoot) stack.push(node.shadowRoot);
                            if (node.children && node.children.length) {
                                for (let i = 0; i < node.children.length; i++) {
                                    stack.push(node.children[i]);
                                }
                            } else if (node.childNodes && node.childNodes.length) {
                                for (let i = 0; i < node.childNodes.length; i++) {
                                    const child = node.childNodes[i];
                                    if (child.nodeType === Node.ELEMENT_NODE || child.shadowRoot || (child.childNodes && child.childNodes.length)) {
                                        stack.push(child);
                                    }
                                }
                            }
                        }
                        return null;
                    }
                    function findEditor() {
                        const editor = deepQuery(document, el => el.tagName === "QA-ANIMATE-FROM-AUDIO-EDITOR");
                        if (!editor) throw new Error("qa-animate-from-audio-editor not found anywhere");
                        if (!editor.shadowRoot) throw new Error("editor has no shadowRoot");
                        return editor;
                    }
                    return { deepQuery, findEditor };
                })();

                const editor = helpers.findEditor();
                const sr5 = editor.shadowRoot;

                const puppets = sr5.querySelector("qa-animate-from-audio-puppets-panel");
                if (!puppets || !puppets.shadowRoot) {
                    throw new Error("qa-animate-from-audio-puppets-panel not found / no shadowRoot");
                }
                const sr6 = puppets.shadowRoot;

                const sliderHost = sr6.querySelector("#puppet-scale-slider");
                if (!sliderHost || !sliderHost.shadowRoot) {
                    throw new Error("#puppet-scale-slider not found / no shadowRoot");
                }
                const sliderSr = sliderHost.shadowRoot;

                const input = sliderSr.querySelector('input[aria-label="Character scale"]');
                if (!input) {
                    throw new Error('input[aria-label="Character scale"] not found');
                }

                input.value = "0.42";
                input.dispatchEvent(new Event("input", { bubbles: true }));
                input.dispatchEvent(new Event("change", { bubbles: true }));

                return { ok: true, value: input.value };
            } catch (e) {
                return { ok: false, reason: String(e) };
            }
        })();
        """

        scale_result = await tab.evaluate(js_set_scale, return_by_value=True)
        print("Scale set result:", scale_result)

        await asyncio.sleep(10)

    finally:
        browser.stop()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
