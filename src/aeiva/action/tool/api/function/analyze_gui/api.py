# tools/analyze_gui/api.py

import sys
import platform


def analyze_gui(target_text: str = None, role: str = None) -> dict:
    """
    Analyze the current GUI to find elements matching the target text and/or role.

    Args:
        target_text (str): The text/name of the UI element to search for.
        role (str): The role/type of the UI element to search for (e.g., 'button', 'textbox').

    Returns:
        dict: A dictionary containing information about matching elements.
    """
    current_platform = platform.system()

    if current_platform == 'Windows':
        return analyze_gui_windows(target_text, role)
    elif current_platform == 'Darwin':
        return analyze_gui_macos(target_text, role)
    elif current_platform == 'Linux':
        return analyze_gui_linux(target_text, role)
    else:
        return {'error': f'Unsupported platform: {current_platform}'}

def analyze_gui_windows(target_text: str = None, role: str = None) -> dict:
    try:
        from pywinauto import Desktop
        elements = []

        # Get all top-level windows
        windows = Desktop(backend="uia").windows()

        for window in windows:
            descendants = window.descendants()

            for elem in descendants:
                name = elem.window_text()
                control_type = elem.element_info.control_type

                if target_text and target_text.lower() not in name.lower():
                    continue
                if role and role.lower() not in control_type.lower():
                    continue

                rect = elem.rectangle()
                elements.append({
                    'name': name,
                    'role': control_type,
                    'position': {
                        'x': rect.left,
                        'y': rect.top,
                        'width': rect.width(),
                        'height': rect.height()
                    }
                })

        return {'elements': elements}
    except Exception as e:
        return {'error': f'Error analyzing GUI on Windows: {e}'}


def analyze_gui_linux(target_text: str = None, role: str = None) -> dict:
    try:
        import pyatspi
        elements = []

        def search_element(element):
            name = element.name or ''
            role_name = element.get_role_name() or ''

            if target_text and target_text.lower() not in name.lower():
                return
            if role and role.lower() not in role_name.lower():
                return

            # Bounding box retrieval can be added here

            elements.append({
                'name': name,
                'role': role_name,
                # 'position': position_info
            })

            for child in element:
                search_element(child)

        desktop = pyatspi.Registry.getDesktop(0)
        for app in desktop:
            search_element(app)

        return {'elements': elements}
    except Exception as e:
        return {'error': f'Error analyzing GUI on Linux: {e}'}


# def analyze_gui_macos(target_text: str = None, role: str = None) -> dict:
#     driver = None  # Initialize driver to None
#     try:
#         from appium import webdriver
#         from appium.webdriver.common.appiumby import AppiumBy
#         from appium.options.mac import Mac2Options  # Import Mac2Options
#         from lxml import etree as ET  # Use lxml.etree for getparent() support

#         # Set up options for Appium using Mac2Options
#         options = Mac2Options()
#         options.platform_name = 'mac'
#         options.automation_name = 'mac2'
#         options.bundle_id = 'com.apple.TextEdit'  # Replace with the bundle ID of the app you want to analyze

#         # Start the Appium driver with options
#         driver = webdriver.Remote('http://localhost:4723', options=options)

#         # Get the page source (UI hierarchy) in XML format
#         page_source = driver.page_source

#         elements = []

#         # Parse the XML
#         root = ET.fromstring(page_source.encode('utf-8'))

#         # Mapping from XCUIElementType to roles
#         role_mapping = {
#             'XCUIElementTypeButton': 'button',
#             'XCUIElementTypeTextField': 'textbox',
#             'XCUIElementTypeStaticText': 'label',
#             'XCUIElementTypeImage': 'image',
#             'XCUIElementTypeWindow': 'window',
#             'XCUIElementTypeMenu': 'menu',
#             'XCUIElementTypeMenuItem': 'menu item',
#             'XCUIElementTypeScrollView': 'scroll view',
#             'XCUIElementTypeTable': 'table',
#             'XCUIElementTypeCell': 'cell',
#             'XCUIElementTypeTextView': 'text view',
#             'XCUIElementTypeCollectionView': 'collection view',
#             'XCUIElementTypeToolbar': 'toolbar',
#             'XCUIElementTypeTabBar': 'tab bar',
#             'XCUIElementTypeSlider': 'slider',
#             'XCUIElementTypeSwitch': 'switch',
#             'XCUIElementTypeAlert': 'alert',
#             'XCUIElementTypeDialog': 'dialog',
#             'XCUIElementTypeGroup': 'group',
#             'XCUIElementTypeList': 'list',
#             'XCUIElementTypeLink': 'link',
#             # Add more as needed
#         }

#         def traverse(element, xpath=''):
#             element_type = element.get('type') or 'unknown'
#             name = element.get('name') or element.get('label') or element.get('identifier') or ''
#             print("element ======", element)
#             role_name = role_mapping.get(element_type, element_type) or 'unknown'

#             # Ensure variables are strings
#             element_type = str(element_type)
#             name = str(name)
#             role_name = str(role_name)

#             # Build XPath for the current element
#             parent = element.getparent()
#             if parent is not None:
#                 siblings = [sib for sib in parent if sib.tag == element.tag]
#                 index = siblings.index(element) + 1  # XPath indices start at 1
#                 current_xpath = f"{xpath}/{element.tag}[{index}]"
#             else:
#                 # Root element
#                 current_xpath = f"/{element.tag}"

#             # Filter based on target_text and role
#             matches = True
#             if target_text and target_text.lower() not in name.lower():
#                 matches = False
#             if role and role.lower() not in role_name.lower():
#                 matches = False

#             if matches:
#                 position_info = {}
#                 try:
#                     # Locate the element using XPath
#                     ui_element = driver.find_element(AppiumBy.XPATH, current_xpath)
#                     location = ui_element.location
#                     size = ui_element.size
#                     position_info = {
#                         'x': location['x'],
#                         'y': location['y'],
#                         'width': size['width'],
#                         'height': size['height']
#                     }
#                 except Exception as e:
#                     # Handle exceptions (element not found, etc.)
#                     pass

#                 element_info = {
#                     'name': name,
#                     'role': role_name,
#                     'position': position_info,
#                 }
#                 elements.append(element_info)

#             # Recursively traverse child elements
#             for child in element:
#                 traverse(child, current_xpath)

#         traverse(root)

#         return {'elements': elements}

#     except Exception as e:
#         return {'error': f'Error analyzing GUI on macOS with Appium: {e}'}
#     finally:
#         if driver:
#             driver.quit()


# def get_element(driver, by, value, timeout=10):
#     """Waits for an element to be available and returns it."""
#     for _ in range(timeout):
#         try:
#             element = driver.find_element(by=by, value=value)
#             return element
#         except Exception:
#             time.sleep(1)
#     raise Exception(f"Element not found: {value}")

# def analyze_gui_macos(target_text: str = None, role: str = None) -> dict:
#     import time
#     from appium import webdriver
#     from appium.webdriver.appium_service import AppiumService
#     from appium.options.mac import Mac2Options
#     from appium.webdriver.common.appiumby import AppiumBy

#     appium_service = AppiumService()
#     appium_service.start()
#     driver = None  # Initialize driver
#     try:
#         options = Mac2Options()
#         options.platform_name = 'mac'
#         options.automation_name = 'mac2'
#         options.bundle_id = 'com.apple.TextEdit'  # Replace with your app's bundle ID

#         driver = webdriver.Remote('http://localhost:4723', options=options)

#         elements = []

#         # Get the page source (UI hierarchy) in XML format
#         page_source = driver.page_source

#         # Parse the XML
#         import xml.etree.ElementTree as ET
#         root = ET.fromstring(page_source)

#         # Mapping from XCUIElementType to roles
#         role_mapping = {
#             # Existing role mappings...
#         }

#         def traverse(element):
#             element_type = element.get('type') or ''
#             name = element.get('name') or element.get('label') or ''
#             role_name = role_mapping.get(element_type, element_type) or ''

#             # Ensure variables are strings
#             element_type = str(element_type)
#             name = str(name)
#             role_name = str(role_name)

#             # Filter based on target_text and role
#             matches = True
#             if target_text and target_text.lower() not in name.lower():
#                 matches = False
#             if role and role.lower() not in role_name.lower():
#                 matches = False

#             if matches:
#                 position_info = {}
#                 try:
#                     # Use 'identifier' or 'label' to locate the element
#                     if name:
#                         ui_element = get_element(driver, AppiumBy.NAME, name)
#                     else:
#                         # Fallback or skip if no unique identifier
#                         return

#                     location = ui_element.location
#                     size = ui_element.size
#                     position_info = {
#                         'x': location['x'],
#                         'y': location['y'],
#                         'width': size['width'],
#                         'height': size['height']
#                     }
#                 except Exception:
#                     # Handle exceptions (element not found, etc.)
#                     pass

#                 element_info = {
#                     'name': name,
#                     'role': role_name,
#                     'position': position_info,
#                 }
#                 elements.append(element_info)

#             # Recursively traverse child elements
#             for child in element:
#                 traverse(child)

#         traverse(root)

#         return {'elements': elements}

#     except Exception as e:
#         return {'error': f'Error analyzing GUI on macOS with Appium: {e}'}
#     finally:
#         if driver:
#             driver.quit()
#         appium_service.stop()
#         time.sleep(2)  # Wait for Mac to exit Automation mode


def analyze_gui_macos(target_text: str = None, role: str = None) -> dict:
    """
    Analyzes the macOS desktop GUI to identify all open applications, files, and UI elements, including positions of
    input boxes, buttons, windows, and other interactive components.
    
    Parameters:
    - target_text: Optional; text to filter elements by name.
    - role: Optional; role to filter elements by type (e.g., 'button', 'input').
    
    Returns:
    - A dictionary containing filtered elements with detailed information, or an error message if analysis fails.
    """

    import time
    import xml.etree.ElementTree as ET
    from appium import webdriver
    from appium.webdriver.appium_service import AppiumService
    from appium.options.mac import Mac2Options
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    # Initialize Appium service to interact with macOS
    appium_service = AppiumService()
    appium_service.start()
    driver = None
    elements = []

    try:
        # Set up Appium options for macOS automation with the Mac2 driver
        options = Mac2Options()
        options.platform_name = 'mac'
        options.automation_name = 'mac2'

        # Connect to Appium server on the default port
        driver = webdriver.Remote('http://localhost:4723', options=options)

        # Mapping UI element types to meaningful roles for easy identification
        role_mapping = {
            0: "Any",
            1: "Other",
            2: "Application",
            3: "Group",
            4: "Window",
            5: "Sheet",
            6: "Drawer",
            7: "Alert",
            8: "Dialog",
            9: "Button",
            10: "RadioButton",
            11: "RadioGroup",
            12: "CheckBox",
            13: "DisclosureTriangle",
            14: "PopUpButton",
            15: "ComboBox",
            16: "MenuButton",
            17: "ToolbarButton",
            18: "Popover",
            19: "Keyboard",
            20: "Key",
            21: "NavigationBar",
            22: "TabBar",
            23: "TabGroup",
            24: "Toolbar",
            25: "StatusBar",
            26: "Table",
            27: "TableRow",
            28: "TableColumn",
            29: "Outline",
            30: "OutlineRow",
            31: "Browser",
            32: "CollectionView",
            33: "Slider",
            34: "PageIndicator",
            35: "ProgressIndicator",
            36: "ActivityIndicator",
            37: "SegmentedControl",
            38: "Picker",
            39: "PickerWheel",
            40: "Switch",
            41: "Toggle",
            42: "Link",
            43: "Image",
            44: "Icon",
            45: "SearchField",
            46: "ScrollView",
            47: "ScrollBar",
            48: "StaticText",
            49: "TextField",
            50: "SecureTextField",
            51: "DatePicker",
            52: "TextView",
            53: "Menu",
            54: "MenuItem",
            55: "MenuBar",
            56: "MenuBarItem",
            57: "Map",
            58: "WebView",
            59: "IncrementArrow",
            60: "DecrementArrow",
            61: "Timeline",
            62: "RatingIndicator",
            63: "ValueIndicator",
            64: "SplitGroup",
            65: "Splitter",
            66: "RelevanceIndicator",
            67: "ColorWell",
            68: "HelpTag",
            69: "Matte",
            70: "DockItem",
            71: "Ruler",
            72: "RulerMarker",
            73: "Grid",
            74: "LevelIndicator",
            75: "Cell",
            76: "LayoutArea",
            77: "LayoutItem",
            78: "Handle",
            79: "Stepper",
            80: "Tab",
            81: "TouchBar",
            82: "StatusItem"
        }

        # Retrieve the desktop-wide UI hierarchy XML
        page_source = driver.page_source
        root = ET.fromstring(page_source)

        # Function to recursively traverse and capture element details
        def traverse(element):
            element_type = element.get('elementType', '')
            name = element.get('name') or element.get('label', '')
            role_name = role_mapping.get(int(element_type), element_type)  # Map to readable role

            # Only proceed if the element has a position
            position_info = {
                'x': int(element.get('x', 0)),
                'y': int(element.get('y', 0)),
                'width': int(element.get('width', 0)),
                'height': int(element.get('height', 0))
            }
            if not any(position_info.values()):  # Skip elements without valid positions
                return

            # Filter based on target_text and role, if provided
            if target_text and target_text.lower() not in name.lower():
                return  # Skip elements not matching the target text
            if role and role.lower() not in role_name.lower():
                return  # Skip elements not matching the specified role

            # Refine role for "Image" types based on specific details
            if role_name == "Image":
                if 'pdf' in name.lower() or 'doc' in name.lower() or 'txt' in name.lower():
                    role_name = "Document"
                elif 'folder' in name.lower():
                    role_name = "Folder"
                else:
                    role_name = "Image File"  # Assumes standalone image if no match

            # Collect element info if name or role are present
            element_info = {
                'name': name,
                'role': role_name,
                'position': position_info,
                'enabled': element.get('enabled', 'false') == 'true',
                'selected': element.get('selected', 'false') == 'true'
            }
            elements.append(element_info)

            # Recursively check child elements to capture nested UI elements
            for child in element:
                traverse(child)

        # Start traversal from the root element of the desktop hierarchy
        traverse(root)
        print('elements: ====== ', elements)
        
        return {'elements': elements}

    except Exception as e:
        # Return error information if an exception occurs
        return {'error': f'Error analyzing GUI on macOS with Appium: {e}'}
    
    finally:
        # Ensure the Appium driver and service are stopped gracefully
        if driver:
            driver.quit()
        appium_service.stop()
        time.sleep(2)  # Wait for macOS to exit Automation mode
