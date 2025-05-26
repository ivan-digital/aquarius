# app/server/routes.py
import os
import logging
from flask import Flask, request, jsonify, Blueprint, current_app

app = Flask(__name__)
bp = Blueprint('api', __name__)
app.logger.setLevel(logging.DEBUG)

APP_COMPONENT = os.environ.get("APP_COMPONENT")
chat_service = None

logger = logging.getLogger(__name__)

if APP_COMPONENT in ["api", "test", "all"] or APP_COMPONENT is None:
    try:
        from app.server.chat import ChatService

        chat_service = ChatService()
        app.logger.info(f"ChatService initialized successfully for APP_COMPONENT='{APP_COMPONENT}'.")
    except Exception as e:
        app.logger.error(f"Failed to initialize ChatService for APP_COMPONENT='{APP_COMPONENT}': {e}", exc_info=True)
        chat_service = None
else:
    app.logger.info(f"ChatService not initialized for APP_COMPONENT='{APP_COMPONENT}'.")

chat_histories = {}


@bp.route("/chat", methods=["GET", "POST"])
def chat_endpoint():
    """Handles chat requests to the /chat endpoint."""
    logger.info(f"Received request to /chat endpoint, method: {request.method}")
    if request.method == "GET":
        logger.info("GET request to /chat, returning basic info.")
        return jsonify({"message": "Chat endpoint is active. Use POST to send messages."}), 200
    
    if request.method == "POST":
        if chat_service is None:
            app.logger.error(
                f"/chat endpoint called on component '{APP_COMPONENT}' where ChatService is not initialized. "
                "This typically means the UI component's internal server was called directly, "
                "or there's a misconfiguration."
            )
            # Generate dynamic error response
            import asyncio
            try:
                # Create a temporary ChatService just for error response generation
                from app.server.chat import ChatService
                temp_chat_service = ChatService()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                error_message = loop.run_until_complete(
                    temp_chat_service._generate_error_response(
                        "Service unavailable", 
                        f"Component '{APP_COMPONENT}' configuration issue"
                    )
                )
                # Clean up resources
                loop.run_until_complete(temp_chat_service.close_agent_resources())
                loop.close()
            except Exception as gen_error:
                app.logger.error(f"Failed to generate dynamic error response: {gen_error}")
                # Generate timestamp-based dynamic message as last resort
                import time
                timestamp = int(time.time())
                error_message = f"Chat service is currently unavailable. Please try again later. (Error ref: {timestamp})"
            
            return jsonify({"error": error_message}), 503

        data = request.get_json()
        app.logger.debug("Received /chat request JSON: %s", data)
        
        # Check for required fields
        if "user_id" not in data or not data["user_id"]:
            logger.warning(f"POST /chat - Missing user_id. Data: {data}")
            return jsonify({"error": "Missing required field: user_id"}), 400
            
        if "message" not in data or not data["message"]:
            logger.warning(f"POST /chat - Missing message. Data: {data}")
            return jsonify({"error": "Missing required field: message"}), 400
        
        user_id = data["user_id"]
        user_input = data["message"]
        stream = data.get("stream", False)

        logger.info(f"POST /chat - User ID: {user_id}, Message: '{user_input[:50]}...', Stream: {stream}")
        
        try:
            if stream:
                # Stream not implemented yet
                return jsonify({"error": "Streaming not implemented"}), 501
            else:
                logger.info(f"POST /chat - About to call chat_service.process_message")
                assistant_reply, full_history = chat_service.process_message(user_id, user_input)
                logger.info(f"POST /chat - chat_service.process_message completed successfully")
                response_data = {
                    "assistant_reply": assistant_reply,
                    "messages": full_history
                }
                logger.info(f"POST /chat - Successfully processed non-streamed request for User ID: {user_id}")
                logger.debug(f"POST /chat - API Response Data: {response_data}")
                return jsonify(response_data), 200
        except Exception as e:
            logger.error(f"POST /chat - Error processing request for User ID: {user_id}: {e}", exc_info=True)
            # Simple error response
            error_message = "An error occurred processing your request"
            error_response = {
                "success": False,
                "assistant_reply": error_message,
                "messages": [{"role": "user", "content": user_input}, 
                           {"role": "assistant", "content": error_message}]
            }
            return jsonify(error_response), 500

@bp.route("/health", methods=["GET"])
def health_check():
    """Provides a simple health check endpoint for the API."""
    logger.info("Received request to /health endpoint.")
    
    # Generate dynamic health message
    import time
    current_time = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    dynamic_message = f"API is operational as of {current_time}"
    
    response_data = {"status": "healthy", "message": dynamic_message}
    logger.info(f"Returning health status: {response_data}")
    return jsonify(response_data), 200

app.register_blueprint(bp, url_prefix='/api')
