from flask import Flask, request, jsonify
import os
import logging
from dotenv import load_dotenv
from quiz_solver import QuizSolver
import threading

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXPECTED_SECRET = os.getenv('SECRET')
EMAIL = os.getenv('EMAIL')
AI_API_KEY = os.getenv('AI_INTEGRATIONS_OPENAI_API_KEY')
AI_BASE_URL = os.getenv('AI_INTEGRATIONS_OPENAI_BASE_URL')

if not EXPECTED_SECRET:
    logger.error("SECRET environment variable is not set")
    raise ValueError("SECRET environment variable is required")

if not EMAIL:
    logger.error("EMAIL environment variable is not set")
    raise ValueError("EMAIL environment variable is required")

if not AI_API_KEY or not AI_BASE_URL:
    logger.error("AI Integrations OpenAI environment variables are not set")
    raise ValueError("AI Integrations for OpenAI must be configured")

@app.route('/quiz', methods=['POST'])
def quiz_endpoint():
    try:
        data = request.get_json()
    except Exception as e:
        logger.error(f"Invalid JSON: {e}")
        return jsonify({"error": "Invalid JSON"}), 400
    
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    email = data.get('email')
    secret = data.get('secret')
    url = data.get('url')
    
    if secret != EXPECTED_SECRET:
        logger.warning(f"Invalid secret provided")
        return jsonify({"error": "Invalid secret"}), 403
    
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    
    logger.info(f"Received valid quiz request for URL: {url}")
    
    def solve_quiz_async():
        try:
            solver = QuizSolver(email, secret)
            solver.solve_quiz_chain(url)
        except Exception as e:
            logger.error(f"Error solving quiz: {e}", exc_info=True)
    
    thread = threading.Thread(target=solve_quiz_async)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "accepted",
        "message": "Quiz solving process started"
    }), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
