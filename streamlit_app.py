# /streamlit_app.py
import dotenv
dotenv.load_dotenv()

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from data_agent import DataAgent
from dotenv import load_dotenv 
from typing import Optional

load_dotenv() 

# Page configuration
st.set_page_config(
    page_title="Betting Edge",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state from environment variables
if 'api_key_football' not in st.session_state:
    st.session_state.api_key_football = os.getenv("API_KEY_FOOTBALL", "KEY_NOT_FOUND")
if 'api_key_cfb' not in st.session_state:
    st.session_state.api_key_cfb = os.getenv("API_KEY_CFB", "KEY_NOT_FOUND")
# --- MODIFICATION ---
if 'api_key_basketball' not in st.session_state:
    st.session_state.api_key_basketball = os.getenv("API_KEY_BASKETBALL", "KEY_NOT_FOUND")
# --- END MODIFICATION ---
if 'data_agent' not in st.session_state:
    st.session_state.data_agent = None
if 'sport_type' not in st.session_state:
    st.session_state.sport_type = "football"
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False

def init_data_agent(sport_type: str = "football"):
    """Initialize the data agent with API key."""
    try:
        # Pass the check_same_thread=False to the connect call in data_agent
        st.session_state.data_agent = DataAgent(sport_type=sport_type, db_path="betting_edge.db")
        st.session_state.sport_type = sport_type
        st.session_state.db_initialized = True
        return True
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        return False

def get_db_connection():
    """Get database connection."""
    # check_same_thread=False is needed for Streamlit's threading
    return sqlite3.connect("betting_edge.db", check_same_thread=False)

def get_unique_leagues(sport_type: str):
    """Get all unique leagues for the selected sport_type from the DB."""
    if not os.path.exists("betting_edge.db"):
        return ["All Leagues"]
    conn = get_db_connection()
    query = "SELECT DISTINCT league_name FROM matches WHERE sport_type = ? ORDER BY league_name"
    try:
        df = pd.read_sql_query(query, conn, params=(sport_type,))
        conn.close()
        return ["All Leagues"] + df['league_name'].tolist()
    except Exception as e:
        print(f"Error getting unique leagues: {e}")
        conn.close()
        return ["All Leagues"]

def fetch_matches_from_db(sport_type: str, 
                          league_name: Optional[str] = None, 
                          selected_year: Optional[int] = None, # <-- NEW PARAMETER
                          include_past=True, include_future=True, limit=100):
    """Fetch matches from database with filtering options."""
    conn = get_db_connection()
    
    params = [sport_type]
    conditions = ["sport_type = ?"]
    
    if not include_past:
        conditions.append("match_date >= datetime('now')")
    if not include_future:
        conditions.append("match_date < datetime('now')")
    
    if league_name and league_name != "All Leagues":
        conditions.append("league_name = ?")
        params.append(league_name)
    
    # --- MODIFICATION START ---
    # Add year filter for college sports
    if selected_year and (sport_type == "college_football" or sport_type == "basketball"):
        conditions.append("season = ?") # The 'season' column stores the year for college sports
        params.append(selected_year)
    # --- MODIFICATION END ---
        
    where_clause = f"WHERE {' AND '.join(conditions)}"
    
    query = f"""
        SELECT match_id, league_name, match_date, 
               home_team_name, away_team_name, 
               home_score, away_score, status, season
        FROM matches
        {where_clause}
        ORDER BY match_date DESC
        LIMIT ?
    """
    params.append(limit)
    
    df = pd.read_sql_query(query, conn, params=tuple(params))
    conn.close()
    return df

def fetch_match_stats(match_id: int):
    """Fetch statistics for a specific match."""
    conn = get_db_connection()
    query = """
        SELECT team_name, shots_on_goal, total_shots, 
               ball_possession, corner_kicks, fouls,
               yellow_cards, red_cards, total_passes, passes_accurate
        FROM match_stats
        WHERE match_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(match_id,))
    conn.close()
    return df

def fetch_odds(match_id: int):
    """Fetch odds for a specific match."""
    conn = get_db_connection()
    query = """
        SELECT bookmaker, home_odds, draw_odds, away_odds
        FROM odds
        WHERE match_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(match_id,))
    conn.close()
    return df

# Main App Header
st.markdown('<div class="main-header">⚽ Betting Edge</div>', unsafe_allow_html=True)
st.markdown("*AI-Powered Sports Intelligence System*")
st.divider()

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # --- MODIFICATION: Add basketball ---
    sport_type = st.radio(
        "Select Sport",
        options=["football", "college_football", "basketball"],
        format_func=lambda x: {
            "football": "⚽ Soccer (API-Football)",
            "college_football": "🏈 College Football",
            "basketball": "🏀 College Basketball"
        }.get(x),
        index=["football", "college_football", "basketball"].index(st.session_state.sport_type)
    )
    # --- END MODIFICATION ---
    
    # API Key Display (masked)
    if sport_type == "football":
        current_key = st.session_state.api_key_football
        st.text_input(
            "API-Football Key",
            value="****" + current_key[-8:] if current_key != "KEY_NOT_FOUND" else "Not Set",
            disabled=True,
            help="Pre-configured API key"
        )
    # --- MODIFICATION: Add basketball key display ---
    elif sport_type == "college_football":
        current_key = st.session_state.api_key_cfb
        st.text_input(
            "College Football Key",
            value="****" + current_key[-8:] if current_key != "KEY_NOT_FOUND" else "Not Set",
            disabled=True,
            help="Pre-configured API key"
        )
    elif sport_type == "basketball":
        current_key = st.session_state.api_key_basketball
        st.text_input(
            "College Basketball Key",
            value="****" + current_key[-8:] if current_key != "KEY_NOT_FOUND" else "Not Set",
            disabled=True,
            help="Pre-configured API key"
        )
    # --- END MODIFICATION ---
    
    if st.button("🔌 Initialize Agent"):
        with st.spinner("Initializing..."):
            if init_data_agent(sport_type):
                st.success(f"✅ {sport_type.replace('_', ' ').title()} Agent Connected!")
                st.rerun() # Rerun to update the rest of the UI
            else:
                st.error("Failed to initialize agent")
    
    st.divider()
    
    # Database Status
    st.subheader("📊 Database Status")
    if os.path.exists("betting_edge.db"):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM matches")
        match_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM match_stats")
        stats_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM odds")
        odds_count = cursor.fetchone()[0]
        
        conn.close()
        
        st.metric("Matches", match_count)
        st.metric("Statistics", stats_count)
        st.metric("Odds Entries", odds_count)
    else:
        st.info("Database not yet initialized")
    
    st.divider()
    
    # Data Fetching Section
    if st.session_state.data_agent:
        st.subheader("🔄 Fetch Data")
        
        if st.session_state.sport_type == "football":
            # Soccer leagues
            league_options = {
                "Premier League": 39,
                "La Liga": 140,
                "Serie A": 135,
                "Bundesliga": 78,
                "Ligue 1": 61
            }
            
            selected_league = st.selectbox(
                "Select League",
                options=list(league_options.keys())
            )
            
            season = st.number_input(
                "Season",
                min_value=2000,
                max_value=2025,
                value=2023,
                help="Use the year the season starts"
            )
            
            # Date range for better filtering
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                from_date = st.date_input(
                    "From Date",
                    value=datetime.now() - timedelta(days=30),
                    help="Fetch matches from this date"
                )
            with col_date2:
                to_date = st.date_input(
                    "To Date", 
                    value=datetime.now() + timedelta(days=7),
                    help="Fetch matches until this date"
                )
            
            if st.button("📥 Fetch Matches"):
                with st.spinner(f"Fetching {selected_league} matches..."):
                    try:
                        league_id = league_options[selected_league]
                        matches = st.session_state.data_agent.fetch_matches(
                            league_id=league_id, 
                            season=season,
                            from_date=from_date.strftime('%Y-%m-%d'),
                            to_date=to_date.strftime('%Y-%m-%d')
                        )
                        
                        if matches:
                            st.info(f"Found {len(matches)} matches. Storing in database...")
                            stored_count = 0
                            for match in matches[:50]:
                                try:
                                    st.session_state.data_agent.store_match(match)
                                    stored_count += 1
                                except Exception as e:
                                    st.warning(f"Error storing match: {e}")
                                    continue
                            
                            st.success(f"✅ Stored {stored_count} matches!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning(f"No matches found for {selected_league} season {season}")
                            st.info("Try adjusting the date range or season year")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        st.info("This might be an API rate limit or invalid season. Try again in a moment.")
        
        # --- MODIFICATION: Grouped CFB and CBB ---
        else:  # college_football or basketball
            sport_name = st.session_state.sport_type.replace('_', ' ').title()
            
            # --- MODIFICATION START ---
            # Define year input and store it in session state
            current_year_value = st.session_state.get('selected_fetch_year', datetime.now().year)
            year = st.number_input(
                "Year",
                min_value=2000,
                max_value=2025,
                value=current_year_value,
                help=f"{sport_name} season year",
                key="sidebar_fetch_year_input" # Add a key
            )
            st.session_state.selected_fetch_year = year # Store the value
            # --- MODIFICATION END ---
            
            week = st.number_input(
                "Week (optional)",
                min_value=0,
                max_value=18, 
                value=0,
                help="Leave at 0 for all weeks, or specify a week number"
            )
            
            if st.button(f"📥 Fetch {sport_name} Games"):
                with st.spinner(f"Fetching {sport_name} games for {year}..."):
                    try:
                        # --- MODIFICATION START ---
                        # First, let's test the raw API response
                        if st.session_state.data_agent:
                            import requests
                            import json 
                            
                            # Dynamically set test path
                            if st.session_state.sport_type == "college_football":
                                test_path = "/games"
                            else: # basketball
                                test_path = "/games" # <-- THE FIX IS HERE
                                
                            test_url = f"{st.session_state.data_agent.base_url}{test_path}"
                            test_params = {'year': year, 'week': 1}  # Just week 1 for testing
                            
                            with st.expander("🔍 API Test (Week 1 sample)"):
                                try:
                                    st.write(f"Testing URL: {test_url}") # Will now show the correct URL
                                    test_response = requests.get(
                                        test_url, 
                                        headers=st.session_state.data_agent.headers, 
                                        params=test_params
                                    )
                                    st.write(f"Response Status: {test_response.status_code}")
                                    
                                    # Check content type
                                    content_type = test_response.headers.get('Content-Type', '')
                                    st.write(f"Content-Type: {content_type}")

                                    if 'application/json' in content_type:
                                        test_data = test_response.json()
                                        if test_data and len(test_data) > 0:
                                            st.json(test_data[0])  # Show first game
                                        else:
                                            st.warning("No data returned")
                                    else:
                                        st.error("API did not return JSON. See raw text below:")
                                        st.code(test_response.text[:1000]) # Show first 1000 chars

                                except json.JSONDecodeError as e:
                                    st.error(f"JSON PARSING FAILED: {e}")
                                    st.error("This usually means an invalid API key or bad request. See raw text below:")
                                    st.code(test_response.text[:1000]) # Show first 1000 chars
                                except requests.RequestException as e:
                                    st.error(f"API Request Failed: {e}")
                        # --- MODIFICATION END ---
                        
                        games = st.session_state.data_agent.fetch_matches(
                            year=year,
                            week=week if week > 0 else None
                        )
                        
                        if games:
                            st.info(f"Found {len(games)} games. Storing in database...")
                            stored_count = 0
                            for game in games:
                                try:
                                    st.session_state.data_agent.store_match(game)
                                    stored_count += 1
                                except Exception as e:
                                    st.warning(f"Error storing game: {e}")
                                    continue
                            
                            st.success(f"✅ Stored {stored_count} games!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning(f"No games found for {year}")
                            st.info("Try a different year or check your API key")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        st.info("Check the terminal for detailed error messages")

# Main Content Area
# --- MODIFICATION: Added check for agent initialization ---
if not st.session_state.data_agent:
    st.info("👋 Welcome! Please select a sport and click 'Initialize Agent' in the sidebar to begin.")
else:
    # All tabs are now nested inside this 'else' block
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Dashboard", "⚽ Matches", "📊 Statistics", "💰 Odds"])

    with tab1:
        st.header(f"Dashboard Overview ({st.session_state.sport_type.replace('_', ' ').title()})")
        
        if os.path.exists("betting_edge.db"):
            col1, col2, col3 = st.columns(3)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # --- MODIFICATION: All metrics are now filtered by sport_type ---
            cursor.execute("""
                SELECT COUNT(*) FROM matches 
                WHERE match_date >= datetime('now', '-7 days')
                AND sport_type = ?
            """, (st.session_state.sport_type,))
            recent_matches = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM matches 
                WHERE match_date >= datetime('now')
                AND status NOT IN ('Match Finished', 'Match Cancelled', 'completed')
                AND sport_type = ?
            """, (st.session_state.sport_type,))
            upcoming_matches = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT m.match_id) 
                FROM odds o
                JOIN matches m ON o.match_id = m.match_id
                WHERE m.sport_type = ?
            """, (st.session_state.sport_type,))
            matches_with_odds = cursor.fetchone()[0]
            # --- END MODIFICATION ---
            
            conn.close()
            
            with col1:
                st.metric("Recent Matches (7 days)", recent_matches)
            with col2:
                st.metric("Upcoming Matches", upcoming_matches)
            with col3:
                st.metric("Matches with Odds", matches_with_odds)
            
            st.divider()
            
            st.subheader("📅 Latest Matches")
            
            leagues = get_unique_leagues(st.session_state.sport_type)
            
            col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 2])
            with col_f1:
                selected_league_filter = st.selectbox(
                    "Filter by League", 
                    options=leagues, 
                    key="dash_league_filter"
                )
            with col_f2:
                filter_past = st.checkbox("Past", value=True, key="dash_past")
            with col_f3:
                filter_future = st.checkbox("Future", value=True, key="dash_future")
            with col_f4:
                show_count = st.slider("Show", 10, 100, 20)

            matches_df = fetch_matches_from_db(
                sport_type=st.session_state.sport_type,
                league_name=selected_league_filter,
                selected_year=year if st.session_state.sport_type in ["college_football", "basketball"] else None, # <-- NEW
                include_past=filter_past, 
                include_future=filter_future,
                limit=show_count
            )
            
            if not matches_df.empty:
                with st.expander("🔍 Debug: View Raw Data Sample"):
                    st.dataframe(matches_df.head(5), use_container_width=True)
                
                matches_df['match_date'] = pd.to_datetime(matches_df['match_date']).dt.strftime('%Y-%m-%d %H:%M')
                matches_df['Score'] = matches_df.apply(
                    lambda x: f"{int(x['home_score'])} - {int(x['away_score'])}" 
                    if pd.notna(x['home_score']) else "vs", 
                    axis=1
                )
                
                display_df = matches_df[[
                    'league_name', 'match_date', 'home_team_name', 
                    'Score', 'away_team_name', 'status'
                ]].head(show_count)
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No matches in database for this sport. Use the sidebar to fetch data.")
        else:
            st.info("🔧 Database not found. Initialize an agent in the sidebar.")

    with tab2:
        st.header("Match Details")
        
        col1, col2 = st.columns(2)
        with col1:
            show_past = st.checkbox("Show Past Matches", value=True, key="tab2_past")
        with col2:
            show_future = st.checkbox("Show Future Matches", value=True, key="tab2_future")
        
        if os.path.exists("betting_edge.db"):
            matches_df = fetch_matches_from_db(
                sport_type=st.session_state.sport_type,
                league_name="All Leagues",
                include_past=show_past, 
                include_future=show_future,
                limit=500 # Get more for the selector
            )
            
            if not matches_df.empty and len(matches_df) > 0:
                match_options = matches_df.apply(
                    lambda x: f"{x['home_team_name']} vs {x['away_team_name']} ({x['match_date'][:10] if x['match_date'] and len(str(x['match_date'])) >= 10 else 'TBD'}) - {x['status']}",
                    axis=1
                ).tolist()
                
                selected_match_idx = st.selectbox(
                    "Select a match to view details",
                    range(len(match_options)),
                    format_func=lambda x: match_options[x]
                )
                
                if selected_match_idx is not None:
                    selected_match = matches_df.iloc[selected_match_idx]
                    match_id = int(selected_match['match_id']) # Ensure it's an int
                    
                    col1, col2, col3 = st.columns([2, 1, 2])
                    
                    with col1:
                        st.subheader(selected_match['home_team_name'])
                        st.metric("Home Score", int(selected_match['home_score']) if pd.notna(selected_match['home_score']) else "-")
                    
                    with col2:
                        st.markdown("<h3 style='text-align: center;'>VS</h3>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align: center;'>{selected_match['status']}</p>", unsafe_allow_html=True)
                    
                    with col3:
                        st.subheader(selected_match['away_team_name'])
                        st.metric("Away Score", int(selected_match['away_score']) if pd.notna(selected_match['away_score']) else "-")
                    
                    st.divider()
                    
                    # Only show refresh button for football
                    if st.session_state.sport_type == 'football':
                        if st.button("🔄 Refresh Match Data (Odds/Stats)"):
                            with st.spinner("Fetching latest data..."):
                                try:
                                    st.session_state.data_agent.refresh_data_for_match(match_id)
                                    st.success("Data refreshed!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    # Display stats (football only)
                    if st.session_state.sport_type == 'football':
                        stats_df = fetch_match_stats(match_id)
                        if not stats_df.empty:
                            st.subheader("📊 Match Statistics")
                            col1, col2 = st.columns(2)
                            for idx, row in stats_df.iterrows():
                                with col1 if idx == 0 else col2:
                                    st.markdown(f"**{row['team_name']}**")
                                    st.metric("Shots on Goal", int(row['shots_on_goal']) if pd.notna(row['shots_on_goal']) else 0)
                                    st.metric("Possession %", f"{int(row['ball_possession']) if pd.notna(row['ball_possession']) else 0}%")
                                    st.metric("Pass Accuracy", f"{int(row['passes_accurate']) if pd.notna(row['passes_accurate']) else 0}/{int(row['total_passes']) if pd.notna(row['total_passes']) else 0}")
                                    st.metric("Corners", int(row['corner_kicks']) if pd.notna(row['corner_kicks']) else 0)
                        else:
                            st.info("No detailed statistics available for this match (or not supported for this sport).")
            else:
                st.info("No matches available for this sport. Use the sidebar to fetch data.")
        else:
            st.info("Database not initialized")

    with tab3:
        st.header("Team Statistics")
        
        if os.path.exists("betting_edge.db"):
            conn = get_db_connection()
            
            # Get unique teams for the current sport
            query = """
                SELECT DISTINCT home_team_name as team_name, home_team_id as team_id
                FROM matches
                WHERE sport_type = ?
                UNION
                SELECT DISTINCT away_team_name as team_name, away_team_id as team_id
                FROM matches
                WHERE sport_type = ?
                ORDER BY team_name
            """
            teams_df = pd.read_sql_query(query, conn, params=(st.session_state.sport_type, st.session_state.sport_type))
            conn.close()
            
            if not teams_df.empty:
                selected_team = st.selectbox(
                    "Select a team",
                    teams_df['team_name'].tolist(),
                    key="tab3_team_select"
                )
                
                if selected_team:
                    team_id = int(teams_df[teams_df['team_name'] == selected_team]['team_id'].iloc[0])
                    
                    if st.session_state.data_agent:
                        recent_matches = st.session_state.data_agent.get_recent_matches(team_id, limit=10)
                        
                        if recent_matches:
                            st.subheader(f"Recent Form (Last {len(recent_matches)} Games) - {selected_team}")
                            
                            wins = sum(1 for m in recent_matches if 
                                     (m['home_team_id'] == team_id and m['home_score'] > m['away_score']) or
                                     (m['away_team_id'] == team_id and m['away_score'] > m['home_score']))
                            
                            # Draws (N/A for CBB/CFB, but logic is safe)
                            draws = sum(1 for m in recent_matches if m['home_score'] == m['away_score'] and st.session_state.sport_type == 'football')
                            losses = len(recent_matches) - wins - draws
                            
                            col1, col2, col3 = st.columns(3)
                            win_pct = (wins / len(recent_matches) * 100) if len(recent_matches) > 0 else 0
                            col1.metric("Wins", wins, delta=f"{win_pct:.0f}%")
                            if st.session_state.sport_type == 'football':
                                col2.metric("Draws", draws)
                            col3.metric("Losses", losses)
                            
                            st.dataframe(
                                pd.DataFrame(recent_matches)[[
                                    'match_date', 'home_team_name', 'home_score', 
                                    'away_score', 'away_team_name', 'status'
                                ]],
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info(f"No recent *finished* matches found for {selected_team}")
            else:
                st.info("No teams in database for this sport.")
        else:
            st.info("Database not initialized")

    with tab4:
        st.header("Betting Odds (Football Only)")
        
        # --- MODIFICATION: Show this tab only for football ---
        if st.session_state.sport_type != 'football':
            st.info("Odds data is currently only supported for Soccer (API-Football).")
        else:
            if os.path.exists("betting_edge.db"):
                matches_df = fetch_matches_from_db(
                    sport_type=st.session_state.sport_type,
                    league_name="All Leagues"
                )
                
                if not matches_df.empty and len(matches_df) > 0:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT match_id FROM odds")
                    matches_with_odds = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    
                    if matches_with_odds:
                        matches_with_odds_df = matches_df[matches_df['match_id'].isin(matches_with_odds)]
                    else:
                        matches_with_odds_df = pd.DataFrame()
                    
                    if not matches_with_odds_df.empty and len(matches_with_odds_df) > 0:
                        match_options = matches_with_odds_df.apply(
                            lambda x: f"{x['home_team_name']} vs {x['away_team_name']} ({x['match_date'][:10]})",
                            axis=1
                        ).tolist()
                        
                        selected_match_idx = st.selectbox(
                            "Select a match to view odds",
                            range(len(match_options)),
                            format_func=lambda x: match_options[x],
                            key="tab4_match_select"
                        )
                        
                        if selected_match_idx is not None:
                            selected_match = matches_with_odds_df.iloc[selected_match_idx]
                            match_id = int(selected_match['match_id'])
                            
                            st.subheader(f"{selected_match['home_team_name']} vs {selected_match['away_team_name']}")
                            
                            odds_df = fetch_odds(match_id)
                            
                            if not odds_df.empty:
                                st.dataframe(
                                    odds_df,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "home_odds": st.column_config.NumberColumn("Home Win", format="%.2f"),
                                        "draw_odds": st.column_config.NumberColumn("Draw", format="%.2f"),
                                        "away_odds": st.column_config.NumberColumn("Away Win", format="%.2f")
                                    }
                                )
                                
                                st.subheader("Implied Probabilities (Average)")
                                avg_home = odds_df['home_odds'].mean()
                                avg_draw = odds_df['draw_odds'].mean()
                                avg_away = odds_df['away_odds'].mean()
                                
                                col1, col2, col3 = st.columns(3)
                                col1.metric("Home Win", f"{(1/avg_home)*100:.1f}%")
                                col2.metric("Draw", f"{(1/avg_draw)*100:.1f}%")
                                col3.metric("Away Win", f"{(1/avg_away)*100:.1f}%")
                            else:
                                st.info("No odds data available for this match.")
                    else:
                        st.info("No matches with odds data found. Please refresh matches in Tab 2.")
                else:
                    st.info("No matches in database for this sport.")
            else:
                st.info("Database not initialized")
        # --- END MODIFICATION ---

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: gray;'>
    Built by Siddhant, Aryan, Ameya & Gautam | Syracuse University
    </div>
""", unsafe_allow_html=True)