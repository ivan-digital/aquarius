import gradio as gr
import os

from app.repo_management import on_list_local_repos
from services.pipeline.index_pipeline import IndexPipeline
from services.llm_client import LlmClient
from services.pipeline.build_service import BuildService

llm_client = LlmClient()
pipeline = IndexPipeline(llm_client)
build_service = BuildService(llm_client)

def user_add_msg(user_input, history):
    """
    Immediately adds the user's message to the chat history.
    """
    if not history:
        history = []
    history.append({"role": "user", "content": user_input})
    return history, ""

def assistant_add_msg(history, repo_selection):
    """
    Calls LLM to generate the assistant's reply, then appends it.
    """
    messages_for_llm = []
    for msg in history:
        messages_for_llm.append(
            {"role": msg["role"], "content": msg["content"]}
        )

    llm_response = llm_client.generate(messages_for_llm)
    assistant_response = llm_response.get("response", "<no response>")
    assistant_thoughts = llm_response.get("thoughts", "<no thoughts>")

    assistant_message = (
        f"**Thoughts**:\n{assistant_thoughts}\n\n"
        f"{assistant_response}"
    )
    history.append({"role": "assistant", "content": assistant_message})
    return history


def detect_build_system(selected_local_repo):
    """
    Checks if the repo has been indexed and tries to detect build files.
    Returns a summary or a message if none found.
    """
    if not selected_local_repo:
        return "No local repo selected."

    # Check if there's at least one indexed class for this repo, implying it's indexed
    entries = pipeline.index_service.list_indexed_classes_for_repo(selected_local_repo)
    if not entries:
        return "No index found for this repo. Please run indexing first."

    # We'll do a minimal approach (no single combined annotation from each file).
    # If you want the actual combined annotations from index pipeline, you can store them.
    # For demonstration, pass a blank or short summary to build_service:
    local_path = os.path.join("cloned_repos", selected_local_repo)
    if not os.path.exists(local_path):
        return f"Local repo path not found: {local_path}"

    # E.g. pass an empty string or some placeholder
    combined_annotations = "Repo was indexed. Summaries are not individually available here."
    result = build_service.analyze_build_files(local_path, combined_annotations)
    print(result)
    if isinstance(result, dict):
        return result.get("response", "No response")
    else:
        return str(result)

def run_build(selected_local_repo):
    """
    Attempts to run the build system if recognized (Maven, Gradle, or Makefile).
    Returns a build status message.
    """
    if not selected_local_repo:
        return "No local repo selected."

    # Again, check if repo is present
    local_path = os.path.join("cloned_repos", selected_local_repo)
    if not os.path.exists(local_path):
        return f"Local repo path not found: {local_path}"

    status = build_service.execute_build(local_path)
    return status

def create_chat_tab():
    """Creates the Chat tab UI with local repo selection and build system buttons."""
    with gr.Tab("Chat"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Select & Index Local Repo")

                local_repo_dropdown = gr.Dropdown(
                    label="Select Local Repo",
                    choices=[],
                    value=None,
                    interactive=True
                )

                refresh_local_button = gr.Button("Refresh Local Repos")
                index_button = gr.Button("Index Selected Repo")

                indexing_progress = gr.Textbox(
                    label="Indexing Progress / Logs",
                    lines=2,
                    interactive=False,
                    placeholder="Indexing progress messages will appear here..."
                )

                # Bind "Refresh Local Repos" to the existing function
                refresh_local_button.click(
                    fn=on_list_local_repos,
                    outputs=[local_repo_dropdown]
                )

                # The pipeline index call is now purely code indexing
                index_button.click(
                    fn=pipeline.index_repo_generator,
                    inputs=[local_repo_dropdown],
                    outputs=[indexing_progress]
                )

                # --- New Build System UI ---
                gr.Markdown("### Build System")
                detect_build_btn = gr.Button("Detect Build System")
                run_build_btn = gr.Button("Run Build")

                build_system_output = gr.Textbox(
                    label="Build System Info / Build Logs",
                    lines=6,
                    interactive=False,
                    placeholder="Info about the build system will appear here."
                )

                detect_build_btn.click(
                    fn=detect_build_system,
                    inputs=[local_repo_dropdown],
                    outputs=[build_system_output]
                )

                run_build_btn.click(
                    fn=run_build,
                    inputs=[local_repo_dropdown],
                    outputs=[build_system_output]
                )

            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="Chat Output", type="messages")
                msg = gr.Textbox(show_label=False, placeholder="Type your message...")
                send_btn = gr.Button("Send")

                # Chat handling
                msg.submit(
                    user_add_msg,
                    [msg, chatbot],
                    [chatbot, msg]
                ).then(
                    assistant_add_msg,
                    [chatbot, local_repo_dropdown],
                    [chatbot]
                )

                send_btn.click(
                    fn=user_add_msg,
                    inputs=[msg, chatbot],
                    outputs=[chatbot, msg],
                    queue=False,
                )
                send_btn.click(
                    fn=assistant_add_msg,
                    inputs=[chatbot, local_repo_dropdown],
                    outputs=[chatbot],
                )

    return local_repo_dropdown, chatbot, msg, send_btn, indexing_progress