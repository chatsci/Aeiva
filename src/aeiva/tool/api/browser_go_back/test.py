# aeiva/tool/api/browser_go_back/test.py

import asyncio
import os
import sys

# Make sure Python can find your 'aeiva' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.browser_go_back.api import browser_go_back

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()  # Asynchronously spin up headful browser
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # 1) Open tab -> example.com
    result_open = await open_browser_tab(context, "https://example.com")
    page_id = result_open["result"]["page_id"]
    print("[TEST] open_browser_tab:", result_open)

    # 2) Navigate somewhere else (so we can go back)
    page = context.pages[page_id]
    await page.goto("https://www.google.com")
    await page.wait_for_load_state("domcontentloaded")

    # 3) Now go back
    result_back = await browser_go_back(context, page_id)
    print("[TEST] browser_go_back:", result_back)

    # Wait so we can observe
    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())