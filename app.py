import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import random
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

app = Flask(__name__)

# Configure xAI Grok API
API_KEY = os.getenv("XAI_API_KEY")
if API_KEY:
    client = OpenAI(
        api_key=API_KEY,
        base_url="https://api.x.ai/v1",
    )
else:
    client = None

# In-memory data storage
# members: list of dicts {"id": int, "name": str, "availability": list[str]}
members = []
# tasks: list of dicts {"id": int, "name": str, "priority": str, "assignee": str or None}
tasks = []

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Dedicated AI Chatbot Endpoint using xAI Grok API.
    """
    user_message = request.json.get("message")
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    if not client:
        return jsonify({"reply": "System: API Key is not configured. Please add XAI_API_KEY to your .env file."}), 200

    try:
        # Provide context to the AI
        context = "You are a helpful AI assistant for a Home Chore Scheduler app. "
        context += "Help users organize tasks, suggest fair ways to split chores, and give cleaning tips. "
        context += f"Current tasks in system: {[t['name'] for t in tasks]}. "
        context += f"Current household members: {[m['name'] for m in members]}. "
        
        response = client.chat.completions.create(
            model="grok-3", # Using grok-3 as it is the active xAI model
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": user_message},
            ],
        )
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error calling xAI API: {error_msg}", exc_info=True)
        return jsonify({"reply": f"Sorry, I am having trouble connecting to my AI brain right now. Error details: {error_msg}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
