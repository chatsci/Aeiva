from typing import Any, Dict
import mammoth


def docx2html(input_file_path: str, output_file_path: str) -> Dict[str, Any]:
    """
    Converts a DOCX file to HTML format and saves it to a file.

    Args:
        input_file_path (str): The path to the input DOCX file.
        output_file_path (str): The path to save the HTML content.

    Returns:
        Dict[str, Any]: A dictionary containing 'result', 'error', and 'error_code'.
                        On success, 'result' includes a success message.
    """
    try:
        with open(input_file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value
        with open(output_file_path, "w", encoding="utf-8") as html_file:
            html_file.write(html)
        return {
            "result": {"message": f"HTML content saved to '{output_file_path}'."},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "result": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }
        return {
            "result": {"html": html},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "result": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }