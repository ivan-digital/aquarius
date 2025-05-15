import gradio as gr
import requests


class AquariusUI:
    CHAT_API_URL = "http://127.0.0.1:5000/chat"

    @staticmethod
    def add_user_message(message, chat_history):
        chat_history.append({"role": "user", "content": message})
        return chat_history, message

    @staticmethod
    def get_assistant_response(message, chat_history):
        try:
            payload = {"user_id": "default", "message": message}
            response = requests.post(AquariusUI.CHAT_API_URL, json=payload, timeout=360)
            if response.status_code == 200:
                data = response.json()
                full_history = data.get("messages", [])
                chat_history.clear()
                chat_history.extend(full_history)

                return chat_history, ""
            else:
                error_msg = f"Error: {response.text}"
                chat_history.append({"role": "assistant", "content": error_msg})
                return chat_history, ""
        except Exception as e:
            error_msg = f"Error: {e}"
            chat_history.append({"role": "assistant", "content": error_msg})
            return chat_history, ""

    @classmethod
    def ui(cls):
        with gr.Blocks(css="footer{display:none !important}") as demo:
            gr.Markdown("## Aquarius")
            with gr.Tabs():
                with gr.Tab("Chat"):
                    chat_history_ui = gr.Chatbot(label="Chat History", type="messages")
                    chat_input = gr.Textbox(lines=1, label="Your Message")
                    chat_state = gr.State([])

                    chat_input.submit(
                        fn=cls.add_user_message,
                        inputs=[chat_input, chat_state],
                        outputs=[chat_history_ui, chat_input]
                    ).then(
                        fn=cls.get_assistant_response,
                        inputs=[chat_input, chat_state],
                        outputs=[chat_history_ui, chat_input]
                    )
        return demo

    @classmethod
    def launch_ui(cls):
        demo = cls.ui()
        demo.queue()
        demo.launch(server_name="0.0.0.0")
