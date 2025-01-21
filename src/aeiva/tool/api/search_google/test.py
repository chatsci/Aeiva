# aeiva/tool/api/search_google/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.search_google.api import search_google

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()  # ephemeral; if reCAPTCHA is shown, you may need manual steps
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # 1) Open a new tab (blank)
    open_result = await open_browser_tab(context)
    page_id = open_result["result"]["page_id"]
    print("[TEST] open_browser_tab:", open_result)

    # 2) Attempt "search_google" for "Playwright Python"
    # If cookie banners or reCAPTCHA appear, the ephemeral session won't handle them automatically
    result_search = await search_google(context, page_id, "Playwright Python")
    print("[TEST] search_google:", result_search)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())