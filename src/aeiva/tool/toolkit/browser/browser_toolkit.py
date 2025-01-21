# aeiva/tool/toolkit/browser/browser_toolkit.py

import logging
import asyncio
import os
from typing import Dict, Any, Optional, List

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from aeiva.tool.toolkit.toolkit import Toolkit
from aeiva.tool.toolkit.toolkit_config import ToolkitConfig  # or remove if unused

logger = logging.getLogger(__name__)

class BrowserToolkit(Toolkit):
    """
    A specialized Toolkit for browser-based APIs. 
    Now supports an async "asetup"/"ateardown" so that we fully await 
    Playwright startup/shutdown (fixing the 'No BrowserContext found!' race condition).
    """

    def __init__(self, config: Optional[ToolkitConfig] = None):
        super().__init__(
            name="BrowserToolkit",
            tool_names=[
                # Register all your browser APIs here:
                "browser_go_back",
                "browser_go_forward",
                "click_webpage_element",
                "close_browser_tab",
                "extract_webpage_content",
                "input_text_on_webpage",
                "navigate_to_webpage",
                "open_browser_tab",
                "open_url",
                "scroll_webpage",
                "search_google",
                "select_dropdown_on_webpage",
                "send_keys_on_webpage",
                "switch_browser_tab",
                "upload_file_on_webpage",
            ],
            config=config
        )
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: List[Page] = []
        self.current_page_index: int = 0
        self.running = False

    # -----------------------------------------------------------
    # Overridden parent methods
    # -----------------------------------------------------------
    def init_shared_resources(self):
        """
        Overridden to do NOTHING. The parent's 'setup()' calls this method.
        We skip it so that no background tasks are spawned. 
        We'll spawn the browser in 'asetup()' below.
        """
        pass

    def teardown_shared_resources(self):
        """
        Overridden to do NOTHING. We'll close the browser in 'ateardown()'.
        """
        pass

    # -----------------------------------------------------------
    # Additional async setup/teardown
    # -----------------------------------------------------------
    async def asetup(self, headless: bool = False):
        """
        Asynchronous setup. 
        1) Calls the parent's 'setup()' for Pydantic loading, etc. 
           (which won't start the browser now). 
        2) Actually awaits the _start_browser(...) so the context is guaranteed ready.
        """
        logger.info("[BrowserToolkit] Performing async setup (asetup).")
        super().setup()  # do parent logic (load tool schemas, pydantic models, etc.)
        await self._start_browser(headless=headless)

    async def ateardown(self):
        """
        Asynchronous teardown.
        1) Closes the browser. 
        2) Calls parent's 'teardown()' to clean up any parent's resources.
        """
        logger.info("[BrowserToolkit] Performing async teardown (ateardown).")
        await self._stop_browser()
        super().teardown()

    # -----------------------------------------------------------
    # Private async methods to start/stop the browser
    # -----------------------------------------------------------
    async def _start_browser(self, headless: bool):
        if self.running:
            logger.info("[BrowserToolkit] Browser is already running.")
            return

        logger.info(f"[BrowserToolkit] Starting Playwright (headless={headless})...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context()

        # Create an initial page
        page = await self.context.new_page()
        self.pages.append(page)
        self.current_page_index = 0
        self.running = True
        logger.info("[BrowserToolkit] Browser started successfully (async).")

    async def _stop_browser(self):
        if not self.running:
            return

        logger.info("[BrowserToolkit] Stopping browser (async)...")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.playwright = None
        self.browser = None
        self.context = None
        self.pages.clear()
        self.current_page_index = 0
        self.running = False
        logger.info("[BrowserToolkit] Browser stopped (async).")

    # -----------------------------------------------------------
    # Utility methods
    # -----------------------------------------------------------
    def get_current_page(self) -> Page:
        if not self.running or not self.pages:
            raise RuntimeError("No browser/page available. Is the browser running?")
        return self.pages[self.current_page_index]

    def get_page_by_id(self, page_id: int) -> Page:
        if page_id < 0 or page_id >= len(self.pages):
            raise ValueError(f"Invalid page ID: {page_id}")
        return self.pages[page_id]

    # Example code for updating DOM state using buildDomTree.js
    async def update_dom_state(self, page: Page, highlight: bool = True) -> Dict[int, str]:
        script_path = os.path.join(os.path.dirname(__file__), "buildDomTree.js")
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()

        dom_data = await page.evaluate(code, highlight)
        highlight_map: Dict[int, str] = {}

        def traverse(node: Dict[str, Any]):
            hi = node.get("highlightIndex")
            if hi is not None:
                xp = node.get("xpath", "")
                highlight_map[hi] = xp
            for child in node.get("children", []):
                if isinstance(child, dict):
                    traverse(child)

        if isinstance(dom_data, dict):
            traverse(dom_data)

        logger.info("[BrowserToolkit] update_dom_state: found %d highlighted elements", len(highlight_map))
        return highlight_map

    # -----------------------------------------------------------
    # Overridden execute methods, injecting 'context' or 'page'
    # -----------------------------------------------------------
    async def aexecute(self, api_name: str, params: Dict[str, Any]) -> Any:
        """
        Overridden to:
          1) validate params with parent's logic
          2) inject self.context or page object
          3) call the API function
        """
        tool = self.tools.get(api_name)
        if not tool:
            raise ValueError(f"Tool '{api_name}' not found in toolkit '{self.toolkit_name}'.")

        # Validate input params
        param_model, result_model = self.tool_models.get(api_name, (None, None))
        if param_model:
            param_instance = param_model(**params)
            param_instance = self.perform_security_checks(param_instance)
            param_dict = param_instance.dict()
        else:
            param_dict = params

        # Insert the context
        param_dict["context"] = self.context

        # If the API expects a page_id -> page
        if "page_id" in param_dict:
            page_id = param_dict["page_id"]
            page = self.get_page_by_id(page_id)
            param_dict["page"] = page

        raw_result = await tool.aexecute(param_dict)

        if result_model:
            validated = result_model(**raw_result)
            return validated.dict()
        else:
            return raw_result

    def execute(self, api_name: str, params: Dict[str, Any]) -> Any:
        """
        Synchronous wrapper calling aexecute. 
        If your tests remain async, you'll typically call aexecute directly 
        or do 'asyncio.run(...)' in your test code.
        """
        return asyncio.run(self.aexecute(api_name, params))

    async def asetup_persistent(self, user_data_dir: str, headless: bool = False):
        """
        Async setup but uses a persistent context so reCAPTCHA or cookies 
        can be solved once and reused in subsequent sessions.

        Usage:
           toolkit = BrowserToolkit()
           await toolkit.asetup_persistent("my_profile_dir", headless=False)
           # now self.context is a persistent context
        """
        logger.info("[BrowserToolkit] Performing async PERSISTENT setup (asetup_persistent).")
        super().setup()  # parent's logic (load Pydantic models, etc.)

        if self.running:
            logger.info("[BrowserToolkit] Already running.")
            return

        # Start Playwright
        self.playwright = await async_playwright().start()
        logger.info(f"[BrowserToolkit] Launching persistent context at {user_data_dir}, headless={headless}")

        # Launch persistent
        # If user_data_dir doesn't exist, it will be created
        # This is only valid for Chromium
        chromium = self.playwright.chromium
        context = await chromium.launch_persistent_context(
            user_data_dir=os.path.abspath(user_data_dir),
            headless=headless
        )

        self.browser = context.browser  # store the underlying browser if needed
        self.context = context

        # Create an initial page if none exist
        if len(context.pages) == 0:
            page = await context.new_page()
            self.pages.append(page)
            self.current_page_index = 0
        else:
            # If we already have pages open in the persistent profile,
            # let's store them in self.pages
            self.pages.extend(context.pages)
            self.current_page_index = 0

        self.running = True
        logger.info("[BrowserToolkit] Browser started successfully (persistent).")

    async def _stop_browser(self):
        """
        Overridden to close the persistent context properly.
        """
        if not self.running:
            return

        logger.info("[BrowserToolkit] Stopping browser (async)...")
        if self.context:
            await self.context.close()  # persist cookies, localStorage, etc. to disk
        if self.playwright:
            await self.playwright.stop()

        self.playwright = None
        self.browser = None
        self.context = None
        self.pages.clear()
        self.current_page_index = 0
        self.running = False
        logger.info("[BrowserToolkit] Browser stopped (async).")