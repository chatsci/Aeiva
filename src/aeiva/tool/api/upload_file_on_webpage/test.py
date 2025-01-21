# aeiva/tool/api/upload_file_on_webpage/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.upload_file_on_webpage.api import upload_file_on_webpage

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # We need a page with <input type="file"> for a real test
    # This example is just a placeholder. You can use a local HTML or a known page.

    open_result = await open_browser_tab(context, "https://www.w3schools.com/howto/howto_html_file_upload_button.asp")
    page_id = open_result["result"]["page_id"]
    print("[TEST] open_browser_tab:", open_result)

    # Provide a dummy file
    dummy_file_path = os.path.abspath("some_local_file.txt")  # ensure this file exists

    result_upload = await upload_file_on_webpage(context, page_id, "input[type='file']", dummy_file_path)
    print("[TEST] upload_file_on_webpage:", result_upload)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())