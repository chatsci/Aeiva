# tools/analyze_gui/api.py

import cv2
import numpy as np
import pytesseract
import pyautogui
import os
from dotenv import load_dotenv

def analyze_gui(
    target_text: str = None,
    template_names: list = None,
    template_path: str = None,
    threshold: float = 0.8
) -> dict:
    """
    Analyze the current GUI to find elements matching the target text and/or provided templates.

    Args:
        target_text (str): The text to search for in the GUI elements using OCR.
        template_names (list): A list of template image names to search for (without extension).
        template_path (str): The path to the directory containing template images.
        threshold (float): The matching threshold for template matching (default is 0.8).

    Returns:
        dict: A dictionary containing the positions of matching elements from OCR and template matching.
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
        if target_text is not None:
            # Perform OCR to extract text data
            data = pytesseract.image_to_data(screenshot_gray, output_type=pytesseract.Output.DICT)

            # Iterate over detected text elements
            for i in range(len(data['text'])):
                text = data['text'][i]
                if text.strip() == '':
                    continue

                if target_text.lower() in text.lower():
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    confidence = data['conf'][i]
                    results['ocr_matches'].append({
                        'text': text,
                        'position': {'x': x, 'y': y, 'width': w, 'height': h},
                        'confidence': float(confidence)
                    })

        # --- Template Matching ---
        if template_path is None:
            template_path = os.getenv('GUI_TEMPLATES_IMG_PATH')
            if template_path is None:
                return {'error': 'Template path not provided and GUI_TEMPLATES_IMG_PATH not set in .env file.'}

        if not os.path.isdir(template_path):
            return {'error': f'Template path does not exist: {template_path}'}

        # Get list of template images
        all_templates = os.listdir(template_path)
        template_files = [f for f in all_templates if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'))]
        print("template files are ===: ", template_files)

        # Filter templates based on template_names
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

        return results
    except Exception as e:
        return {'error': f'Error analyzing GUI: {e}'}