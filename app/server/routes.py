# app/server/routes.py
import os
import logging
from flask import Flask, request, jsonify
from app.server.chat import ChatService

app = Flask(__name__)
# Enable debug logging
app.logger.setLevel(logging.DEBUG)
chat_service = ChatService()
chat_histories = {}


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    app.logger.debug("Received /chat request JSON: %s", data)
    user_id = data.get("user_id", "default")
    user_input = data.get("message", "")

    assistant_reply, full_history = chat_service.process_message(user_id, user_input)
    response_data = {
        "assistant_reply": assistant_reply,
        "messages": full_history
    }
    app.logger.debug("Sending /chat response JSON: %s", response_data)

    return jsonify(response_data)
