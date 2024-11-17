# toolkit/file_toolkit/pdf2tables/api.py

from typing import Any, Dict, Optional, List
import os
import pdfplumber
import pandas as pd


def pdf2tables(
    input_file_path: str,
    pages: Optional[List[int]] = None,
    output_format: Optional[str] = "json",
    output_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts tables from a PDF file.
    Optionally, specific pages can be selected, and the tables can be saved in the specified format.

    Args:
        input_file_path (str): The path to the input PDF file.
        pages (List[int], optional): A list of 0-based page numbers to extract tables from.
                                     If None, tables from all pages are extracted.
        output_format (str, optional): The format to save the extracted tables ('json' or 'csv').
                                       Defaults to 'json'.
        output_file_path (str, optional): The path to save the extracted tables.
                                          If None, the tables are returned in the response.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
                        On success, 'output' includes the extracted tables or a success message if saved to a file.
    """
    try:
        # Validate output_format
        if output_format.lower() not in ["json", "csv"]:
            return {
                "output": None,
                "error": f"Invalid output format '{output_format}'. Supported formats are 'json' and 'csv'.",
                "error_code": "VALIDATION_ERROR"
            }

        # Check if the input file exists
        if not os.path.isfile(input_file_path):
            return {
                "output": None,
                "error": f"Input file '{input_file_path}' does not exist.",
                "error_code": "FILE_NOT_FOUND"
            }

        # Initialize list to hold all extracted tables
        all_tables = []

        # Extract tables using pdfplumber
        try:
            with pdfplumber.open(input_file_path) as pdf:
                total_pages = len(pdf.pages)
                if pages:
                    selected_pages = [p for p in pages if 0 <= p < total_pages]
                else:
                    selected_pages = list(range(total_pages))

                for page_number in selected_pages:
                    page = pdf.pages[page_number]
                    tables = page.extract_tables()
                    for table in tables:
                        # Convert table to DataFrame for better structure
                        if len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            all_tables.append(df.to_dict(orient='records'))
                        else:
                            # Handle tables with only headers or empty rows
                            df = pd.DataFrame(table)
                            all_tables.append(df.to_dict(orient='records'))
        except Exception as e:
            return {
                "output": None,
                "error": f"TABLE_EXTRACTION_ERROR: {e}",
                "error_code": "TABLE_EXTRACTION_ERROR"
            }

        if output_file_path:
            # Save the tables to the specified file
            try:
                if output_format.lower() == "json":
                    with open(output_file_path, 'w', encoding='utf-8') as json_file:
                        pd.Series(all_tables).to_json(json_file, orient='records', indent=4)
                elif output_format.lower() == "csv":
                    # Concatenate all tables into a single DataFrame
                    combined_tables = [pd.DataFrame(tbl) for tbl in all_tables if tbl]
                    if combined_tables:
                        combined_df = pd.concat(combined_tables, ignore_index=True)
                        combined_df.to_csv(output_file_path, index=False, encoding='utf-8')
                    else:
                        # Handle case with no tables extracted
                        with open(output_file_path, 'w', encoding='utf-8') as csv_file:
                            csv_file.write("")
                return {
                    "output": {"message": f"Tables extracted and saved to '{output_file_path}' in {output_format.upper()} format."},
                    "error": None,
                    "error_code": "SUCCESS"
                }
            except IOError as io_err:
                return {
                    "output": None,
                    "error": f"IO_ERROR: {io_err}",
                    "error_code": "IO_ERROR"
                }
        else:
            # Return the extracted tables
            return {
                "output": {"tables": all_tables},
                "error": None,
                "error_code": "SUCCESS"
            }

    except Exception as e:
        return {
            "output": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }