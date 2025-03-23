import json
from langchain import LLMChain, PromptTemplate
from langchain.llms import OpenAI


class ReactAgent:
    def __init__(self, tools_facade, intent_conf_threshold=0.8, qa_conf_threshold=0.8, llm=None):
        self.tools_facade = tools_facade
        self.intent_conf_threshold = intent_conf_threshold
        self.qa_conf_threshold = qa_conf_threshold
        self.llm = llm or OpenAI(temperature=0)

        # --- Chain for extracting intent ---
        self.intent_template = PromptTemplate(
            input_variables=["text"],
            template=(
                "You are a friendly assistant. Analyze the input below and extract the intent.\n"
                "Return a JSON object with two keys: 'intent' (either 'command' or 'qa') and 'confidence' (a float between 0 and 1).\n"
                "Input: {text}"
            )
        )
        self.intent_chain = LLMChain(llm=self.llm, prompt=self.intent_template)

        # --- Chain for determining QA type ---
        self.qa_type_template = PromptTemplate(
            input_variables=["question"],
            template=(
                "Determine whether the following question expects a short answer or a detailed explanation. \n"
                "Return a JSON object with keys: 'qa_type' (either 'short' or 'detailed') and 'confidence' (a float between 0 and 1).\n"
                "Question: {question}"
            )
        )
        self.qa_type_chain = LLMChain(llm=self.llm, prompt=self.qa_type_template)

        # --- Chain for planning (clarification check) ---
        self.planner_template = PromptTemplate(
            input_variables=["question"],
            template=(
                "Analyze the following input and decide if any clarification is needed before executing the request. \n"
                "Return a JSON object with keys: 'needs_clarification' (true/false) and 'clarification_message'. \n"
                "Input: {question}"
            )
        )
        self.planner_chain = LLMChain(llm=self.llm, prompt=self.planner_template)

        # --- Chain for generating clarification message ---
        self.clarification_template = PromptTemplate(
            input_variables=["question"],
            template=(
                "The input appears ambiguous. Please ask for additional details in a friendly manner.\n"
                "Input: {question}"
            )
        )
        self.clarification_chain = LLMChain(llm=self.llm, prompt=self.clarification_template)

        # --- Chain for short QA answers ---
        self.basic_qa_template = PromptTemplate(
            input_variables=["question"],
            template=(
                "Answer the following question in a friendly tone with a concise answer (1-5 words):\n"
                "Question: {question}"
            )
        )
        self.basic_qa_chain = LLMChain(llm=self.llm, prompt=self.basic_qa_template)

        # --- Chain for detailed QA answers ---
        self.detailed_qa_template = PromptTemplate(
            input_variables=["question"],
            template=(
                "Provide a detailed explanation in a warm and conversational tone for the following question:\n"
                "Question: {question}"
            )
        )
        self.detailed_qa_chain = LLMChain(llm=self.llm, prompt=self.detailed_qa_template)

        # --- Chain for command execution ---
        self.command_exec_template = PromptTemplate(
            input_variables=["command"],
            template=(
                "Execute the following command and return the result in a clear and engaging manner:\n"
                "Command: {command}"
            )
        )
        self.command_exec_chain = LLMChain(llm=self.llm, prompt=self.command_exec_template)

        # --- Chain for self-critical feedback ---
        self.self_critic_template = PromptTemplate(
            input_variables=["answer_content"],
            template=(
                "Provide self-critical feedback for the following answer. If there is no feedback to provide, respond with 'No feedback provided'.\n"
                "Answer: {answer_content}"
            )
        )
        self.self_critic_chain = LLMChain(llm=self.llm, prompt=self.self_critic_template)

    def extract_intent(self, user_input: str) -> dict:
        result = self.intent_chain.run(text=user_input)
        try:
            data = json.loads(result)
            intent = data.get("intent")
            confidence = float(data.get("confidence", 1.0))
        except Exception as e:
            intent, confidence = None, 0.0
        print(f"extract_intent result: {data if 'data' in locals() else result}")
        return {"intent": intent, "confidence": confidence}

    def extract_qa_type(self, question: str) -> dict:
        result = self.qa_type_chain.run(question=question)
        try:
            data = json.loads(result)
            qa_type = data.get("qa_type")
            confidence = float(data.get("confidence", 1.0))
        except Exception as e:
            qa_type, confidence = None, 0.0
        print(f"extract_qa_type result: {data if 'data' in locals() else result}")
        return {"qa_type": qa_type, "confidence": confidence}

    def ask_qa_clarification(self, text: str) -> dict:
        result = self.clarification_chain.run(question=text)
        print(f"ask_qa_clarification result: {result}")
        return {"final": False, "response": result}

    def process(self, conversation_history: list, current_message: str) -> dict:
        # Build the conversation context
        full_input = "\n".join(f"{msg['role']}: {msg['content']}" for msg in conversation_history)
        full_input += f"\nuser: {current_message}"

        # --- Planning Turn ---
        plan_result = self.planner_chain.run(question=full_input)
        try:
            plan_data = json.loads(plan_result)
            needs_clarification = plan_data.get("needs_clarification", False)
            clarification_message = plan_data.get("clarification_message", "")
        except Exception as e:
            needs_clarification, clarification_message = False, ""
        print(f"plan_result: {plan_data if 'plan_data' in locals() else plan_result}")

        if needs_clarification:
            return {"final": False, "response": clarification_message or "Could you please provide more details?"}

        # --- Intent Extraction ---
        intent_result = self.extract_intent(full_input)
        if intent_result["confidence"] < self.intent_conf_threshold:
            return {"final": False,
                    "response": "I'm not sure I understood your intent. Could you please clarify your request?"}

        intent = intent_result["intent"]

        # --- Processing Based on Intent ---
        if intent == "qa":
            qa_result = self.extract_qa_type(full_input)
            if qa_result["confidence"] < self.qa_conf_threshold:
                return {"final": False,
                        "response": "I'm not sure if you want a short or detailed answer. Could you please specify?"}
            qa_type = qa_result["qa_type"]

            if qa_type == "short":
                answer_content = self.basic_qa_chain.run(question=full_input)
                answer_prefix = "Short QA Answer"
            elif qa_type == "detailed":
                answer_content = self.detailed_qa_chain.run(question=full_input)
                answer_prefix = "Detailed QA Answer"
            else:
                return self.ask_qa_clarification(full_input)
        else:
            answer_content = self.command_exec_chain.run(command=full_input)
            answer_prefix = "Command Execution Result"

        # --- Self-Critic Turn ---
        critic_feedback = self.self_critic_chain.run(answer_content=answer_content)
        print(f"self_critic result: {critic_feedback}")
        final_answer = (
            f"{answer_prefix}: {answer_content} | Self Critique: {critic_feedback}"
        )
        return {"final": True, "response": final_answer}


