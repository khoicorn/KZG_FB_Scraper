# import pandas as pd
# import time
# from io import BytesIO
# from datetime import datetime
# # from io import StringIO

# def generate_excel_report(crawler):
#     today = datetime.now().strftime("%Y-%m-%d")
#     time.sleep(3)

#     # Bỏ qua kiểm tra, luôn gọi start() và chờ queue
#     crawler.start()  
        
#     # Chờ đến khi request thoát khỏi queue (đã xử lý xong)
#     while crawler.queue_manager.get_queue_position(crawler.chat_id) is not None:
#         time.sleep(1)

#     crawler.data_to_dataframe()

#     output = BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         crawler.df.to_excel(writer, index=False, sheet_name='Results')

#     output.seek(0)
#     filename = f"{crawler.keyword.replace('.', '-')}_{today}_results.xlsx"
#     return output, filename, crawler.df
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenPyxlImage
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment
from PIL import Image
import requests
import logging
from typing import Optional, Tuple
# from pathlib import Path
import time

class ExcelImageExporter:
    """Enhanced Excel exporter with image support and error handling."""
    
    def __init__(self, 
                 image_size: Tuple[int, int] = (80, 80),
                 row_height: int = 80,
                 image_col_width: int = 18,
                 timeout: int = 10):
        """
        Initialize the Excel exporter.
        
        Args:
            image_size: Tuple of (width, height) for image thumbnails
            row_height: Excel row height for image rows
            image_col_width: Width of the image column
            timeout: Request timeout in seconds
        """
        self.image_size = image_size
        self.row_height = row_height
        self.image_col_width = image_col_width
        self.timeout = timeout
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _download_and_process_image(self, url: str) -> Optional[BytesIO]:
        """
        Download and process an image from URL.
        
        Args:
            url: Image URL to download
            
        Returns:
            BytesIO object containing processed image or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Open and process image
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail
            img.thumbnail(self.image_size, Image.Resampling.LANCZOS)
            
            # Save to buffer
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG", optimize=True)
            img_buffer.seek(0)
            
            return img_buffer
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to download image from {url}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to process image from {url}: {e}")
        
        return None
    
    def _setup_header_styling(self, ws, num_cols: int):
        """Apply styling to header row."""
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for col in range(1, num_cols + 2):  # +1 for image column
            cell = ws.cell(row=1, column=col)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
    
    def _auto_adjust_column_widths(self, ws, df: pd.DataFrame):
        """Auto-adjust column widths based on content."""
        for col_idx, column in enumerate(df.columns, 1):
            max_length = len(str(column))  # Header length
            
            # Check data length
            for value in df[column].astype(str):
                max_length = max(max_length, len(value))
            
            # Set width with reasonable limits
            adjusted_width = min(max(max_length + 2, 10), 50)
            ws.column_dimensions[get_column_letter(col_idx)].width = adjusted_width
    
    def export_to_excel(self, 
                       df: pd.DataFrame, 
                       image_column: str) -> BytesIO:
        """
        Export DataFrame to Excel with images (in-memory only).
        
        Args:
            df: DataFrame to export
            image_column: Column name containing image URLs
            
        Returns:
            BytesIO object containing the Excel file
        """
        if image_column not in df.columns:
            raise ValueError(f"Image column '{image_column}' not found in DataFrame")
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Data with Images"
        
        # Write headers
        for col_idx, col_name in enumerate(df.columns, 1):
            ws.cell(row=1, column=col_idx, value=col_name)
        
        # Add image column header
        image_col_idx = len(df.columns) + 1
        ws.cell(row=1, column=image_col_idx, value="Image")
        
        # Apply header styling
        self._setup_header_styling(ws, len(df.columns))
        
        # Process data rows
        successful_images = 0
        failed_images = 0
        
        for row_idx, (_, row) in enumerate(df.iterrows(), start=2):
            # Write data
            for col_idx, (col_name, value) in enumerate(row.items(), 1):
                # Skip image URL column in output (or include it, based on preference)
                ws.cell(row=row_idx, column=col_idx, value=value)
            
            # Process image
            image_url = row[image_column]
            if pd.notna(image_url) and str(image_url).strip():
                img_buffer = self._download_and_process_image(str(image_url))
                
                if img_buffer:
                    try:
                        openpyxl_img = OpenPyxlImage(img_buffer)
                        
                        # Position image
                        image_col_letter = get_column_letter(image_col_idx)
                        openpyxl_img.anchor = f"{image_col_letter}{row_idx}"
                        
                        ws.add_image(openpyxl_img)
                        
                        # Adjust row height
                        ws.row_dimensions[row_idx].height = self.row_height
                        
                        successful_images += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to add image to Excel for row {row_idx}: {e}")
                        failed_images += 1
                else:
                    failed_images += 1
            else:
                failed_images += 1
                
        # Process hyperlinks in specified column (add this after image processing)
        # Auto-adjust column widths
        self._auto_adjust_column_widths(ws, df)

        # hyperlink_column = "destination_url"  # Change this to your desired column name
        list_urls = ["destination_url", "ad_url", "thumbnail_url"]
        for hyperlink_column in list_urls:
            if hyperlink_column in df.columns:
                for row_idx, (_, row) in enumerate(df.iterrows(), start=2):
                    url = row[hyperlink_column]
                    if pd.notna(url) and str(url).strip():
                        cell = ws.cell(row=row_idx, column=df.columns.get_loc(hyperlink_column)+1)
                        cell.value = "Click here"
                        cell.hyperlink = url
                        cell.font = Font(color="0563C1", underline="single")
                        
            colA_idx = df.columns.get_loc(hyperlink_column) + 1  # +1 for 1-based index
            ws.column_dimensions[get_column_letter(colA_idx)].width = 20  # Your desired width

        # Set image column width
        image_col_letter = get_column_letter(image_col_idx)
        print(image_col_letter)
        ws.column_dimensions[image_col_letter].width = self.image_col_width
        
        
        # Log results
        self.logger.info(f"Export completed: {successful_images} images added, {failed_images} failed")
        
        # Save to memory only
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output

# Usage example and convenience function
def export_dataframe_with_images(df: pd.DataFrame, 
                                image_column: str,
                                **kwargs) -> BytesIO:
    """
    Convenience function to export DataFrame with images to Excel (in-memory).
    
    Args:
        df: DataFrame to export
        image_column: Column name containing image URLs
        **kwargs: Additional arguments for ExcelImageExporter
        
    Returns:
        BytesIO object containing the Excel file
    """
    exporter = ExcelImageExporter(**kwargs)
    return exporter.export_to_excel(df, image_column)

# import pandas as pd

# from io import BytesIO
from datetime import datetime
# from io import StringIO

def generate_excel_report(crawler):
    today = datetime.now().strftime("%Y-%m-%d")
    time.sleep(3)

    # Bỏ qua kiểm tra, luôn gọi start() và chờ queue
    crawler.start()  
        
    # Chờ đến khi request thoát khỏi queue (đã xử lý xong)
    while crawler.queue_manager.get_queue_position(crawler.chat_id) is not None:
        time.sleep(1)

    crawler.data_to_dataframe()

   # Export in-memory only
    excel_buffer = export_dataframe_with_images(
        df=crawler.df,
        image_column='thumbnail_url'
    )
    
    # Or use the class directly for more control (also in-memory only)
    exporter = ExcelImageExporter(
        image_size=(100, 100),
        row_height=100,
        timeout=15
    )
    
    excel_buffer = exporter.export_to_excel(
        df=crawler.df,
        image_column='thumbnail_url'
    )

    # output = BytesIO()
    # with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    #     crawler.df.to_excel(writer, index=False, sheet_name='Results')

    # output.seek(0)
    filename = f"{crawler.keyword.replace('.', '-')}_{today}_results.xlsx"

    return excel_buffer, filename, crawler.df
