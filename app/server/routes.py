# app/server/routes.py
import os
from flask import Flask, request, jsonify
from app.server.chat import ChatService

app = Flask(__name__)
chat_service = ChatService()
chat_histories = {}


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_id = data.get("user_id", "default")
    user_input = data.get("message", "")

   # try:
    assistant_reply, full_history = chat_service.process_message(user_id, user_input)

    return jsonify({
            "assistant_reply": assistant_reply,
            "messages": full_history
        })
    # except Exception as e:
    #    log_service.add_log(f"Error in chat route: {e}")
    #    return jsonify({"error": str(e)}), 500
