import os
import logging
import requests
import pandas as pd
import pdfplumber
from io import BytesIO
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.temp_dir = 'temp_downloads'
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def fetch_and_process(self, url):
        try:
            logger.info(f"Fetching data from: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: {response.status_code}")
                return None
            
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'pdf' in content_type or url.endswith('.pdf'):
                return self.process_pdf(response.content)
            elif 'csv' in content_type or url.endswith('.csv'):
                return self.process_csv(response.content)
            elif 'json' in content_type or url.endswith('.json'):
                return self.process_json(response.content)
            elif 'excel' in content_type or url.endswith(('.xlsx', '.xls')):
                return self.process_excel(response.content)
            elif 'html' in content_type:
                return self.process_html(response.content)
            else:
                logger.warning(f"Unknown content type: {content_type}")
                return response.text
                
        except Exception as e:
            logger.error(f"Error fetching/processing {url}: {e}")
            return None
    
    def process_pdf(self, content):
        try:
            pdf_file = BytesIO(content)
            text_data = []
            tables_data = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_data.append(f"Page {page_num}:\n{text}")
                    
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            df = pd.DataFrame(table[1:], columns=table[0] if table else None)
                            tables_data.append({
                                'page': page_num,
                                'table_index': table_idx,
                                'data': df.to_dict()
                            })
            
            return {
                'type': 'pdf',
                'text': '\n\n'.join(text_data),
                'tables': tables_data
            }
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return None
    
    def process_csv(self, content):
        try:
            df = pd.read_csv(BytesIO(content))
            return {
                'type': 'csv',
                'dataframe': df.to_dict(),
                'summary': {
                    'rows': len(df),
                    'columns': list(df.columns),
                    'head': df.head().to_dict()
                }
            }
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            return None
    
    def process_json(self, content):
        try:
            data = json.loads(content)
            return {
                'type': 'json',
                'data': data
            }
        except Exception as e:
            logger.error(f"Error processing JSON: {e}")
            return None
    
    def process_excel(self, content):
        try:
            excel_file = BytesIO(content)
            dfs = pd.read_excel(excel_file, sheet_name=None)
            
            result = {
                'type': 'excel',
                'sheets': {}
            }
            
            for sheet_name, df in dfs.items():
                result['sheets'][sheet_name] = {
                    'data': df.to_dict(),
                    'summary': {
                        'rows': len(df),
                        'columns': list(df.columns)
                    }
                }
            
            return result
        except Exception as e:
            logger.error(f"Error processing Excel: {e}")
            return None
    
    def process_html(self, content):
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            tables = []
            for table in soup.find_all('table'):
                df = pd.read_html(str(table))[0]
                tables.append(df.to_dict())
            
            text = soup.get_text()
            
            return {
                'type': 'html',
                'text': text,
                'tables': tables
            }
        except Exception as e:
            logger.error(f"Error processing HTML: {e}")
            return None
