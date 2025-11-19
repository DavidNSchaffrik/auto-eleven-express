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


async def main():
    browser = await uc.start(
        headless=False,
        browser_args=["--start-maximized"],
    )

    try:
        tab = await browser.get(TARGET_URL, new_tab=True)
        await tab.set_window_state(state="maximized")

        # crude wait for app boot; bump if needed
        await asyncio.sleep(10)

        js_click = r"""
        (() => {
            function require(el, label) {
                if (!el) throw new Error("Not found: " + label);
                return el;
            }
            function requireShadow(el, label) {
                if (!el.shadowRoot) throw new Error("No shadowRoot on: " + label);
                return el.shadowRoot;
            }

            try {
                // 1) outer shell
                const host1 = require(
                    document.querySelector("body > x-app-entry-point-wrapper"),
                    "x-app-entry-point-wrapper"
                );
                const sr1 = requireShadow(host1, "x-app-entry-point-wrapper");

                // 2) app entry
                const host2 = require(
                    sr1.querySelector("hz-context-provider-locator > x-app-ui-entry-point"),
                    "x-app-ui-entry-point"
                );
                const sr2 = requireShadow(host2, "x-app-ui-entry-point");

                // 3) quick action tools view
                const host3 = require(
                    sr2.querySelector("x-quick-action-tools-view"),
                    "x-quick-action-tools-view"
                );
                const sr3 = requireShadow(host3, "x-quick-action-tools-view");

                // 4) quick-action-component
                const host4 = require(
                    sr3.querySelector("quick-action-component"),
                    "quick-action-component"
                );
                const sr4 = requireShadow(host4, "quick-action-component");

                // 5) main editor
                const host5 = require(
                    sr4.querySelector("qa-app-root > qa-app > qa-animate-from-audio-editor"),
                    "qa-animate-from-audio-editor"
                );
                const sr5 = requireShadow(host5, "qa-animate-from-audio-editor");

                // 6) puppets panel (DON'T use random #sp-tab-panel-... ID)
                const host6 = require(
                    sr5.querySelector("qa-animate-from-audio-puppets-panel"),
                    "qa-animate-from-audio-puppets-panel"
                );
                const sr6 = requireShadow(host6, "qa-animate-from-audio-puppets-panel");

                // 7) thumbnail grid wrapper
                const host7 = require(
                    sr6.querySelector("qa-animate-from-audio-thumbnail-grid"),
                    "qa-animate-from-audio-thumbnail-grid"
                );
                const sr7 = requireShadow(host7, "qa-animate-from-audio-thumbnail-grid");

                // 8) inner qa-thumbnail-grid
                const host8 = require(
                    sr7.querySelector("qa-thumbnail-grid"),
                    "qa-thumbnail-grid"
                );
                const sr8 = requireShadow(host8, "qa-thumbnail-grid");

                // 9) the nth thumbnail
                const thumb = require(
                    sr8.querySelector("qa-thumbnail:nth-child(317)"),
                    "qa-thumbnail:nth-child(317)"
                );
                const thumbSr = requireShadow(thumb, "qa-thumbnail:nth-child(317)");

                // 10) button inside thumbnail
                const btn = require(
                    thumbSr.querySelector("button"),
                    "thumbnail button"
                );

                btn.click();

                return { ok: true };
            } catch (e) {
                return { ok: false, reason: String(e) };
            }
        })();
        """

        result = await tab.evaluate(js_click, return_by_value=True)
        print("Click result:", result)

        # keep browser open so you can see the result
        await asyncio.sleep(10)

    finally:
        browser.stop()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
