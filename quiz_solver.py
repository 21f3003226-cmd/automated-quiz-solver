import os
import logging
import time
import requests
from playwright.sync_api import sync_playwright
from openai import OpenAI
import json
from data_processor import DataProcessor
from visualizer import Visualizer

logger = logging.getLogger(__name__)

class QuizSolver:
    def __init__(self, email, secret):
        self.email = email
        self.secret = secret
        ai_api_key = os.getenv('AI_INTEGRATIONS_OPENAI_API_KEY')
        ai_base_url = os.getenv('AI_INTEGRATIONS_OPENAI_BASE_URL')
        self.client = OpenAI(
            api_key=ai_api_key,
            base_url=ai_base_url
        )
        self.data_processor = DataProcessor()
        self.visualizer = Visualizer()
        self.start_time = None
        
    def solve_quiz_chain(self, initial_url):
        self.start_time = time.time()
        current_url = initial_url
        max_quizzes = 20
        quiz_count = 0
        
        while current_url and quiz_count < max_quizzes:
            if time.time() - self.start_time > 170:
                logger.warning("Approaching 3-minute time limit, stopping")
                break
                
            quiz_count += 1
            logger.info(f"Solving quiz {quiz_count}: {current_url}")
            
            try:
                next_url = self.solve_single_quiz(current_url)
                if next_url:
                    current_url = next_url
                else:
                    logger.info("Quiz chain completed!")
                    break
            except Exception as e:
                logger.error(f"Error solving quiz {current_url}: {e}", exc_info=True)
                break
    
    def solve_single_quiz(self, quiz_url):
        quiz_content = self.fetch_quiz_page(quiz_url)
        
        if not quiz_content:
            logger.error("Failed to fetch quiz content")
            return None
        
        logger.info(f"Quiz content extracted: {quiz_content[:500]}...")
        
        solution = self.analyze_and_solve(quiz_content, quiz_url)
        
        if solution is None:
            logger.error("Failed to generate solution")
            return None
        
        submit_url = solution.get('submit_url')
        answer = solution.get('answer')
        
        if not submit_url:
            logger.error("No submit URL found in solution")
            return None
        
        logger.info(f"Submitting answer to {submit_url}")
        logger.info(f"Answer: {str(answer)[:200]}")
        
        response = self.submit_answer(submit_url, quiz_url, answer)
        
        if response:
            if response.get('correct'):
                logger.info("Answer was correct!")
                return response.get('url')
            else:
                logger.warning(f"Answer was incorrect: {response.get('reason', 'No reason provided')}")
                if response.get('url'):
                    return response.get('url')
        
        return None
    
    def fetch_quiz_page(self, url):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until='networkidle', timeout=30000)
                time.sleep(2)
                content = page.content()
                browser.close()
                return content
        except Exception as e:
            logger.warning(f"Playwright failed: {e}, falling back to requests")
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"Fallback fetch failed with status {response.status_code}")
                    return None
            except Exception as fallback_error:
                logger.error(f"Both Playwright and fallback fetch failed: {fallback_error}")
                return None
    
    def analyze_and_solve(self, quiz_content, quiz_url):
        system_prompt = """You are an expert data analyst and quiz solver. You receive HTML content from quiz pages and must:
1. Extract the quiz question/task from the HTML
2. Identify any data sources (URLs to download files, APIs to call, etc.)
3. Determine what data processing/analysis is needed
4. Extract the submit URL for the answer - IMPORTANT: construct the full URL from the quiz URL context
5. Return a structured plan to solve the quiz

Focus on finding:
- The question being asked
- Any file downloads (PDFs, CSVs, etc.)  
- API endpoints to call
- Data analysis requirements (sum, filter, aggregate, etc.)
- The submit URL - if you see "/submit" or a relative path, construct the full URL using the quiz URL's domain
- The expected answer format (number, string, boolean, JSON, base64 image)

IMPORTANT: For submit URLs:
- If the HTML says "POST to /submit", construct the full URL from the quiz URL
- If the quiz is at "https://example.com/demo", the submit URL is "https://example.com/submit"
- Never use placeholders like "current-page-url" - always construct the real URL

Return your response as JSON with this structure:
{
  "question": "the question text",
  "data_sources": ["url1", "url2"],
  "analysis_needed": "description of what to do",
  "submit_url": "https://example.com/submit",
  "answer_format": "number|string|boolean|json|base64_image"
}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"The quiz is at URL: {quiz_url}\n\nExtract the quiz task from this HTML and provide a solution plan. IMPORTANT: Construct the submit URL using this quiz URL's domain:\n\n{quiz_content[:8000]}"}
                ],
                max_completion_tokens=8192
            )
            
            analysis = response.choices[0].message.content
            if not analysis:
                logger.error("LLM returned empty response")
                return None
                
            logger.info(f"LLM Analysis: {analysis}")
            
            try:
                plan = json.loads(analysis)
            except:
                start_idx = analysis.find('{')
                end_idx = analysis.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    plan = json.loads(analysis[start_idx:end_idx])
                else:
                    plan = {"error": "Could not parse JSON"}
            
            answer = self.execute_solution_plan(plan, quiz_url)
            
            submit_url = plan.get('submit_url', '')
            if submit_url and ('current-page-url' in submit_url or not submit_url.startswith('http')):
                from urllib.parse import urlparse, urljoin
                if submit_url.startswith('/'):
                    parsed = urlparse(quiz_url)
                    submit_url = f"{parsed.scheme}://{parsed.netloc}{submit_url}"
                elif 'current-page-url' in submit_url:
                    parsed = urlparse(quiz_url)
                    submit_url = submit_url.replace('current-page-url', parsed.netloc)
                    if not submit_url.startswith('http'):
                        submit_url = f"{parsed.scheme}://{submit_url}"
                else:
                    submit_url = urljoin(quiz_url, submit_url)
                logger.info(f"Corrected submit URL to: {submit_url}")
            
            return {
                "submit_url": submit_url,
                "answer": answer
            }
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}", exc_info=True)
            return None
    
    def execute_solution_plan(self, plan, quiz_url):
        try:
            data_sources = plan.get('data_sources', [])
            analysis_needed = plan.get('analysis_needed', '')
            answer_format = plan.get('answer_format', 'string')
            
            downloaded_data = []
            for source in data_sources:
                data = self.data_processor.fetch_and_process(source)
                if data:
                    downloaded_data.append(data)
            
            solve_prompt = f"""Given this task: {plan.get('question', '')}
Analysis needed: {analysis_needed}
Expected answer format: {answer_format}

Downloaded data summary: {str(downloaded_data[:1000]) if downloaded_data else 'No data downloaded'}

Provide the EXACT answer value that should go into the 'answer' field of the submission JSON. 
- For numbers: return just the number (e.g., 42 or 3.14)
- For strings: return just the string (e.g., "example text")  
- For JSON objects/arrays: return the complete object/array
- For boolean: return true or false
Do NOT return the entire submission payload - only the answer value itself."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a precise data analyst. Provide exact, concise answers."},
                    {"role": "user", "content": solve_prompt}
                ],
                max_completion_tokens=8192
            )
            
            answer_content = response.choices[0].message.content
            if not answer_content:
                logger.error("LLM returned empty answer")
                return None
                
            answer_text = answer_content.strip()
            logger.info(f"LLM Answer: {answer_text}")
            
            if answer_format == 'number':
                try:
                    import re
                    numbers = re.findall(r'-?\d+\.?\d*', answer_text)
                    if numbers:
                        return float(numbers[0]) if '.' in numbers[0] else int(numbers[0])
                    logger.warning(f"Could not extract number from: {answer_text}")
                    return answer_text
                except Exception as e:
                    logger.error(f"Error parsing number: {e}")
                    return answer_text
            elif answer_format == 'boolean':
                lower_text = answer_text.lower()
                return 'true' in lower_text or 'yes' in lower_text
            elif answer_format == 'json':
                try:
                    start_idx = answer_text.find('{')
                    end_idx = answer_text.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        return json.loads(answer_text[start_idx:end_idx])
                    logger.warning(f"Could not extract JSON from: {answer_text}")
                    return answer_text
                except Exception as e:
                    logger.error(f"Error parsing JSON: {e}")
                    return answer_text
            elif answer_format == 'base64_image' or 'chart' in answer_format.lower() or 'visualization' in answer_format.lower():
                try:
                    chart_data = self.prepare_chart_data(downloaded_data, answer_text)
                    if chart_data is not None:
                        chart_type = self.determine_chart_type(answer_text)
                        base64_chart = self.visualizer.create_chart(
                            data=chart_data,
                            chart_type=chart_type,
                            title=plan.get('question', 'Chart')[:50]
                        )
                        if base64_chart:
                            logger.info("Successfully generated base64 chart")
                            return base64_chart
                    logger.warning("Could not generate chart, returning text answer")
                    return answer_text
                except Exception as e:
                    logger.error(f"Error generating visualization: {e}")
                    return answer_text
            
            return answer_text
            
        except Exception as e:
            logger.error(f"Error executing solution: {e}", exc_info=True)
            return None
    
    def prepare_chart_data(self, downloaded_data, answer_text):
        try:
            if not downloaded_data:
                return None
            
            import pandas as pd
            
            for data_item in downloaded_data:
                if data_item.get('type') == 'csv':
                    df_dict = data_item.get('dataframe')
                    if df_dict:
                        df = pd.DataFrame(df_dict)
                        if len(df) > 0:
                            return df
                elif data_item.get('type') == 'excel':
                    sheets = data_item.get('sheets', {})
                    if sheets:
                        first_sheet = next(iter(sheets.values()))
                        sheet_data = first_sheet.get('data')
                        if sheet_data:
                            df = pd.DataFrame(sheet_data)
                            if len(df) > 0:
                                return df
                elif data_item.get('type') == 'json':
                    json_data = data_item.get('data')
                    if isinstance(json_data, dict):
                        return json_data
            
            return None
        except Exception as e:
            logger.error(f"Error preparing chart data: {e}")
            return None
    
    def determine_chart_type(self, answer_text):
        lower_text = answer_text.lower()
        if 'pie' in lower_text:
            return 'pie'
        elif 'line' in lower_text or 'trend' in lower_text or 'time' in lower_text:
            return 'line'
        else:
            return 'bar'
    
    def submit_answer(self, submit_url, quiz_url, answer):
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }
        
        try:
            response = requests.post(submit_url, json=payload, timeout=30)
            logger.info(f"Submit response status: {response.status_code}")
            logger.info(f"Submit response: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Submit failed with status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            return None
