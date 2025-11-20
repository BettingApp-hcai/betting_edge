# pipelines/pipeline.py (UPDATED)

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
        Now handles returning multiple matches or a single selected match.
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

        # --- MODIFIED LOGIC: Filter matches based on query ---
        all_filtered_matches = []
        target_team = structured.team_name.lower() if structured.team_name else None
        
        # Filter all fetched matches by team if specified
        for m in matches:
            home_name = m.get("teams", {}).get("home", {}).get("name", "").lower()
            away_name = m.get("teams", {}).get("away", {}).get("name", "").lower()
            
            if target_team is None or target_team in home_name or target_team in away_name:
                all_filtered_matches.append(m)

        if not all_filtered_matches:
            return {
                "status": "no_matches",
                "request": structured.dict(),
                "message": f"No matches found involving '{structured.team_name}' after filtering.",
            }

        # If only one match is desired for deep analysis, we can proceed with the rest of the pipeline
        # For now, we return all filtered matches and let Streamlit handle selection.
        # Future enhancement: Query Agent could indicate if a specific match was requested (e.g., "Liverpool vs Man Utd")
        
        # The key change: Return ALL filtered matches initially.
        # The rest of the pipeline (prediction, verification, etc.) will ONLY run AFTER a match is explicitly selected.

        return {
            "status": "ok",
            "query": user_query,
            "structured_query": structured.dict(),
            "filtered_matches": all_filtered_matches, # <-- Changed this to return all
            "message": f"Found {len(all_filtered_matches)} matches. Select one for detailed analysis."
        }

    def run_deep_analysis(self, selected_match: dict):
        """
        Runs the prediction, verification, behavior, recommendation, and ethics
        for a *single, pre-selected match*.
        """
        if not selected_match:
            return {"status": "error", "message": "No match provided for deep analysis."}

        # Step 3: Prediction
        prediction = self.prediction_agent.invoke(selected_match)

        # Step 4: Verification
        verification = self.verification_agent.invoke(prediction)

        # Step 5: Behavior action
        action = self.behavior_agent.invoke({"state": "placeholder"})

        # Step 6: Recommendation
        recommendation = self.recommendation_agent.invoke({
            "match": selected_match,
            "prediction": prediction,
            "verification": verification,
            "action": action
        })

        # Step 7: Ethics
        ethics = self.ethics_agent.invoke(recommendation)

        return {
            "status": "ok",
            "match": selected_match,
            "prediction": prediction,
            "verification": verification,
            "action": action,
            "recommendation": recommendation,
            "ethics": ethics
        }