# tools/analyze_gui_by_ocr/api.py

from typing import Dict, Any
import cv2
import numpy as np
import pytesseract
import pyautogui
import os
from dotenv import load_dotenv
import time

async def analyze_gui_by_ocr(
    target_text: str = None,
    template_names: list = None,
    template_path: str = None,
    threshold: float = 0.8
) -> Dict[str, Any]:
    """
    Analyze the current GUI to find elements using OCR and template matching.
    If 'target_text' or 'template_names' are provided, they act as filters.

    Args:
        target_text (str): The text to search for in the GUI elements using OCR.
        template_names (list): A list of template image names to search for (without extension).
        template_path (str): The path to the directory containing template images.
        threshold (float): The matching threshold for template matching (default is 0.8).

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Load environment variables from .env file
        load_dotenv()

        # Take a screenshot
        screenshot = pyautogui.screenshot()
        screenshot_np = np.array(screenshot)
        screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

        results = {
            'ocr_matches': [],
            'template_matches': []
        }

        # --- OCR-Based Text Detection ---
        # Perform OCR to extract text data
        data = pytesseract.image_to_data(screenshot_gray, output_type=pytesseract.Output.DICT)

        # Iterate over detected text elements
        for i in range(len(data['text'])):
            text = data['text'][i]

            # Check if text is not None and is a string
            if text is not None and isinstance(text, str):
                stripped_text = text.strip()
                if stripped_text == '':
                    continue

                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                confidence = data['conf'][i]

                ocr_element = {
                    'text': stripped_text,
                    'position': {'x': x, 'y': y, 'width': w, 'height': h},
                    'confidence': float(confidence)
                }

                # Apply filter if target_text is provided
                if target_text is None or target_text.lower() in stripped_text.lower():
                    results['ocr_matches'].append(ocr_element)
            else:
                continue  # Skip if text is None or not a string

        # --- Template Matching ---
        # Set template_path from environment variable if not provided
        template_path = template_path or os.getenv('GUI_TEMPLATES_IMG_PATH')

        # Proceed only if template_path exists
        if template_path and os.path.isdir(template_path):
            # Get list of template images
            all_templates = os.listdir(template_path)
            print("all_templates: ======", all_templates)
            template_files = [f for f in all_templates if f.lower().endswith(
                ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'))]

            # Filter templates based on template_names if provided
            if template_names is not None:
                template_files = [f for f in template_files if os.path.splitext(f)[0] in template_names]

            if not template_files:
                print("No template images found to match.")
            else:
                # For each template image
                for template_file in template_files:
                    template_image_path = os.path.join(template_path, template_file)
                    template = cv2.imread(template_image_path, cv2.IMREAD_GRAYSCALE)
                    if template is None:
                        continue  # Skip if template image could not be read

                    template_name = os.path.splitext(template_file)[0]
                    w, h = template.shape[::-1]

                    # Perform template matching
                    res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
                    loc = np.where(res >= threshold)

                    for pt in zip(*loc[::-1]):
                        match = {
                            'template_name': template_name,
                            'position': {'x': int(pt[0]), 'y': int(pt[1]), 'width': int(w), 'height': int(h)},
                            'confidence': float(res[pt[1], pt[0]])
                        }
                        results['template_matches'].append(match)
        else:
            print("Template path not provided or does not exist.")

        print("Done with analyzing GUI =======")
        return {
            "output": results,
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": f'Error analyzing GUI: {e}',
            "error_code": "ANALYSIS_FAILED"
        }