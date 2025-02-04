import gradio as gr
from app.repo_management import get_token_placeholder, on_save_token, on_list_repos, on_clone_repo

def create_repo_management_tab():
    """Creates the Repo Management tab UI."""
    with gr.Tab("Repo Management"):
        gr.Markdown("## Manage Your Repos")

        gr.Markdown("### 1) GitHub Token")
        token_save_input = gr.Textbox(
            label="GitHub Token (to save)",
            type="password",
            value=get_token_placeholder()
        )
        save_token_button = gr.Button("Save Token")

        gr.Markdown("### 2) List & Clone Repos from GitHub")
        list_button = gr.Button("List Repos")
        repo_dropdown = gr.Dropdown(
            label="Your GitHub Repos",
            choices=[],
            allow_custom_value=True,
            value=None,
            interactive=True
        )
        clone_button = gr.Button("Clone Selected Repo")
        status_textbox = gr.Markdown()

        save_token_button.click(
            fn=on_save_token,
            inputs=[token_save_input]
        )
        list_button.click(
            fn=on_list_repos,
            outputs=[repo_dropdown, status_textbox]
        )
        clone_button.click(
            fn=on_clone_repo,
            inputs=[repo_dropdown],
            outputs=[status_textbox]
        )

    return repo_dropdown, status_textbox