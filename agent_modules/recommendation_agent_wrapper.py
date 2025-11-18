from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

class RecommendationAgentLC(Runnable):
    """
    Produces final natural-language recommendation based on 
    match context, prediction, verification, and behavior.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def invoke(self, composed, **kwargs):
        match = composed["match"]
        pred = composed["prediction"]
        ver = composed["verification"]
        action = composed["action"]

        prompt = f"""
        You are the recommendation generator.
        Create a short explanation for the user.
        Inputs:
        Match: {match}
        Prediction: {pred}
        Verification: {ver}
        Behavior Action: {action}
        """

        return self.llm.invoke(prompt).content
