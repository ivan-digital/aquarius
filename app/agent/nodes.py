import json
import logging

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode

from app.agent.prompts import INTENT_PROMPT, generate_system_prompt # INTENT_PROMPT might need to be updated or removed
from app.agent.state import State
from app.config_manager import configManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Nodes():
    def __init__(self, model, facade=None):
        self.model = model
        if facade is not None:
            self.search_node = ToolNode(tools=facade.search_tools)
            self.code_node = ToolNode(tools=facade.code_tools)
        else:
            self.search_node = None
            self.code_node = None
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
        """Detect user intent using the LLM based on available intents from config."""
        intent_to_node_mapping = configManager.config.get("intent_to_node_mapping", {})
        available_intents = list(intent_to_node_mapping.keys())
        fallback_intent = configManager.config.get("fallback_node_name", "clarify") # Using fallback_node_name as the intent name for clarification

        if not available_intents:
            logger.warning("No intents configured in intent_to_node_mapping. Defaulting to fallback.")
            return fallback_intent

        # Construct the prompt for the LLM
        # This prompt needs to be carefully crafted.
        # For now, using a simplified version of the INTENT_PROMPT logic.
        # TODO: Refine this prompt or make INTENT_PROMPT more generic.
        prompt_template = (
            "Given the user's message and a list of available capabilities (intents), "
            "determine the most appropriate intent. "
            "The available intents are: {intent_list}. "
            "If none of the intents seem to match well, respond with '{fallback_intent}'. "
            "Only respond with the name of the intent and nothing else.\\n\\n"
            "User message: \\\"{user_message}\\\"\\n"
            "Intent:"
        )
        
        intent_list_str = ", ".join(available_intents)
        prompt = prompt_template.format(
            intent_list=intent_list_str,
            fallback_intent=fallback_intent,
            user_message=text
        )
        
        logger.debug(f"Detecting intent for: '{text}'. Prompt for LLM: {prompt}")

        try:
            # Assuming self.model.invoke can take a simple string prompt for this kind of task
            # and returns a response from which we can extract the intent string.
            # The actual invocation might need to be AIMessage, HumanMessage, etc.
            response = self.model.invoke([HumanMessage(content=prompt)]) # Wrapping in HumanMessage
            
            if isinstance(response, AIMessage):
                detected_intent = response.content.strip()
            elif hasattr(response, 'content') and isinstance(response.content, str):
                detected_intent = response.content.strip()
            else: # Fallback if response is not as expected
                logger.warning(f"LLM response for intent detection was not a string or AIMessage: {response}. Defaulting to fallback.")
                detected_intent = fallback_intent

            logger.info(f"LLM detected intent: '{detected_intent}' for text: '{text}'")

            # Validate if the detected intent is one of the available ones or the fallback
            if detected_intent in available_intents or detected_intent == fallback_intent:
                return detected_intent
            else:
                logger.warning(f"LLM returned an unknown intent '{detected_intent}'. Defaulting to fallback intent '{fallback_intent}'.")
                return fallback_intent
                
        except Exception as e:
            logger.error(f"Error during LLM call for intent detection: {e}. Defaulting to fallback intent '{fallback_intent}'.")
            return fallback_intent

    def human_node(self, state: State) -> dict:
        logger.info(f"Entering human_node with state: {state}")
        last_msg = state["messages"][-1]
        user_text = last_msg.content.strip() if isinstance(last_msg, HumanMessage) else str(last_msg)

        history_parts = []
        for m in state["messages"][:-1]:
            role = "User" if isinstance(m, HumanMessage) else "Assistant"
            content = m.content.strip() if hasattr(m, "content") else str(m)
            history_parts.append(f"{role}: {content}")
        conversation_history = "\\n".join(history_parts) or "(no previous conversation)"

        template = (
            "You are an assistant whose job is to clarify an ambiguous request.\\n\\n"
            "Conversation so far (for context):\\n"
            "{conversation}\\n\\n"
            "Latest user message (ambiguous):\\n"
            "\\\"{user_message}\\\"\\n\\n"
            "Ask the user a **single, specific follow‑up question** that will let you resolve the ambiguity. "
            "Keep the question short and direct; add no other text."
        )

        prompt = template.format(
            conversation=conversation_history,
            user_message=user_text,
        )
        logger.info(f"human_node prompt: {prompt}")

        raw_model_response = self.model.invoke([SystemMessage(content=prompt)])
        logger.info(f"human_node raw model response: {raw_model_response}")
        
        if isinstance(raw_model_response, AIMessage):
            response = raw_model_response
        elif hasattr(raw_model_response, 'content') and isinstance(raw_model_response.content, str):
            response = AIMessage(content=raw_model_response.content)
        else:
            logger.error(f"human_node received unexpected model response type: {type(raw_model_response)}. Content: {raw_model_response}")
            response = AIMessage(content="I'm having trouble understanding that. Could you try again?")

        logger.info("human_node generated AIMessage content: %s", response.content)
        
        return_dict = {"messages": [response]}
        logger.info(f"human_node returning: {return_dict}")
        return return_dict

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