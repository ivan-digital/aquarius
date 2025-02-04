import gradio as gr
from ui.chat_tab import create_chat_tab
from ui.repo_management_tab import create_repo_management_tab
from ui.index_explorer_tab import create_index_explorer_tab

def create_ui():
    """Constructs the full Gradio UI with all tabs."""
    custom_css = "footer { display: none !important; }"

    with gr.Blocks(css=custom_css) as demo:
        gr.Markdown("# Aquarius - Code Assistant")

        # Create individual tabs
        local_repo_dropdown, chatbot, msg, send_btn, indexing_progress = create_chat_tab()
        repo_dropdown, status_textbox = create_repo_management_tab()
        index_table = create_index_explorer_tab(local_repo_dropdown)

        gr.Markdown("© 2025, Aquarius")

    return demo