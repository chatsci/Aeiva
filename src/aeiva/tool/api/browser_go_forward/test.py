# aeiva/tool/api/browser_go_forward/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.browser_go_forward.api import browser_go_forward

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # 1) Open -> example.com
    open_result = await open_browser_tab(context, "https://example.com")
    page_id = open_result["result"]["page_id"]
    print("[TEST] open_browser_tab:", open_result)

    page = context.pages[page_id]
    # 2) Go to google
    await page.goto("https://www.google.com")
    await page.wait_for_load_state("domcontentloaded")

    # 3) Go back to example.com
    await page.go_back()
    await page.wait_for_load_state("domcontentloaded")

    # 4) Now test forward
    forward_result = await browser_go_forward(context, page_id)
    print("[TEST] browser_go_forward:", forward_result)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())