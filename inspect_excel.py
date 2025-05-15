import openpyxl
import os
import pandas as pd # Import pandas

EXCEL_FILE_PATH = "data/DRVs_All_populations.xlsx"
MAX_ROWS_TO_PRINT = 5 # Adjusted for brevity as pandas will give more info
COLUMNS_TO_ANALYZE = ['Category', 'Nutrient', 'Target population', 'Age', 'Gender']
VALUE_COLUMNS_TO_ANALYZE = ['AI', 'AR', 'PRI', 'RI', 'UL', 'Safe and adequate intake']

output = []

try:
    # Path resolution logic (simplified for brevity, assuming it worked before)
    if not os.path.exists(EXCEL_FILE_PATH):
        alt_path = os.path.join("app", EXCEL_FILE_PATH)
        if os.path.exists(alt_path):
            EXCEL_FILE_PATH = alt_path
        else:
            # Attempt absolute paths common in Docker if initial paths fail
            abs_path_app = "/app/" + EXCEL_FILE_PATH.replace("app/", "", 1)
            abs_path_home_appuser_app = "/home/appuser/app/" + EXCEL_FILE_PATH.replace("app/", "", 1)

            if EXCEL_FILE_PATH.startswith("data/"): # if it's a relative path from project root
                 abs_path_app = "/app/" + EXCEL_FILE_PATH
                 abs_path_home_appuser_app = "/home/appuser/app/" + EXCEL_FILE_PATH
            
            if os.path.exists(abs_path_app):
                EXCEL_FILE_PATH = abs_path_app
            elif os.path.exists(abs_path_home_appuser_app):
                EXCEL_FILE_PATH = abs_path_home_appuser_app
            else:
                output.append(f"Error: File not found. Checked: {EXCEL_FILE_PATH}, {alt_path}, {abs_path_app}, {abs_path_home_appuser_app}")
                print("\n".join(output))
                exit()
    
    output.append(f"Attempting to open: {EXCEL_FILE_PATH}")
    # Use pandas to read the Excel file
    excel_file = pd.ExcelFile(EXCEL_FILE_PATH)
    output.append(f"Successfully opened with pandas: {EXCEL_FILE_PATH}")
    output.append(f"Sheet names: {excel_file.sheet_names}")

    # Assuming we are interested in the first sheet, as identified previously
    if not excel_file.sheet_names:
        output.append("Error: No sheets found in the Excel file.")
        print("\n".join(output))
        exit()

    sheet_name = excel_file.sheet_names[0]
    output.append(f"\n--- Reading Sheet: {sheet_name} ---")
    df = excel_file.parse(sheet_name)

    output.append("\n--- DataFrame Info ---")
    # Capture df.info() output
    import io
    buffer = io.StringIO()
    df.info(buf=buffer)
    output.append(buffer.getvalue())

    output.append(f"\n--- First {MAX_ROWS_TO_PRINT} rows of the DataFrame ---")
    output.append(df.head(MAX_ROWS_TO_PRINT).to_string())

    for col in COLUMNS_TO_ANALYZE:
        if col in df.columns:
            unique_values = df[col].unique()
            output.append(f"\n--- Unique values in column: {col} ({len(unique_values)} unique) ---")
            # Truncate if too many unique values for cleaner output
            if len(unique_values) > 50:
                 output.append(str(list(unique_values[:50])) + "... (truncated)")
            else:
                 output.append(str(list(unique_values)))

        else:
            output.append(f"\n--- Column not found: {col} ---")
            
    output.append(f"\n--- Exploring value columns (first ~10 unique values if many) ---")
    for col in VALUE_COLUMNS_TO_ANALYZE:
        if col in df.columns:
            # Attempt to convert to numeric, coercing errors to NaN to see non-numeric entries
            numeric_check = pd.to_numeric(df[col], errors='coerce')
            non_numeric_count = numeric_check.isna().sum()
            
            unique_values = df[col].dropna().unique() # Show unique non-NaN raw values
            output.append(f"\n--- Unique values in value column: {col} ({len(unique_values)} unique) ---")
            output.append(f"    (Column contains {non_numeric_count} non-numeric or NaN entries out of {len(df[col])})")
            if len(unique_values) > 20: # Show more for value columns to spot units
                 output.append(str(list(unique_values[:20])) + "... (truncated)")
            else:
                 output.append(str(list(unique_values)))
        else:
            output.append(f"\n--- Value column not found: {col} ---")


except Exception as e:
    output.append(f"An error occurred: {e}")

print("\n".join(output)) 