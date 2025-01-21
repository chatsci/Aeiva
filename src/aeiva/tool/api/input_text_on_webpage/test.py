# aeiva/tool/api/input_text_on_webpage/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.input_text_on_webpage.api import input_text_on_webpage

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # 1) Open google
    open_result = await open_browser_tab(context, "https://www.google.com")
    page_id = open_result["result"]["page_id"]
    print("[TEST] open_browser_tab:", open_result)

    # 2) Input text into the "q" selector (Google search box).
    # If a cookie overlay or reCAPTCHA appears, you may need manual handling or persistent approach
    result_input = await input_text_on_webpage(context, page_id, "input[name='q']", "Hello from AEIVA")
    print("[TEST] input_text_on_webpage:", result_input)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())