# /data_agent.py (FINAL VERSION - SQL-RAG Ready)

import requests
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import json
import os
from dotenv import load_dotenv 

load_dotenv() 

class DataAgent:
    """
    Data Agent for fetching and managing sports data.
    Provides tools for API fetching, storage, and SQL-Augmented Context retrieval.
    """
    
    def __init__(self, sport_type: str = "football", db_path: str = "betting_edge.db"):
        # Load API keys
        api_keys = {
            "football": os.getenv("API_KEY_FOOTBALL"),
            "college_football": os.getenv("API_KEY_CFB"),
            "basketball": os.getenv("API_KEY_BASKETBALL")
        }
        
        self.sport_type = sport_type
        self.api_key = api_keys.get(sport_type)
        
        if not self.api_key:
            self.api_key = os.getenv("API_KEY_FOOTBALL_DATA") # Fallback check

        if not self.api_key:
            raise ValueError(f"API key for {sport_type} not found. Check your .env file.")
        
        # --- CONFIGURATION ---
        if sport_type == "football":
            self.base_url = "https://api.football-data.org/v4"
            self.headers = {'X-Auth-Token': self.api_key}
        
        elif sport_type == "college_football":
            self.base_url = "https://api.collegefootballdata.com"
            self.headers = {'Authorization': f'Bearer {self.api_key}', 'Accept': 'application/json'}
            
        elif sport_type == "basketball":
            self.base_url = "https://api.collegebasketballdata.com"
            self.headers = {'Authorization': f'Bearer {self.api_key}', 'Accept': 'application/json'}
        else:
             raise ValueError(f"Unsupported sport_type: {sport_type}")

        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required schemas."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY, sport_type TEXT, league_id INTEGER, 
                league_name TEXT, season INTEGER, match_date TEXT, home_team_id INTEGER, 
                home_team_name TEXT, away_team_id INTEGER, away_team_name TEXT,
                home_score INTEGER, away_score INTEGER, status TEXT, venue TEXT, last_updated TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER, team_id INTEGER, 
                team_name TEXT, shots_on_goal INTEGER, total_shots INTEGER, ball_possession INTEGER,
                last_updated TEXT, FOREIGN KEY (match_id) REFERENCES matches(match_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS odds (
                odds_id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER, bookmaker TEXT, 
                bet_type TEXT, home_odds REAL, draw_odds REAL, away_odds REAL, last_updated TEXT, 
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            )
        ''')

        cursor.execute('CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY, username TEXT UNIQUE)')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")

    # --- CORE FETCHING LOGIC (Unchanged) ---
    def fetch_matches(self, league_id: int = None, season: int = None, 
                      from_date: Optional[str] = None, to_date: Optional[str] = None,
                      year: Optional[int] = None, week: Optional[int] = None) -> List[Dict]:
        if self.sport_type == "college_football":
            return self._fetch_college_data(path="/games", year=year or season, week=week)
        elif self.sport_type == "basketball":
            return self._fetch_college_data(path="/games", year=year or season, week=week)
        else: # football
            id_map = {39: 'PL', 140: 'PD', 135: 'SA', 78: 'BL1', 61: 'FL1'}
            competition_code = id_map.get(league_id, 'PL') 
            return self._fetch_football_data_org(competition_code, season)

    def _fetch_football_data_org(self, competition_code: str, season: int) -> List[Dict]:
        url = f"{self.base_url}/competitions/{competition_code}/matches"
        params = {'season': season}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            raw_matches = data.get('matches', [])
            converted_games = []
            for m in raw_matches:
                converted = {
                    'fixture': {'id': m['id'], 'date': m['utcDate'], 'status': {'long': m['status']}, 'venue': {'name': 'Unknown'}},
                    'league': {'id': data['competition']['id'], 'name': data['competition']['name'], 'season': season},
                    'teams': {'home': {'id': m['homeTeam']['id'], 'name': m['homeTeam']['name']}, 'away': {'id': m['awayTeam']['id'], 'name': m['awayTeam']['name']}},
                    'goals': {'home': m['score']['fullTime']['home'], 'away': m['score']['fullTime']['away']}
                }
                converted_games.append(converted)
            return converted_games
        except Exception as e:
            print(f"Error fetching from football-data.org: {e}")
            return []

    def _fetch_college_data(self, path: str, year: int, week: Optional[int] = None) -> List[Dict]:
        endpoint = f"{self.base_url}{path}"
        params = {'year': year}
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            if 'application/json' not in response.headers.get('Content-Type', ''): return []
            data = response.json()
            converted_games = []
            for game in data:
                if game.get('season') == year:
                    converted_game = {
                        'fixture': {'id': game.get('id', 0), 'date': game.get('startDate', ''), 'status': {'long': 'completed' if game.get('completed') else 'scheduled'}, 'venue': {'name': game.get('venue') or 'TBD'}},
                        'league': {'id': 0, 'name': 'College Football' if self.sport_type == 'college_football' else 'College Basketball', 'season': game.get('season', year)},
                        'teams': {'home': {'id': game.get('homeId', 0), 'name': game.get('homeTeam', 'TBD')}, 'away': {'id': game.get('awayId', 0), 'name': game.get('awayTeam', 'TBD')}},
                        'goals': {'home': game.get('homePoints'), 'away': game.get('awayPoints')}
                    }
                    converted_games.append(converted_game)
            return converted_games
        except Exception as e:
            print(f"Error fetching college games: {e}")
            return []
            
    def store_match(self, match_data: Dict):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        try:
            f, l, t, g = match_data['fixture'], match_data['league'], match_data['teams'], match_data['goals']
            cursor.execute('''INSERT OR REPLACE INTO matches (match_id, sport_type, league_id, league_name, season, match_date, home_team_id, home_team_name, away_team_id, away_team_name, home_score, away_score, status, venue, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (f['id'], self.sport_type, l['id'], l['name'], l['season'], f['date'], t['home']['id'], t['home']['name'], t['away']['id'], t['away']['name'], g['home'], g['away'], f['status']['long'], f['venue']['name'], datetime.now().isoformat()))
            conn.commit()
        except Exception as e:
            print(f"Error storing match: {e}")
        finally:
            conn.close()

    # --- CORE SQL-RAG IMPLEMENTATION ---

    def _safe_fetch_one(self, query: str, params: tuple) -> Dict:
        """Safely executes a query and returns a dictionary or an empty dict {}."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row is not None else {}
        except Exception as e:
            # Catches errors if table is completely missing or SQL is malformed
            print(f"SQL Error in safe_fetch: {e}")
            conn.close()
            return {}
    
    def get_full_match_context(self, match_id: int) -> Dict:
        """
        Retrieves all necessary structured data for the Recommendation Agent.
        """
        
        # 1. Get Match and Score Details
        match_details = self._safe_fetch_one(
            'SELECT * FROM matches WHERE match_id = ?', 
            (match_id,)
        )
        
        # Default to -1 if match details couldn't be found
        home_team_id = match_details.get('home_team_id', -1) 
        
        # 2. Get Statistics (Focus on Home Team)
        home_stats = self._safe_fetch_one(
            'SELECT ball_possession, total_shots, shots_on_goal FROM match_stats WHERE match_id = ? AND team_id = ?',
            (match_id, home_team_id)
        )
        
        # 3. Get Latest Odds
        latest_odds = self._safe_fetch_one(
            'SELECT bookmaker, home_odds, away_odds FROM odds WHERE match_id = ? ORDER BY last_updated DESC LIMIT 1',
            (match_id,)
        )
        
        # Combine into a single, clean dictionary for the LLM
        return {
            "match_details": match_details,
            "home_team_stats": home_stats,
            "latest_odds": latest_odds,
        }

    # --- PLACEHOLDERS (Cleaned up) ---
    def fetch_stats(self, match_id: int): return None
    def fetch_odds(self, match_id: int): return None
    def store_stats(self, match_id, data): pass
    def store_odds(self, match_id, data): pass
    def refresh_data_for_match(self, match_id): pass
    
    def get_recent_matches(self, team_id: int, limit: int = 5) -> List[Dict]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM matches WHERE (home_team_id = ? OR away_team_id = ?) AND (status = 'FINISHED' OR status = 'completed' OR status = 'Match Finished') ORDER BY match_date DESC LIMIT ?''', (team_id, team_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]