import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import base64
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class Visualizer:
    def __init__(self):
        pass
    
    def create_chart(self, data, chart_type='bar', title='Chart', xlabel='X', ylabel='Y'):
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if chart_type == 'bar':
                if isinstance(data, dict):
                    ax.bar(data.keys(), data.values())
                elif isinstance(data, pd.DataFrame):
                    data.plot(kind='bar', ax=ax)
            elif chart_type == 'line':
                if isinstance(data, dict):
                    ax.plot(list(data.keys()), list(data.values()))
                elif isinstance(data, pd.DataFrame):
                    data.plot(kind='line', ax=ax)
            elif chart_type == 'pie':
                if isinstance(data, dict):
                    ax.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')
            
            ax.set_title(title)
            if chart_type != 'pie':
                ax.set_xlabel(xlabel)
                ax.set_ylabel(ylabel)
            
            plt.tight_layout()
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return None
