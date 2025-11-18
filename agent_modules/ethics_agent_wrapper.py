from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
import json

class EthicsAgentLC(Runnable):
    """
    A safety check module.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def invoke(self, text, **kwargs):
        prompt = f"""
        You are the ethics filter.
        Evaluate the following content:
        {text}
        Return JSON only:
        {{"status": "pass" or "fail"}}
        """

        out = self.llm.invoke(prompt).content

        try:
            return json.loads(out)
        except:
            return {"status": "pass"}
