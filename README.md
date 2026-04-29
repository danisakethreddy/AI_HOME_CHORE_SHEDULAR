# Home Chore Scheduler

A Flask-based household chore scheduling app with AI assistant support.

## What it includes

- Flask web application in `app.py`
- Frontend in `templates/index.html` and `static/app.js`
- REST API endpoints for members, tasks, scheduling, and AI chat
- Render deployment config in `render.yaml`

## Requirements

- Python 3.12
- `pip` installed

## Local setup

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Activate it:

   - Windows PowerShell:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - Windows CMD:
     ```cmd
     .\.venv\Scripts\activate.bat
     ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the repo root and add your API keys:

   ```env
   GROQ_API_KEY=your_groq_api_key
   AI_MODEL=llama-3.3-70b-versatile
   ```

   If you want to use xAI instead, add:

   ```env
   XAI_API_KEY=your_xai_api_key
   AI_PROVIDER=xai
   AI_MODEL=grok-3
   ```

5. Run locally:

   ```bash
   python app.py
   ```

6. Open the browser at `http://127.0.0.1:5000`

## Render deployment

The repository is configured for Render using `render.yaml`.

### Deployment steps

1. Push the repository to GitHub (or another Git provider).
2. Create a new Web Service on Render.
3. Connect the service to the repository.
4. Render should detect `render.yaml` and use these settings:
   - `env: python`
   - `pythonVersion: 3.12.0`
   - `buildCommand: pip install -r requirements.txt`
   - `startCommand: gunicorn --bind 0.0.0.0:$PORT app:app`
   - `healthCheckPath: /`
5. Add the environment variables in Render dashboard:
   - `GROQ_API_KEY`
   - `XAI_API_KEY`
6. Deploy the service.

### Notes

- Do not commit `.env` or secrets to version control.
- If you only have one provider key, set only that key and the app will use it.
- If both keys are set, the app prefers `GROQ_API_KEY` first and will use Groq.

## App endpoints

- `/` - front-end homepage
- `/api/members` - GET/POST
- `/api/tasks` - GET/POST
- `/api/schedule` - POST
- `/api/chat` - POST
- `/api/health` - GET (checks API key configuration and provider status)

## Troubleshooting

- If the app fails to start, check that `python 3.12` is used.
- Ensure `GROQ_API_KEY` or `XAI_API_KEY` is configured in Render.
- Check Render logs for startup or runtime errors.
