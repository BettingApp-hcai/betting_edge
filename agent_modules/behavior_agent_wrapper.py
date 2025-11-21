from langchain_core.runnables import Runnable
from langchain.chat_models import ChatOpenAI


class BehaviorAgentLC(Runnable):
    """
    The RL-based behavior agent placeholder.
    Replace with real DQN later.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def invoke(self, user_state, **kwargs):
        prompt = """
        Choose one of these actions:
        neutral
        safe
        value
        high_risk
        summary
        explain
        Respond with the action only.
        """

        action = self.llm.invoke(prompt).content.strip()

        allowed = ["neutral", "safe", "value", "high_risk", "summary", "explain"]

        if action not in allowed:
            return "neutral"

        return action
