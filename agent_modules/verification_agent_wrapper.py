from langchain_core.runnables import Runnable
from langchain.chat_models import ChatOpenAI
import json

class VerificationAgentLC(Runnable):
    """
    Value checking module for predictions.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def invoke(self, prediction, **kwargs):
        prompt = f"""
        You are the value verification module.
        Given this prediction:
        {prediction}
        Rate whether the edge is low, medium, or high.
        Return JSON only.
        """

        out = self.llm.invoke(prompt).content

        try:
            return json.loads(out)
        except:
            return {
                "value_edge": "Low",
                "confidence": "Medium"
            }
