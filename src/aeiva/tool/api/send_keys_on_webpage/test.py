# aeiva/tool/api/send_keys_on_webpage/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.send_keys_on_webpage.api import send_keys_on_webpage

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # 1) Open google so we can see a search box
    open_result = await open_browser_tab(context, "https://www.google.com")
    page_id = open_result["result"]["page_id"]
    print("[TEST] open_browser_tab:", open_result)

    # 2) For demonstration, send Tab + Enter keys to the search box
    # Because "typing" letters is often done with .fill or .type, while "send_keys_on_webpage"
    # might be for pressing Enter, Esc, etc.

    keys = ["Tab", "Tab", "Enter"]
    result_send = await send_keys_on_webpage(context, page_id, "input[name='q']", keys)
    print("[TEST] send_keys_on_webpage:", result_send)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())