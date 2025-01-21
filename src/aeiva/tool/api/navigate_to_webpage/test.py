# aeiva/tool/api/navigate_to_webpage/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.navigate_to_webpage.api import navigate_to_webpage

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()
    context = toolkit.context

    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # 1) Open a blank tab
    open_result = await open_browser_tab(context)
    page_id = open_result["result"]["page_id"]
    print("[TEST] open_browser_tab:", open_result)

    # 2) Now navigate to example.com
    nav_result = await navigate_to_webpage(context, page_id, "https://example.com")
    print("[TEST] navigate_to_webpage:", nav_result)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())