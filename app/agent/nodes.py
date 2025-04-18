import json
import logging

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode

from app.agent.prompts import INTENT_PROMPT, generate_system_prompt
from app.agent.state import State

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Nodes():
    def __init__(self, model, facade):
        self.model = model
        self.search_node = ToolNode(tools=facade.search_tools)
        self.code_node = ToolNode(tools=facade.code_tools)
        logger.info("Initialized Nodes with model %s and facade %s", model, facade)


    def time_node(self, state: State) -> dict:
        info = state.user_info.get_user_info()
        now = info["local_time"]
        tz  = info["timezone"]

        msg = AIMessage(content=f"Today is {now.strftime('%A, %B %d, %Y')} in {tz}.")
        logger.info("time_node result: %s", msg.content)
        return {"messages": [msg], "state_updates": {"last_time_check": now}}

    def profile_node(self, state: State) -> dict:
        questions = []
        if "name" not in state.get("profile", {}):
            questions.append("By the way, what’s your name?")
        if "timezone" not in state.get("profile", {}):
            questions.append("Which timezone are you in, so I can give times correctly?")

        prompt = " ".join(questions)
        logger.info("profile_node prompt: %s", prompt)
        response = AIMessage(content=prompt)
        return {"messages": [response]}

    def detect_intent(self, text: str) -> str:
        messages = [
            SystemMessage(content=INTENT_PROMPT),
            HumanMessage(content=f"User message: {text}")
        ]
        reply = self.model.invoke(messages)
        raw = reply.content.strip()
        try:
            intent = json.loads(raw).get("intent", "other")
            logger.info("Parsed intent: %s", intent)
            return intent
        except Exception as e:
            logger.error("Failed to parse intent JSON: %s", e)
            return "other"

    def human_node(self, state: State) -> dict:
        last_msg = state["messages"][-1]
        user_text = last_msg.content.strip() if isinstance(last_msg, HumanMessage) else str(last_msg)

        history_parts = []
        for m in state["messages"][:-1]:
            role = "User" if isinstance(m, HumanMessage) else "Assistant"
            content = m.content.strip() if hasattr(m, "content") else str(m)
            history_parts.append(f"{role}: {content}")
        conversation_history = "\n".join(history_parts) or "(no previous conversation)"

        template = (
            "You are an assistant whose job is to clarify an ambiguous request.\n\n"
            "Conversation so far (for context):\n"
            "{conversation}\n\n"
            "Latest user message (ambiguous):\n"
            "\"{user_message}\"\n\n"
            "Ask the user a **single, specific follow‑up question** that will let you resolve the ambiguity. "
            "Keep the question short and direct; add no other text."
        )

        prompt = template.format(
            conversation=conversation_history,
            user_message=user_text,
        )

        response: AIMessage = self.model.invoke([SystemMessage(content=prompt)])
        logger.info("human_node response: %s", response.content)
        return {"messages": [response]}

    def chatbot_node(self, state: State) -> dict:
        chat_msgs: list[BaseMessage] = [SystemMessage(content=generate_system_prompt())]
        for m in state["messages"]:
            chat_msgs.append(m)

        response_msg: AIMessage = self.model.invoke(chat_msgs)
        logger.info("chatbot_node response: %s", response_msg.content)
        return {"messages": [response_msg]}

    def end_node_fn(self, state: State) -> dict:
        logger.info("Entering end_node_fn: ending conversation.")
        return {"messages": [AIMessage(content="(Conversation ended.)")]}