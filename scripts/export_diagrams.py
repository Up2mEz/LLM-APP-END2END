"""Render project diagram HTML with an existing Playwright browser; install nothing."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(device_scale_factor=3)
        for name in ("architecture", "evaluation"):
            source = ROOT / "docs/diagrams" / f"{name}.html"
            page.goto(source.as_uri(), wait_until="domcontentloaded")
            page.evaluate("document.fonts.ready")
            svg = page.locator("svg").first
            svg.evaluate("""el => {
                const b = el.viewBox.baseVal;
                for (const [axis, size] of [['width', b.width], ['height', b.height]])
                    for (const prefix of ['', 'min-', 'max-'])
                        el.style.setProperty(prefix + axis, size + 'px', 'important');
                for (let a = el.parentElement; a; a = a.parentElement)
                    a.style.setProperty('overflow', 'visible', 'important');
            }""")
            output = source.with_suffix(".png")
            svg.screenshot(path=str(output), omit_background=True)
            print(output.relative_to(ROOT))
        browser.close()


if __name__ == "__main__":
    main()
