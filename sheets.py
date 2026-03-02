import os
import json
import logging
import gspread
from gspread.utils import rowcol_to_a1

def get_client():
    """Initialize and return Google Sheets client using service account."""
    try:
        service_account_info = os.environ.get("GOOGLE_SA_JSON")
        if not service_account_info:
            raise ValueError("GOOGLE_SA_JSON environment variable not set")
            
        sa_dict = json.loads(service_account_info)
        gc = gspread.service_account_from_dict(sa_dict)
        return gc
    except Exception as e:
        logging.error(f"Error creating Google Sheets client: {str(e)}")
        raise Exception(f"Failed to authenticate with Google Sheets: {str(e)}")

def write_dataframe(df, sheet_id, tab_name="Calendar"):
    """
    Write a pandas DataFrame to a Google Sheet.
    
    Args:
        df: pandas DataFrame to write
        sheet_id: Google Sheet ID
        tab_name: Name of the worksheet tab
        
    Returns:
        URL to the created sheet
    """
    try:
        logging.info(f"Writing {len(df)} rows to Google Sheet {sheet_id}")
        logging.debug(f"DataFrame columns: {list(df.columns)}")
        
        # Get Google Sheets client
        try:
            gc = get_client()
            logging.debug("Successfully created Google Sheets client")
        except Exception as client_error:
            logging.error(f"Failed to create Google Sheets client: {str(client_error)}")
            raise Exception(f"Google Sheets authentication failed: {str(client_error)}")
        
        # Open the spreadsheet
        try:
            sh = gc.open_by_key(sheet_id)
            logging.debug(f"Successfully opened spreadsheet: {sh.title}")
        except Exception as open_error:
            logging.error(f"Failed to open spreadsheet {sheet_id}: {str(open_error)}")
            if "not found" in str(open_error).lower():
                raise Exception(f"Spreadsheet not found. Please check the sheet ID: {sheet_id}")
            elif "permission" in str(open_error).lower():
                raise Exception(f"Permission denied. Please share the spreadsheet with your service account.")
            else:
                raise Exception(f"Failed to access spreadsheet: {str(open_error)}")
        
        # Remove existing worksheet if it exists
        try:
            ws = sh.worksheet(tab_name)
            sh.del_worksheet(ws)
            logging.info(f"Deleted existing worksheet: {tab_name}")
        except Exception:
            logging.debug(f"Worksheet {tab_name} doesn't exist, will create new one")
            pass
        
        # Create new worksheet
        try:
            ws = sh.add_worksheet(
                title=tab_name, 
                rows=len(df) + 10, 
                cols=12
            )
            logging.debug(f"Created new worksheet: {tab_name}")
        except Exception as create_error:
            logging.error(f"Failed to create worksheet: {str(create_error)}")
            raise Exception(f"Could not create worksheet '{tab_name}': {str(create_error)}")
        
        # Write headers
        try:
            ws.update(range_name="A1", values=[list(df.columns)])
            logging.debug("Successfully wrote headers")
        except Exception as header_error:
            logging.error(f"Failed to write headers: {str(header_error)}")
            raise Exception(f"Could not write headers: {str(header_error)}")
        
        # Write data
        if len(df) > 0:
            try:
                data_values = df.values.tolist()
                ws.update(range_name="A2", values=data_values)
                logging.debug(f"Successfully wrote {len(data_values)} rows of data")
            except Exception as data_error:
                logging.error(f"Failed to write data: {str(data_error)}")
                raise Exception(f"Could not write data rows: {str(data_error)}")
        
        # Freeze the header row
        try:
            ws.freeze(rows=1, cols=1)
            logging.debug("Successfully froze header row")
        except Exception as freeze_error:
            logging.warning(f"Could not freeze header row: {str(freeze_error)}")
            # Not critical - continue
        
        # Return the sheet URL
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid={ws.id}"
        logging.info(f"Successfully wrote data to Google Sheet: {sheet_url}")
        
        return sheet_url
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error writing to Google Sheets: {error_msg}")
        
        if "authentication" in error_msg.lower() or "credentials" in error_msg.lower():
            raise Exception("Google Sheets authentication failed. Please check your service account setup.")
        elif "permission" in error_msg.lower():
            raise Exception("Permission denied. Make sure the spreadsheet is shared with your service account.")
        elif "not found" in error_msg.lower():
            raise Exception("Spreadsheet not found. Please check the sheet ID and sharing settings.")
        else:
            raise Exception(f"Failed to write to Google Sheets: {error_msg}")
