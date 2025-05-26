import gradio as gr
import requests
import os


class AquariusUI:
    # Default API URL, can be overridden by app.main.py using environment or CLI arg
    CHAT_API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/api/chat")

    @staticmethod
    def _is_processing_message(content):
        """Check if a message is a processing indicator"""
        if not content:
            return False
        return "Processing your request" in content

    @staticmethod
    def add_user_message(message, chat_history):
        # Gradio expects a list of tuples for chatbot history, or a list of dicts with "role" and "content"
        updated_history = list(chat_history)
        updated_history.append({"role": "user", "content": message})
        return updated_history, updated_history, "" # Return updated state, updated UI, and clear input box

    @staticmethod
    def show_processing(chat_history_state):
        """Add a processing message to show the assistant is working"""
        updated_history = list(chat_history_state)
        # Use spinning animation for the processing indicator
        animated_content = """<div class="processing-container">
            <span class="processing-spinner">⚙️</span>
            <span class="processing-text">Processing your request...</span>
        </div>"""
        updated_history.append({"role": "assistant", "content": animated_content})
        return updated_history

    @staticmethod
    def get_assistant_response(chat_history_state): 
        if not chat_history_state or chat_history_state[-1]["role"] != 'user':
            return chat_history_state # Should not happen in normal flow

        # Find the actual user message (skip any processing messages)
        user_actual_message = None
        for msg in reversed(chat_history_state):
            if msg["role"] == "user":
                user_actual_message = msg["content"]
                break
        
        if not user_actual_message:
            return chat_history_state

        try:
            payload = {"user_id": "default", "message": user_actual_message}
            print(f"DEBUG: Making API request to {AquariusUI.CHAT_API_URL} with payload: {payload}")
            response = requests.post(AquariusUI.CHAT_API_URL, json=payload, timeout=360)
            print(f"DEBUG: API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                assistant_reply = data.get("assistant_reply", "")
                print(f"DEBUG: Assistant reply length: {len(assistant_reply) if assistant_reply else 0}")
                print(f"DEBUG: Assistant reply preview: {assistant_reply[:200] if assistant_reply else 'None'}...")
                
                # Clean the assistant reply to remove thinking tags
                cleaned_reply = AquariusUI._clean_assistant_response(assistant_reply)
                print(f"DEBUG: Cleaned reply length: {len(cleaned_reply) if cleaned_reply else 0}")
                print(f"DEBUG: Cleaned reply preview: {cleaned_reply[:200] if cleaned_reply else 'None'}...")
                
                # Remove processing message and add the assistant's response
                updated_history = [msg for msg in chat_history_state if not AquariusUI._is_processing_message(msg.get("content"))]
                print(f"DEBUG: Updated history after removing processing: {len(updated_history)} messages")
                
                if cleaned_reply:
                    updated_history.append({"role": "assistant", "content": cleaned_reply})
                    print(f"DEBUG: Added cleaned assistant reply, final history: {len(updated_history)} messages")
                else:
                    updated_history.append({"role": "assistant", "content": "I received your message but couldn't generate a proper response."})
                
                return updated_history
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(f"DEBUG: API Error: {error_msg}")
                # Create a new list for the updated history, remove processing message
                updated_history = [msg for msg in chat_history_state if not AquariusUI._is_processing_message(msg.get("content"))]
                updated_history.append({"role": "assistant", "content": error_msg})
                return updated_history
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Error: {e}"
            print(f"DEBUG: Request Exception: {error_msg}")
            updated_history = [msg for msg in chat_history_state if not AquariusUI._is_processing_message(msg.get("content"))]
            updated_history.append({"role": "assistant", "content": error_msg})
            return updated_history
        except Exception as e: # Catch other potential errors, e.g., JSONDecodeError
            error_msg = f"General Error: {e}"
            print(f"DEBUG: General Exception: {error_msg}")
            updated_history = [msg for msg in chat_history_state if not AquariusUI._is_processing_message(msg.get("content"))]
            updated_history.append({"role": "assistant", "content": error_msg})
            return updated_history

    @staticmethod
    def _clean_assistant_response(response: str) -> str:
        """Clean assistant response by removing thinking tags"""
        import re
        if not response:
            return response
        
        # Remove content between <think> and </think> tags (including the tags)
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        
        # Clean up any extra whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Multiple newlines to double
        cleaned = cleaned.strip()
        
        return cleaned

    @classmethod
    def final_sync_debug(cls, state):
        """Debug method for final synchronization"""
        print(f"DEBUG: Final sync - state has {len(state)} messages")
        for i, msg in enumerate(state):
            print(f"DEBUG: Message {i}: {msg.get('role')} - {msg.get('content', '')[:100]}...")
        return state, state

    @classmethod
    def ui(cls):
        # CSS for animated processing indicator
        custom_css = """
        footer{display:none !important}
        
        .processing-container {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 0;
        }
        
        .processing-spinner {
            display: inline-block;
            animation: spin 1s linear infinite;
            font-size: 1.2em;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .processing-text {
            color: #666;
            font-style: italic;
        }
        """
        
        with gr.Blocks(css=custom_css) as demo:
            gr.Markdown("## Aquarius")
            with gr.Tabs():
                with gr.Tab("Chat"):
                    chat_history_ui = gr.Chatbot(label="Chat History", type="messages")
                    chat_input = gr.Textbox(lines=1, label="Your Message")
                    chat_state = gr.State([])

                    chat_input.submit(
                        fn=cls.add_user_message,
                        inputs=[chat_input, chat_state],
                        outputs=[chat_state, chat_history_ui, chat_input]
                    ).then(
                        fn=cls.show_processing,
                        inputs=[chat_state],
                        outputs=[chat_history_ui]
                    ).then(
                        fn=cls.get_assistant_response,
                        inputs=[chat_state],
                        outputs=[chat_state]
                    ).then(
                        fn=cls.final_sync_debug,
                        inputs=[chat_state],
                        outputs=[chat_state, chat_history_ui]
                    )
        return demo

    @classmethod
    def launch_ui(cls, server_name="0.0.0.0", server_port=7860):  # Added server_port argument
        demo = cls.ui()
        demo.queue()
        demo.launch(server_name=server_name, server_port=server_port)  # Use server_port
