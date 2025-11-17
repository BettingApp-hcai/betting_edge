import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

class DataAgent:
    """
    Data Agent for fetching and managing sports data from API-Football.
    Handles live/historical data and stores it in SQLite database.
    """
    
    def __init__(self, api_key: str = None, sport_type: str = "football", db_path: str = "betting_edge.db"):
        """
        Initialize the Data Agent.
        
        Args:
            api_key: API key (API-Football or API-Sports)
            sport_type: Type of sport - "football" or "college_football"
            db_path: Path to SQLite database
        """
        # Default API keys
        default_keys = {
            "football": "29b91fd12011657f47a0b7da8c65a89a",
            "college_football": "Cm65xEJGHrZaC4gxJE5d1ZdcJYEC+Zw1Yo8ZFjs4h7HUPe6XazxcXntbTLMdjssF"
        }
        
        self.sport_type = sport_type
        self.api_key = api_key if api_key else default_keys.get(sport_type)
        
        if sport_type == "football":
            self.base_url = "https://v3.football.api-football.com"
            self.headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': 'v3.football.api-football.com'
            }
        else:  # college_football
            self.base_url = "https://api.sportsdata.io/v3/cfb"
            self.headers = {
                'Ocp-Apim-Subscription-Key': self.api_key
            }
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required schemas."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY,
                league_id INTEGER,
                league_name TEXT,
                season INTEGER,
                match_date TEXT,
                home_team_id INTEGER,
                home_team_name TEXT,
                away_team_id INTEGER,
                away_team_name TEXT,
                home_score INTEGER,
                away_score INTEGER,
                status TEXT,
                venue TEXT,
                last_updated TEXT
            )
        ''')
        
        # Match statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                team_id INTEGER,
                team_name TEXT,
                shots_on_goal INTEGER,
                shots_off_goal INTEGER,
                total_shots INTEGER,
                blocked_shots INTEGER,
                shots_inside_box INTEGER,
                shots_outside_box INTEGER,
                fouls INTEGER,
                corner_kicks INTEGER,
                offsides INTEGER,
                ball_possession INTEGER,
                yellow_cards INTEGER,
                red_cards INTEGER,
                goalkeeper_saves INTEGER,
                total_passes INTEGER,
                passes_accurate INTEGER,
                passes_percentage INTEGER,
                last_updated TEXT,
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            )
        ''')
        
        # Odds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS odds (
                odds_id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                bookmaker TEXT,
                bet_type TEXT,
                home_odds REAL,
                draw_odds REAL,
                away_odds REAL,
                spread REAL,
                over_under REAL,
                last_updated TEXT,
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            )
        ''')
        
        # Team form table (derived stats)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_form (
                form_id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                team_name TEXT,
                last_5_wins INTEGER,
                last_5_draws INTEGER,
                last_5_losses INTEGER,
                avg_goals_scored REAL,
                avg_goals_conceded REAL,
                form_string TEXT,
                last_updated TEXT
            )
        ''')
        
        # User profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                risk_tolerance TEXT,
                focus_teams TEXT,
                preferred_leagues TEXT,
                last_updated TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")
    
    def fetch_odds(self, match_id: int) -> Optional[Dict]:
        """
        Fetch betting odds for a specific match.
        
        Args:
            match_id: API-Football match ID
            
        Returns:
            Dictionary containing odds data or None if request fails
        """
        endpoint = f"{self.base_url}/odds"
        params = {'fixture': match_id}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['response']:
                return data['response'][0]
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds: {e}")
            return None
    
    def fetch_matches(self, league_id: int, season: int, 
                     from_date: Optional[str] = None,
                     to_date: Optional[str] = None) -> List[Dict]:
        """
        Fetch matches for a specific league and season.
        
        Args:
            league_id: League ID (e.g., 39 for Premier League)
            season: Season year (e.g., 2024)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            List of match dictionaries
        """
        endpoint = f"{self.base_url}/fixtures"
        params = {
            'league': league_id,
            'season': season
        }
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data['response']
        except requests.exceptions.RequestException as e:
            print(f"Error fetching matches: {e}")
            return []
    
    def fetch_stats(self, match_id: int) -> Optional[Dict]:
        """
        Fetch detailed statistics for a specific match.
        
        Args:
            match_id: API-Football match ID
            
        Returns:
            Dictionary containing match statistics or None
        """
        endpoint = f"{self.base_url}/fixtures/statistics"
        params = {'fixture': match_id}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data['response']
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stats: {e}")
            return None
    
    def fetch_team_stats(self, team_id: int, league_id: int, season: int) -> Optional[Dict]:
        """
        Fetch team statistics for a season.
        
        Args:
            team_id: Team ID
            league_id: League ID
            season: Season year
            
        Returns:
            Dictionary containing team statistics
        """
        endpoint = f"{self.base_url}/teams/statistics"
        params = {
            'team': team_id,
            'league': league_id,
            'season': season
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data['response']
        except requests.exceptions.RequestException as e:
            print(f"Error fetching team stats: {e}")
            return None
    
    def store_match(self, match_data: Dict):
        """Store match data in SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        fixture = match_data['fixture']
        league = match_data['league']
        teams = match_data['teams']
        goals = match_data['goals']
        
        cursor.execute('''
            INSERT OR REPLACE INTO matches 
            (match_id, league_id, league_name, season, match_date,
             home_team_id, home_team_name, away_team_id, away_team_name,
             home_score, away_score, status, venue, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fixture['id'],
            league['id'],
            league['name'],
            league['season'],
            fixture['date'],
            teams['home']['id'],
            teams['home']['name'],
            teams['away']['id'],
            teams['away']['name'],
            goals['home'],
            goals['away'],
            fixture['status']['long'],
            fixture['venue']['name'],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def store_stats(self, match_id: int, stats_data: List[Dict]):
        """Store match statistics in SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for team_stats in stats_data:
            team = team_stats['team']
            stats = {s['type']: s['value'] for s in team_stats['statistics']}
            
            cursor.execute('''
                INSERT OR REPLACE INTO match_stats 
                (match_id, team_id, team_name, shots_on_goal, shots_off_goal,
                 total_shots, blocked_shots, shots_inside_box, shots_outside_box,
                 fouls, corner_kicks, offsides, ball_possession,
                 yellow_cards, red_cards, goalkeeper_saves,
                 total_passes, passes_accurate, passes_percentage, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_id,
                team['id'],
                team['name'],
                stats.get('Shots on Goal', 0),
                stats.get('Shots off Goal', 0),
                stats.get('Total Shots', 0),
                stats.get('Blocked Shots', 0),
                stats.get('Shots insidebox', 0),
                stats.get('Shots outsidebox', 0),
                stats.get('Fouls', 0),
                stats.get('Corner Kicks', 0),
                stats.get('Offsides', 0),
                stats.get('Ball Possession', '0%').rstrip('%'),
                stats.get('Yellow Cards', 0),
                stats.get('Red Cards', 0),
                stats.get('Goalkeeper Saves', 0),
                stats.get('Total passes', 0),
                stats.get('Passes accurate', 0),
                stats.get('Passes %', '0%').rstrip('%'),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def store_odds(self, match_id: int, odds_data: Dict):
        """Store betting odds in SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for bookmaker in odds_data['bookmakers']:
            for bet in bookmaker['bets']:
                if bet['name'] == 'Match Winner':
                    values = bet['values']
                    cursor.execute('''
                        INSERT INTO odds 
                        (match_id, bookmaker, bet_type, home_odds, draw_odds, away_odds, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        match_id,
                        bookmaker['name'],
                        'Match Winner',
                        float(values[0]['odd']) if len(values) > 0 else None,
                        float(values[1]['odd']) if len(values) > 1 else None,
                        float(values[2]['odd']) if len(values) > 2 else None,
                        datetime.now().isoformat()
                    ))
        
        conn.commit()
        conn.close()
    
    def get_match_data(self, match_id: int) -> Optional[Dict]:
        """Retrieve match data from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM matches WHERE match_id = ?', (match_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_recent_matches(self, team_id: int, limit: int = 5) -> List[Dict]:
        """Get recent matches for a team."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM matches 
            WHERE (home_team_id = ? OR away_team_id = ?)
            AND status = 'Match Finished'
            ORDER BY match_date DESC
            LIMIT ?
        ''', (team_id, team_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def refresh_data_for_match(self, match_id: int):
        """
        Complete data refresh for a specific match.
        Fetches and stores match info, stats, and odds.
        """
        print(f"Refreshing data for match {match_id}...")
        
        # Fetch and store odds
        odds_data = self.fetch_odds(match_id)
        if odds_data:
            self.store_odds(match_id, odds_data)
            print(f"✓ Odds stored")
        
        # Fetch and store stats
        stats_data = self.fetch_stats(match_id)
        if stats_data:
            self.store_stats(match_id, stats_data)
            print(f"✓ Stats stored")
        
        print(f"Data refresh complete for match {match_id}")


# Example usage
if __name__ == "__main__":
    # Initialize agent with your API key
    API_KEY = "your_api_key_here"  # Replace with actual key
    agent = DataAgent(API_KEY)
    
    # Example: Fetch and store Premier League matches
    # league_id = 39  # Premier League
    # season = 2024
    # matches = agent.fetch_matches(league_id, season)
    # 
    # for match in matches[:5]:  # First 5 matches
    #     agent.store_match(match)
    #     agent.refresh_data_for_match(match['fixture']['id'])