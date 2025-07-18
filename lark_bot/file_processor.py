import pandas as pd
import time
from io import BytesIO
from tools import FacebookAdsCrawler
from datetime import datetime
# from io import StringIO

def generate_excel_report(crawler):
    today = datetime.now().strftime("%Y-%m-%d")
    time.sleep(3)

    crawler.crawl()
    crawler.data_to_dataframe()
    data = crawler.df

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False, sheet_name='Results')

    output.seek(0)
    filename = f"{crawler.keyword.replace('.', '-')}_{today}_results.xlsx"
    return output, filename, data
