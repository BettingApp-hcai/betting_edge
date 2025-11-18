from agent_modules.data_agent_wrapper import DataAgentLC
from agent_modules.prediction_agent_wrapper import PredictionAgentLC
from agent_modules.verification_agent_wrapper import VerificationAgentLC
from agent_modules.behavior_agent_wrapper import BehaviorAgentLC
from agent_modules.recommendation_agent_wrapper import RecommendationAgentLC
from agent_modules.ethics_agent_wrapper import EthicsAgentLC
from agent_modules.query_agent_wrapper import QueryAgentLC


class BettingEdgePipeline:
    """
    This is the unified multi-agent flow:
    user query -> query agent -> data agent -> prediction -> verification -> behavior -> recommendation -> ethics
    """

    def __init__(self):
        self.query_agent = QueryAgentLC()
        self.data_agent = DataAgentLC()
        self.prediction_agent = PredictionAgentLC()
        self.verification_agent = VerificationAgentLC()
        self.behavior_agent = BehaviorAgentLC()
        self.recommendation_agent = RecommendationAgentLC()
        self.ethics_agent = EthicsAgentLC()

    def run(self, user_query: str):
        """
        Runs the full pipeline start to finish.
        """

        # Step 1: Query agent
        structured = self.query_agent.invoke(user_query)
        if structured is None:
            return {
                "status": "query_error",
                "message": "Query agent could not parse that request"
            }

        # Step 2: Data agent fetch
        matches = self.data_agent.invoke(structured.dict())
        if not matches:
            return {
                "status": "no_matches",
                "request": structured.dict(),
                "message": "No matching results from data agent",
            }

        # use the first match in list
        match = matches[0]

        # Step 3: Prediction
        prediction = self.prediction_agent.invoke(match)

        # Step 4: Verification
        verification = self.verification_agent.invoke(prediction)

        # Step 5: Behavior action
        action = self.behavior_agent.invoke({"state": "placeholder"})

        # Step 6: Recommendation
        recommendation = self.recommendation_agent.invoke({
            "match": match,
            "prediction": prediction,
            "verification": verification,
            "action": action
        })

        # Step 7: Ethics
        ethics = self.ethics_agent.invoke(recommendation)

        return {
            "status": "ok",
            "query": user_query,
            "structured_query": structured.dict(),
            "match": match,
            "prediction": prediction,
            "verification": verification,
            "action": action,
            "recommendation": recommendation,
            "ethics": ethics
        }
