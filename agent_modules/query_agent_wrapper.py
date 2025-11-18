from langchain_core.runnables import Runnable
from query_agent import parse_user_query

class QueryAgentLC(Runnable):
    def invoke(self, user_query: str, **kwargs):
        result = parse_user_query(user_query)
        return result
