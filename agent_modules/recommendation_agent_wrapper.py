# /agent_modules/recommendation_agent_wrapper.py

import json
# --- START IMPORT FIX ---
# Using the correct, legacy import path per your instruction:
from langchain.chat_models import ChatOpenAI 
# --- END IMPORT FIX ---
from langchain_core.prompts import PromptTemplate
from data_agent import DataAgent 

class RecommendationAgentLC:
    """
    Agent responsible for synthesizing all structured data (prediction, verification, SQL context)
    into a final, conversational recommendation.
    """
    
    def __init__(self):
        # Initialize LLM and DataAgent (to access the SQL context method)
        self.data_agent = DataAgent() 
        # Using the legacy ChatOpenAI import path
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # Define the Synthesis Prompt template once
        self.prompt_template_str = """
        You are a seasoned sports betting analyst. Your task is to provide a concise recommendation 
        based on the provided analysis, structured match facts, and the user's inferred intent.

        --- MATCH FACTS ---
        MATCH DETAILS: {match_details}
        HOME TEAM STATS (Snapshot): {home_stats}
        LATEST ODDS: {latest_odds}
        
        --- MODEL ANALYSIS ---
        PREDICTION: Home Win Prob: {prediction_prob_home}, Away Win Prob: {prediction_prob_away}
        VERIFICATION: Value Edge is {value_edge} with {confidence} confidence.
        
        --- INFERRED INTENT ---
        BEHAVIOR: {action_tag} (Tailor the tone to this action, e.g., low risk, high education).

        --- TASK ---
        1. Summarize the key data point from the FACTS section (e.g., possession, shots).
        2. State the final recommendation (Bet For/Against) and the rationale based on the Value Edge.
        3. Keep the entire response clear, concise, and under 4 sentences.
        """
        # Create the PromptTemplate here, outside of invoke
        self.prompt = PromptTemplate.from_template(self.prompt_template_str)

    def invoke(self, context: dict):
        """
        Generates the final recommendation by interpreting structured data from context.
        """
        match_id = context['match']['fixture']['id']
        
        # 1. SQL-RAG: Fetch Structured Context from Database
        structured_context = self.data_agent.get_full_match_context(match_id)

        try:
            # 2. Prepare the input dictionary for the prompt, ensuring all complex objects are JSON strings
            input_data = {
                # Convert dictionaries to JSON strings to prevent prompt template serialization errors
                "match_details": json.dumps(structured_context.get('match_details', {})),
                "home_stats": json.dumps(structured_context.get('home_team_stats', {})),
                "latest_odds": json.dumps(structured_context.get('latest_odds', {})),
                
                # Analysis (other variables are already strings/floats)
                "prediction_prob_home": f"{context['prediction']['home_win_prob']:.2f}",
                "prediction_prob_away": f"{context['prediction']['away_win_prob']:.2f}",
                "value_edge": context['verification']['value_edge'],
                "confidence": context['verification']['confidence'],
                "action_tag": context['action'],
            }

            # 3. Explicitly format the prompt before sending it to the LLM
            formatted_prompt = self.prompt.format(**input_data)
            
            # 4. Invoke the LLM directly with the formatted string (avoids chain complexity)
            final_recommendation = self.llm.invoke(formatted_prompt)
            
            # 5. Extract the string content
            return final_recommendation.content
            
        except Exception as e:
            # This will help us debug if there's another issue
            return f"Error during recommendation synthesis: {e}"