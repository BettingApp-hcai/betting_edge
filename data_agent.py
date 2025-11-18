# /data_agent.py
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
    Handles:
      - Football (Soccer) via football-data.org
      - College Football via collegefootballdata.com
      - College Basketball via collegebasketballdata.com
    """
    
    def __init__(self, sport_type: str = "football", db_path: str = "betting_edge.db"):
        # Load API keys
        api_keys = {
            "football": os.getenv("API_KEY_FOOTBALL"), # Now uses football-data.org key
            "college_football": os.getenv("API_KEY_CFB"),
            "basketball": os.getenv("API_KEY_BASKETBALL")
        }
        
        self.sport_type = sport_type
        self.api_key = api_keys.get(sport_type)
        
        # Fallback: If the key is missing, check specifically for the new variable name
        if not self.api_key and sport_type == "football":
             self.api_key = os.getenv("API_KEY_FOOTBALL_DATA")

        if not self.api_key:
            raise ValueError(f"API key for {sport_type} not found. Check your .env file.")
        
        # --- CONFIGURATION ---
        if sport_type == "football":
            # NEW: Configuration for football-data.org
            self.base_url = "https://api.football-data.org/v4"
            self.headers = {'X-Auth-Token': self.api_key}
        
        elif sport_type == "college_football":
            self.base_url = "https://api.collegefootballdata.com"
            self.headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
        elif sport_type == "basketball":
            self.base_url = "https://api.collegebasketballdata.com"
            self.headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
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
                match_id INTEGER PRIMARY KEY,
                sport_type TEXT,
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

    def fetch_matches(self, league_id: int = None, season: int = None, 
                      from_date: Optional[str] = None,
                      to_date: Optional[str] = None,
                      year: Optional[int] = None,
                      week: Optional[int] = None) -> List[Dict]:
        """
        Fetch matches based on the agent's sport_type.
        """
        if self.sport_type == "college_football":
            return self._fetch_college_data(path="/games", year=year or season, week=week)
        elif self.sport_type == "basketball":
            return self._fetch_college_data(path="/games", year=year or season, week=week)
        else: # football
            # Map legacy numeric IDs (from API-Sports) to new Football-Data.org Codes
            # 39=Premier League, 140=La Liga, 135=Serie A, 78=Bundesliga, 61=Ligue 1
            id_map = {39: 'PL', 140: 'PD', 135: 'SA', 78: 'BL1', 61: 'FL1'}
            competition_code = id_map.get(league_id, 'PL') 
            
            return self._fetch_football_data_org(competition_code, season)

    def _fetch_football_data_org(self, competition_code: str, season: int) -> List[Dict]:
        """
        Fetcher for football-data.org.
        Includes conversion to standard format so the rest of the app works.
        """
        url = f"{self.base_url}/competitions/{competition_code}/matches"
        params = {'season': season}
        
        try:
            print(f"Fetching Soccer from: {url}")
            print(f"Params: {params}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            raw_matches = data.get('matches', [])
            print(f"Found {len(raw_matches)} matches from football-data.org")

            converted_games = []
            for m in raw_matches:
                # Convert football-data.org format to our SQLite schema format
                converted = {
                    'fixture': {
                        'id': m['id'],
                        'date': m['utcDate'],
                        'status': {'long': m['status']}, # SCHEDULED, FINISHED, etc.
                        'venue': {'name': 'Unknown'} # This API doesn't always provide venue
                    },
                    'league': {
                        'id': data['competition']['id'],
                        'name': data['competition']['name'],
                        'season': season
                    },
                    'teams': {
                        'home': {
                            'id': m['homeTeam']['id'],
                            'name': m['homeTeam']['name']
                        },
                        'away': {
                            'id': m['awayTeam']['id'],
                            'name': m['awayTeam']['name']
                        }
                    },
                    'goals': {
                        'home': m['score']['fullTime']['home'],
                        'away': m['score']['fullTime']['away']
                    }
                }
                converted_games.append(converted)
            
            return converted_games

        except Exception as e:
            print(f"Error fetching from football-data.org: {e}")
            if '403' in str(e):
                print("Tip: Check if your API key has access to this competition.")
            return []

    def _fetch_college_data(self, path: str, year: int, week: Optional[int] = None) -> List[Dict]:
        """Generic fetcher for college sports (CFB, CBB)."""
        endpoint = f"{self.base_url}{path}"
        params = {'year': year}
        if week: params['week'] = week
        
        try:
            print(f"Fetching College Data from: {endpoint}")
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Check for HTML response (documentation page) error
            if 'application/json' not in response.headers.get('Content-Type', ''):
                print("ERROR: Received HTML instead of JSON. Check URL.")
                return []

            data = response.json()
            converted_games = []
            
            for game in data:
                # Simple validation to skip bad historical data
                if game.get('season') == year:
                    converted_game = {
                        'fixture': {
                            'id': game.get('id', 0),
                            'date': game.get('startDate', ''),
                            'status': {'long': 'completed' if game.get('completed') else 'scheduled'},
                            'venue': {'name': game.get('venue') or 'TBD'}
                        },
                        'league': {
                            'id': 0,
                            'name': 'College Football' if self.sport_type == 'college_football' else 'College Basketball',
                            'season': game.get('season', year)
                        },
                        'teams': {
                            'home': {'id': game.get('homeId', 0), 'name': game.get('homeTeam', 'TBD')},
                            'away': {'id': game.get('awayId', 0), 'name': game.get('awayTeam', 'TBD')}
                        },
                        'goals': {
                            'home': game.get('homePoints'),
                            'away': game.get('awayPoints')
                        }
                    }
                    converted_games.append(converted_game)
            
            return converted_games
            
        except Exception as e:
            print(f"Error fetching college games: {e}")
            return []

    def store_match(self, match_data: Dict):
        """Store match data in SQLite database."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            f = match_data['fixture']
            l = match_data['league']
            t = match_data['teams']
            g = match_data['goals']
            
            print(f"Storing: {t['home']['name']} vs {t['away']['name']}")
            
            cursor.execute('''
                INSERT OR REPLACE INTO matches 
                (match_id, sport_type, league_id, league_name, season, match_date,
                 home_team_id, home_team_name, away_team_id, away_team_name,
                 home_score, away_score, status, venue, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f['id'], self.sport_type, l['id'], l['name'], l['season'], f['date'],
                t['home']['id'], t['home']['name'], t['away']['id'], t['away']['name'],
                g['home'], g['away'], f['status']['long'], f['venue']['name'],
                datetime.now().isoformat()
            ))
            conn.commit()
        except Exception as e:
            print(f"Error storing match: {e}")
        finally:
            conn.close()

    # --- Placeholder methods for Stats/Odds ---
    # Since football-data.org free tier handles stats/odds differently, 
    # these are placeholders to prevent the app from crashing.
    
    def fetch_stats(self, match_id: int): 
        return None
    
    def fetch_odds(self, match_id: int): 
        return None
    
    def store_stats(self, match_id, data): 
        pass
    
    def store_odds(self, match_id, data): 
        pass
    
    def refresh_data_for_match(self, match_id): 
        # For football-data.org, detailed refresh logic would go here
        print(f"Refresh requested for match {match_id} (Not available on free tier)")
        pass
    
    def get_recent_matches(self, team_id: int, limit: int = 5) -> List[Dict]:
        """Get recent matches for a team from DB."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM matches 
            WHERE (home_team_id = ? OR away_team_id = ?)
            AND (status = 'FINISHED' OR status = 'completed' OR status = 'Match Finished')
            ORDER BY match_date DESC
            LIMIT ?
        ''', (team_id, team_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]