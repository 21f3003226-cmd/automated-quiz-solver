# Automated Quiz Solver

An intelligent application that automatically solves data analysis quizzes using LLMs and headless browsing.

## Features

- **API Endpoint**: Receives quiz tasks via POST requests with proper authentication
- **Headless Browsing**: Uses Playwright to render JavaScript-heavy quiz pages
- **LLM-Powered Analysis**: Leverages OpenAI GPT-4o via Replit AI Integrations to interpret instructions and solve tasks (no personal API key required)
- **Multi-Format Data Processing**: Handles PDF, CSV, JSON, Excel, and HTML data sources
- **Data Analysis**: Performs filtering, sorting, aggregation, and statistical calculations
- **Visualization**: Generates charts as base64-encoded images using matplotlib
- **Sequential Quiz Chains**: Automatically follows quiz chains until completion
- **Time-Aware**: Respects 3-minute time limits for quiz completion
- **Secure**: Validates secrets and requires proper environment configuration

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure Environment Variables**:
   
   The application uses **Replit AI Integrations for OpenAI** (no personal API key needed). Configure these secrets in Replit:
   
   - `EMAIL`: Your student email address
   - `SECRET`: Your authentication secret string
   
   The AI Integrations environment variables (`AI_INTEGRATIONS_OPENAI_API_KEY` and `AI_INTEGRATIONS_OPENAI_BASE_URL`) are automatically configured when using the OpenAI integration blueprint.

3. **Run the Application**:
   ```bash
   python app.py
   ```

The server will start on `http://0.0.0.0:5000`

## API Usage

### POST /quiz

Submit a quiz task:

```json
{
  "email": "your-email@example.com",
  "secret": "your-secret-string",
  "url": "https://example.com/quiz-834"
}
```

**Responses**:
- `200 OK`: Quiz solving process started
- `400 Bad Request`: Invalid JSON or missing URL
- `403 Forbidden`: Invalid secret

### GET /health

Check server status:

```bash
curl http://localhost:5000/health
```

## Testing

Test with the demo endpoint:

```bash
curl -X POST http://localhost:5000/quiz \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "secret": "your-secret-string",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
  }'
```

## How It Works

1. **Receive Request**: API endpoint validates credentials and accepts quiz URL
2. **Fetch Quiz**: Headless browser renders the JavaScript quiz page
3. **Extract Task**: LLM analyzes HTML to extract question and data sources
4. **Process Data**: Downloads and parses files (PDF, CSV, JSON, etc.)
5. **Analyze**: LLM determines the solution based on the data
6. **Submit Answer**: Posts answer to the specified endpoint
7. **Chain Quizzes**: If a new URL is provided, repeats the process

## Supported Data Types

- PDF files (with table extraction)
- CSV files
- JSON data
- Excel spreadsheets (.xlsx, .xls)
- HTML tables
- Web scraping

## Answer Formats

The system automatically handles various answer formats:
- Numbers (integers and floats)
- Strings
- Booleans
- JSON objects
- Base64-encoded images

## Architecture

- **app.py**: Flask API server with endpoint routing
- **quiz_solver.py**: Core quiz-solving logic and orchestration
- **data_processor.py**: Data fetching and format conversion
- **visualizer.py**: Chart generation and image encoding

## License

MIT License
