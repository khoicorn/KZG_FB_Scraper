import pandas as pd
import time
from io import BytesIO
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

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        crawler.df.to_excel(writer, index=False, sheet_name='Results')

    output.seek(0)
    filename = f"{crawler.keyword.replace('.', '-')}_{today}_results.xlsx"
    return output, filename, crawler.df
