# toolkit/file_toolkit/pdf2images/api.py

from typing import Any, Dict, Optional, List
import os
import pdfplumber
from PIL import Image
import io


def pdf2images(
    input_file_path: str,
    pages: Optional[List[int]] = None,
    output_format: Optional[str] = "png",
    output_directory: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts images from a PDF file.
    Optionally, specific pages can be selected, and the images can be saved in the specified format.

    Args:
        input_file_path (str): The path to the input PDF file.
        pages (List[int], optional): A list of 0-based page numbers to extract images from.
                                     If None, images from all pages are extracted.
        output_format (str, optional): The format to save the extracted images ('png' or 'jpeg').
                                       Defaults to 'png'.
        output_directory (str, optional): The directory to save the extracted images.
                                          If None, images are returned in the response.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
                        On success, 'output' includes the extracted images or a success message if saved to files.
    """
    try:
        # Validate output_format
        if output_format.lower() not in ["png", "jpeg"]:
            return {
                "output": None,
                "error": f"Invalid output format '{output_format}'. Supported formats are 'png' and 'jpeg'.",
                "error_code": "VALIDATION_ERROR"
            }

        # Check if the input file exists
        if not os.path.isfile(input_file_path):
            return {
                "output": None,
                "error": f"Input file '{input_file_path}' does not exist.",
                "error_code": "FILE_NOT_FOUND"
            }

        # Initialize list to hold all extracted images
        all_images = []

        # Extract images using pdfplumber
        try:
            with pdfplumber.open(input_file_path) as pdf:
                total_pages = len(pdf.pages)
                if pages:
                    selected_pages = [p for p in pages if 0 <= p < total_pages]
                else:
                    selected_pages = list(range(total_pages))

                image_counter = 1
                for page_number in selected_pages:
                    page = pdf.pages[page_number]
                    images = page.images  # List of image dictionaries
                    for img in images:
                        # Extract image bytes
                        x0, y0, x1, y1 = img['x0'], img['top'], img['x1'], img['bottom']
                        try:
                            # Crop the image from the page
                            cropped_image = page.crop((x0, y0, x1, y1)).to_image()
                            img_bytes = cropped_image.original
                            image = Image.open(io.BytesIO(img_bytes))

                            if output_directory:
                                # Ensure the output directory exists
                                os.makedirs(output_directory, exist_ok=True)
                                image_filename = f"image_{page_number + 1}_{image_counter}.{output_format.lower()}"
                                image_path = os.path.join(output_directory, image_filename)
                                image.save(image_path, format=output_format.upper())
                                image_counter += 1
                            else:
                                # Convert image to bytes
                                img_buffer = io.BytesIO()
                                image.save(img_buffer, format=output_format.upper())
                                img_bytes = img_buffer.getvalue()
                                all_images.append({
                                    "page": page_number,
                                    "image": img_bytes.decode('latin1')  # Encode bytes to string
                                })
                        except Exception as img_exc:
                            return {
                                "output": None,
                                "error": f"IMAGE_EXTRACTION_ERROR: Failed to extract image on page {page_number + 1}: {img_exc}",
                                "error_code": "IMAGE_EXTRACTION_ERROR"
                            }
        except Exception as e:
            return {
                "output": None,
                "error": f"IO_ERROR: {e}",
                "error_code": "IO_ERROR"
            }

        if output_directory:
            # Return success message
            return {
                "output": {"message": f"Images extracted and saved to '{output_directory}' in {output_format.upper()} format."},
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            # Return the extracted images
            return {
                "output": {"images": all_images},
                "error": None,
                "error_code": "SUCCESS"
            }

    except Exception as e:
        return {
            "output": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }