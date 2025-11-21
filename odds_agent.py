import requests
import os
from dotenv import load_dotenv

load_dotenv()

class OddsAgent:
    """
    Fetches betting odds (future + live) using The Odds API.
    Docs: https://the-odds-api.com/
    """

    def __init__(self):
        self.api_key = os.getenv("ODDS_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Missing ODDS_API_KEY in .env file.")
        
        self.base_url = "https://api.the-odds-api.com/v4"

    def _get(self, endpoint, params):
        params["apiKey"] = self.api_key

        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print("❌ Odds API Error:", e)
            return []

    # ----------------------------
    # UPCOMING / FUTURE ODDS
    # ----------------------------
    def get_upcoming_odds(self, sport="soccer_epl", regions="us,eu", markets="h2h,ou,spreads"):
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal"
        }
        endpoint = f"/sports/{sport}/odds"
        return self._get(endpoint, params)

    # ----------------------------
    # LIVE SCORES + LIVE ODDS
    # ----------------------------
    def get_live_odds(self, sport="soccer_epl"):
        """
        Odds API supports live data via the /scores endpoint.
        """
        params = {"daysFrom": 3}
        endpoint = f"/sports/{sport}/scores"
        return self._get(endpoint, params)

    # ----------------------------
    # LIST AVAILABLE SPORTS
    # ----------------------------
    def list_sports(self):
        endpoint = "/sports"
        return self._get(endpoint, {})
