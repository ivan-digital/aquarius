import dspy


# Base class to fuse humanistic traits
class HumanSignature(dspy.Signature):
    """
    Base signature for responses that incorporate a friendly, human touch.
    """
    personality = dspy.OutputField(default="friendly", desc="The assistant's personality style.")


class BasicQA(HumanSignature):
    """Answer factual questions with a short factoid answer in a personable tone."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="Concise answer (often between 1 and 5 words) delivered in a friendly style.")


class DetailedQA(HumanSignature):
    """Answer factual questions with a detailed explanation in a warm, conversational manner."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="Detailed explanation answer enriched with personal insights.")


class CommandExec(HumanSignature):
    """Execute user commands and return the result in a clear and human-friendly manner."""
    command = dspy.InputField()
    result = dspy.OutputField(desc="Command execution result articulated in a warm, engaging style.")


class ExtractIntent(HumanSignature):
    """Extract the intent from the user input using an LLM in a human-like way.
    Returns either 'command' or 'qa' with a touch of personality."""
    text = dspy.InputField()
    intent = dspy.OutputField(desc="Extracted intent: either 'command' or 'qa', expressed with human context.")


class ExtractQAType(HumanSignature):
    """Determine whether a factual question expects a short or detailed answer with a friendly tone.
    Returns either 'short' or 'detailed'."""
    question = dspy.InputField()
    qa_type = dspy.OutputField(desc="Extracted QA type: either 'short' or 'detailed', with a personal nuance.")


class AskClarification(HumanSignature):
    """Generate a friendly clarification message when the user's input is ambiguous.
    Returns a message asking for more details in a warm, approachable way."""
    question = dspy.InputField()
    message = dspy.OutputField(desc="Friendly clarification message asking for more details.")
