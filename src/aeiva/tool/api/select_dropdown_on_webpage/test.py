# aeiva/tool/api/select_dropdown_on_webpage/test.py

import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from aeiva.tool.toolkit.browser.browser_toolkit import BrowserToolkit
from aeiva.tool.api.open_browser_tab.api import open_browser_tab
from aeiva.tool.api.select_dropdown_on_webpage.api import select_dropdown_on_webpage

async def main():
    toolkit = BrowserToolkit()
    await toolkit.asetup()
    context = toolkit.context
    if not context:
        print("[TEST] No BrowserContext found!")
        return

    # For a real dropdown, let's open a known page with a <select>.
    # W3Schools example is inside an iframe, so it's a bit tricky. 
    # Alternatively, you can create your own local test page with a straightforward <select>.

    open_result = await open_browser_tab(context, "https://www.w3schools.com/tags/tryit.asp?filename=tryhtml_select")
    page_id = open_result["result"]["page_id"]
    print("[TEST] open_browser_tab:", open_result)

    # We'll attempt to select 'volvo' from the <select> in the iframe
    page = context.pages[page_id]

    # Find the correct iframe
    frames = page.frames
    dropdown_iframe = None
    for fr in frames:
        if "tryhtml_select" in (fr.url or ""):
            dropdown_iframe = fr
            break

    if not dropdown_iframe:
        print("[TEST] Could not find the correct iframe for the W3Schools dropdown example.")
    else:
        try:
            result_select = await select_dropdown_on_webpage(
                context,
                page_id,  # not used in the real code if we rely on the direct frame call
                "#cars",  # the <select> in the example
                "volvo"
            )
            print("[TEST] select_dropdown_on_webpage:", result_select)

            # Actually, in the real script, `select_dropdown_on_webpage` tries to do
            # page.select_option(selector, value=value). Because we're in an iframe,
            # we might need to adapt the code. For demonstration, let's just do:
            await dropdown_iframe.select_option("#cars", value="volvo")

        except Exception as e:
            print("[TEST] Error selecting dropdown:", e)

    await asyncio.sleep(5)
    await toolkit.ateardown()

if __name__ == "__main__":
    asyncio.run(main())