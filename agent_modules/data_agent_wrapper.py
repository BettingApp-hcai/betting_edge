from langchain_core.runnables import Runnable
from data_agent import DataAgent

class DataAgentLC(Runnable):
    """
    LangChain wrapper over your existing DataAgent.
    """

    def __init__(self):
        self.agent = None

    def invoke(self, params, **kwargs):
        sport = params["sport_type"]
        season = params["season"]
        comp = params.get("competition_code")

        self.agent = DataAgent(sport_type=sport, db_path="betting_edge.db")

        if sport == "football":
            return self.agent._fetch_football_data_org(
                competition_code=comp or "PL",
                season=season
            )
        else:
            return self.agent.fetch_matches(year=season)
