from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
import json

class PredictionAgentLC(Runnable):
    """
    Placeholder prediction agent using OpenAI.
    Replace later with real ML model.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def invoke(self, match, **kwargs):
        prompt = f"""
        You are the prediction module.
        Estimate win probabilities for this match.
        Return JSON only.
        Match:
        {match}
        """

        out = self.llm.invoke(prompt).content

        try:
            return json.loads(out)
        except:
            return {
                "home_win_prob": 0.40,
                "draw_prob": 0.30,
                "away_win_prob": 0.30
            }
