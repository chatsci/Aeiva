# aeiva/tool/api/close_browser_tab/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.close_browser_tab.api import close_browser_tab

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

    # 2) Now close that tab
    close_result = await close_browser_tab(context, page_id)
    print("[TEST] close_browser_tab:", close_result)

    await asyncio.sleep(3)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())