# aeiva/tool/api/switch_browser_tab/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.switch_browser_tab.api import switch_browser_tab

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # 1) Open tab #0 -> example.com
    r1 = await open_browser_tab(context, "https://example.com")
    page_id1 = r1["result"]["page_id"]
    print("[TEST] open_browser_tab #0:", r1)

    # 2) Open tab #1 -> google.com
    r2 = await open_browser_tab(context, "https://google.com")
    page_id2 = r2["result"]["page_id"]
    print("[TEST] open_browser_tab #1:", r2)

    # 3) Switch to tab #0
    switch_result = await switch_browser_tab(context, page_id1)
    print("[TEST] switch_browser_tab -> 0:", switch_result)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())