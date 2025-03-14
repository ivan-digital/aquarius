import dspy
from app.server.agent.signatures import ExtractIntent, ExtractQAType, BasicQA, DetailedQA, CommandExec, AskClarification


class ReactAgent:
    def __init__(self, tools_facade, intent_conf_threshold=0.8, qa_conf_threshold=0.8):
        self.tools_facade = tools_facade
        self.intent_conf_threshold = intent_conf_threshold
        self.qa_conf_threshold = qa_conf_threshold

        self.intent_extractor = dspy.ChainOfThought(ExtractIntent)
        self.qa_type_extractor = dspy.ChainOfThought(ExtractQAType)
        self.react_qa = dspy.ReAct(BasicQA, tools=self.tools_facade.search_tools)
        self.react_detailed = dspy.ReAct(DetailedQA, tools=self.tools_facade.available_tools)
        self.react_command = dspy.ReAct(CommandExec, tools=self.tools_facade.code_tools)
        self.clarification_agent = dspy.ChainOfThought(AskClarification)

    def extract_intent(self, user_input: str) -> dict:
        """
        Extract the intent from the user input.
        Expected result should have both an 'intent' attribute and a 'confidence' score.
        If confidence is not provided, defaults to 1.0.
        """
        result = self.intent_extractor(text=user_input)
        print(f"extract_intent result: {result}")
        intent = getattr(result, 'intent', None)
        confidence = getattr(result, 'confidence', 1.0)
        return {"intent": intent, "confidence": confidence}

    def extract_qa_type(self, question: str) -> dict:
        """
        Determine the QA type (e.g., 'short' or 'detailed') from the question.
        Expected result should include 'qa_type' and a 'confidence' score.
        Defaults to 1.0 if not provided.
        """
        result = self.qa_type_extractor(question=question)
        print(f"extract_qa_type result: {result}")
        qa_type = getattr(result, 'qa_type', None)
        confidence = getattr(result, 'confidence', 1.0)
        return {"qa_type": qa_type, "confidence": confidence}

    def ask_qa_clarification(self, text: str) -> dict:
        """
        Use the LLM clarification agent to ask for more details when the QA type is ambiguous.
        """
        result = self.clarification_agent(question=text)
        print(f"ask_qa_clarification {result}")
        return {"final": False, "response": result.message}

    def process(self, conversation_history: list, current_message: str) -> dict:
        """
        Process the user input by:
          1. Extracting intent. If the confidence is below the threshold, ask for clarification.
          2. For 'qa' intent, extracting the QA type. Again, if confidence is low, ask for clarification.
          3. Routing to the appropriate module based on the (possibly clarified) intent and QA type.
          4. Emitting intermediate clarification responses and a final response with a final flag.
        Returns a dictionary containing the final response.
        """
        full_input = "\n".join(
            f"{msg['r   ole']}: {msg['content']}"
            for msg in conversation_history
        )
        full_input += f"\nuser: {current_message}"
        intent_result = self.extract_intent(full_input)
        if intent_result["confidence"] < self.intent_conf_threshold:
            clar_message = "I'm not sure I understood your intent. Could you please clarify your request?"
            return {"final": False, "response": clar_message}

        intent = intent_result["intent"]

        if intent == "qa":
            qa_result = self.extract_qa_type(full_input)
            if qa_result["confidence"] < self.qa_conf_threshold:
                clar_message = "I'm not sure if you want a short or detailed answer. Could you please specify?"
                return {"final": False, "response": clar_message}
            qa_type = qa_result["qa_type"]

            if qa_type == "short":
                result = self.react_qa(question=full_input)
                print(f"react_qa {result}")
                final_answer = f"Short QA Answer: {result.answer}"
            elif qa_type == 'detailed':
                result = self.react_detailed(question=full_input)
                print(f"react_detailed {result}")
                final_answer = f"Detailed QA Answer: {result.answer}"
            else:
                return self.ask_qa_clarification(full_input)

        else:
            result = self.react_command(command=full_input)
            print(f"react_command {result}")
            final_answer = f"Command Execution Result: {result.result}"

        return {"final": True, "response": final_answer}