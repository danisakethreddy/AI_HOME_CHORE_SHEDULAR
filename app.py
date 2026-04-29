import os
from flask import Flask, request, jsonify, render_template, Response
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("werkzeug").setLevel(logging.ERROR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)

XAI_BASE_URL = "https://api.x.ai/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _detect_provider(api_key: str) -> str:
    if api_key.startswith("gsk_"):
        return "groq"
    if api_key.startswith("xai-") or api_key.startswith("xai_"):
        return "xai"

    return os.getenv("AI_PROVIDER", "xai").strip().lower() or "xai"


def _get_provider_config() -> tuple[str | None, str | None]:
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_api_key:
        return groq_api_key, "groq"

    xai_api_key = os.getenv("XAI_API_KEY", "").strip()
    if xai_api_key:
        return xai_api_key, _detect_provider(xai_api_key)

    return None, None


def _get_base_url(provider: str) -> str:
    if provider == "groq":
        return GROQ_BASE_URL
    return XAI_BASE_URL


def _create_client_and_provider() -> tuple[OpenAI | None, str | None]:
    api_key, provider = _get_provider_config()
    if not api_key or not provider:
        return None, None

    return OpenAI(
        api_key=api_key,
        base_url=_get_base_url(provider),
    ), provider


def _log_provider_status() -> None:
    api_key, provider = _get_provider_config()
    if provider == "groq":
        logging.info("Using Groq provider via GROQ_API_KEY.")
    elif provider == "xai":
        logging.info("Using xAI provider via XAI_API_KEY.")
    else:
        logging.warning("No AI provider key configured. Chat will use local fallback mode.")


# Initialize provider status logging
_log_provider_status()


def _get_model_candidates(provider: str) -> list[str]:
    configured_model = os.getenv("AI_MODEL", "").strip()

    if provider == "groq":
        fallback_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    else:
        fallback_models = ["grok-3", "grok-2-latest", "grok-2", "grok-beta", "grok-flash"]

    if configured_model:
        return [configured_model] + [model for model in fallback_models if model != configured_model]

    return fallback_models


def _is_permission_or_billing_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    if status_code == 403:
        return True

    error_text = str(error).lower()
    return any(
        keyword in error_text
        for keyword in (
            "403",
            "permission",
            "forbidden",
            "credits",
            "license",
            "billing",
        )
    )


def _is_funding_or_license_error(error: Exception) -> bool:
    error_text = str(error).lower()
    return any(keyword in error_text for keyword in ("credits", "license", "billing"))


def _build_local_chat_reply(user_message: str) -> str:
    message = user_message.strip().lower()
    member_names = [member["name"] for member in members]
    task_names = [task["name"] for task in tasks]

    if not member_names and not task_names:
        return (
            "Hi! I can help you organize chores or give cleaning advice. "
            "Add a few members and tasks, and I can suggest a fair split."
        )

    if any(word in message for word in ("hello", "hi", "hey")):
        return (
            "Hi! I can help you organize chores, split tasks fairly, or suggest cleaning tips. "
            f"Right now I know about members: {', '.join(member_names) or 'none yet'} and tasks: {', '.join(task_names) or 'none yet'}."
        )

    if any(word in message for word in ("schedule", "split", "fair", "assign", "distribution")):
        if member_names and task_names:
            return (
                "For a fair schedule, assign the highest-priority chores first and rotate the rest evenly. "
                f"With your current setup, members are {', '.join(member_names)} and tasks are {', '.join(task_names)}. "
                "Use Auto-Schedule to generate the assignment, then adjust anything manually if needed."
            )
        if member_names:
            return (
                f"You have members {', '.join(member_names)}, but no tasks yet. Add chores first, then I can help split them fairly."
            )
        if task_names:
            return (
                f"You have tasks {', '.join(task_names)}, but no members yet. Add household members first, then I can assign them fairly."
            )

    if any(word in message for word in ("clean", "cleaning", "tip", "advice")):
        return (
            "A practical cleaning flow is: clear clutter first, dust top to bottom, then vacuum or mop last. "
            "For stubborn chores, break them into small timed sessions and assign one person per room."
        )

    if task_names:
        return (
            "I am in local assistant mode right now. Based on your current chores, you can make progress by tackling "
            f"{task_names[0]} first{'' if len(task_names) == 1 else ' and then the remaining tasks one by one'}."
        )

    return (
        "I am in local assistant mode right now. Tell me about your chores or ask for a fair task split, and I will help."
    )


def _build_provider_error_reply(provider: str, user_message: str, error: Exception) -> str:
    if provider == "xai" and _is_permission_or_billing_error(error):
        return (
            "Your xAI key does not have credits or permission right now, so I switched to local chore-assistant mode. "
            "Add credits to xAI or set a working GROQ_API_KEY or XAI_API_KEY."
        )

    if provider == "groq":
        return (
            "Groq is not returning a usable completion for this key right now, so I switched to local chore-assistant mode. "
            "Check that GROQ_API_KEY is active and that the selected model exists on your account."
        )

    return _build_local_chat_reply(user_message)

# In-memory data storage
# members: list of dicts {"id": int, "name": str, "availability": list[str]}
members = []
# tasks: list of dicts {"id": int, "name": str, "priority": str, "assignee": str or None}
tasks = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return Response(status=204)

# --- API Endpoints ---

@app.route('/api/members', methods=['GET', 'POST'])
def handle_members():
    if request.method == 'POST':
        data = request.json
        new_member = {
            "id": len(members) + 1,
            "name": data.get("name"),
            "availability": data.get("availability", [])
        }
        members.append(new_member)
        return jsonify(new_member), 201
    return jsonify(members)

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    if request.method == 'POST':
        data = request.json
        new_task = {
            "id": len(tasks) + 1,
            "name": data.get("name"),
            "priority": data.get("priority", "Medium"),
            "assignee": None
        }
        tasks.append(new_task)
        return jsonify(new_task), 201
    return jsonify(tasks)

@app.route('/api/schedule', methods=['POST'])
def generate_schedule():
    """
    Applies a simple scheduling algorithm for fair distribution.
    Rules:
    1. Distribute High priority tasks first.
    2. Then Medium, then Low.
    3. Try to balance the number of tasks per person.
    """
    if not members:
        return jsonify({"error": "No household members available to assign tasks."}), 400
    if not tasks:
        return jsonify({"error": "No tasks to assign."}), 400

    # Reset assignments
    for task in tasks:
        task["assignee"] = None

    # Sort tasks by priority
    priority_map = {"High": 1, "Medium": 2, "Low": 3}
    sorted_tasks = sorted(tasks, key=lambda x: priority_map.get(x["priority"], 2))

    # Task count per member to ensure fairness
    member_task_count = {m["name"]: 0 for m in members}
    member_names = [m["name"] for m in members]

    for task in sorted_tasks:
        # Find member with the least tasks
        least_assigned_member = min(member_task_count, key=member_task_count.get)
        task["assignee"] = least_assigned_member
        member_task_count[least_assigned_member] += 1

    return jsonify({"tasks": tasks, "distribution": member_task_count})

@app.route('/api/health', methods=['GET'])
def health():
    groq_key = bool(os.getenv("GROQ_API_KEY", "").strip())
    xai_key = bool(os.getenv("XAI_API_KEY", "").strip())
    _, provider = _get_provider_config()

    return jsonify({
        "status": "ok",
        "provider": provider or "none",
        "groq_key_configured": groq_key,
        "xai_key_configured": xai_key,
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Dedicated AI Chatbot Endpoint using xAI Grok API.
    """
    payload = request.get_json(silent=True) or {}
    user_message = payload.get("message")
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    client, provider = _create_client_and_provider()
    if not client:
        return jsonify({"reply": _build_local_chat_reply(user_message), "mode": "local"}), 200

    context = "You are a helpful AI assistant for a Home Chore Scheduler app. "
    context += "Help users organize tasks, suggest fair ways to split chores, and give cleaning tips. "
    context += f"Current tasks in system: {[t['name'] for t in tasks]}. "
    context += f"Current household members: {[m['name'] for m in members]}. "

    try:
        last_error = None
        for model_name in _get_model_candidates(provider or "xai"):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": context},
                        {"role": "user", "content": user_message},
                    ],
                )
                return jsonify({"reply": response.choices[0].message.content, "model": model_name})
            except Exception as model_error:
                last_error = model_error
                if _is_funding_or_license_error(model_error):
                    raise model_error
                logging.warning("AI model %s failed, trying next model: %s", model_name, model_error)

        if last_error is not None:
            raise last_error
    except Exception as e:
        error_code = "ai_request_failed"
        if _is_permission_or_billing_error(e):
            logging.warning("AI provider %s rejected the request: %s", provider or "AI", e)
            error_code = "ai_billing_or_permission"
        else:
            logging.error("Error calling %s API: %s", provider or "AI", e, exc_info=True)

        return jsonify(
            {
                "reply": _build_provider_error_reply(provider or "xai", user_message, e),
                "mode": "local",
                "error": error_code,
            }
        ), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "").strip() == "1"
    print(f"Local app is running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
