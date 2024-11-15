# toolkit/web_toolkit.py

from aeiva.tool.toolkit.toolkit import Toolkit

class WebToolkit(Toolkit):
    """
    A toolkit for interacting with web pages.
    """

    def __init__(self, config=None):
        super().__init__(
            name="WebToolkit",
            tool_names=[
                "click_webpage_element",
                "crawl",
                "execute_js_script_on_webpage",
                "get_webpage_details",
                "get_webpage_elements",
                "navigate_browser_history",
                "navigate_to_webpage",
                "refresh_webpage",
                "scrape",
                "scroll_webpage",
                "type_text_in_webpage_element",
                "web_search"
            ],
            config=config
        )