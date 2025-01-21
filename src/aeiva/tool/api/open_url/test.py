# aeiva/tool/api/open_url/test.py

import asyncio
import os
import sys

# Make sure Python can locate your 'aeiva' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_url.api import open_url

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()  # Asynchronously launch browser
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # Example usage: open example.com
    url_to_open = "https://example.com"
    result = await open_url(context, url_to_open)
    print("[TEST] open_url:", result)

    # Wait a few seconds so you can observe the page
    await asyncio.sleep(5)

    # Teardown
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())