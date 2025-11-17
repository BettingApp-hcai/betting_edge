import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from data_agent import DataAgent
from dotenv import load_dotenv  # <-- Import this

load_dotenv()  # <-- Load the .env file

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
    st.session_state.api_key_football = os.getenv("API_KEY_FOOTBALL", "KEY_NOT_FOUND") # <-- Read from os.getenv
if 'api_key_cfb' not in st.session_state:
    st.session_state.api_key_cfb = os.getenv("API_KEY_CFB", "KEY_NOT_FOUND") # <-- Read from os.getenv
if 'data_agent' not in st.session_state:
    st.session_state.data_agent = None
if 'sport_type' not in st.session_state:
    st.session_state.sport_type = "football"
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False

def init_data_agent(sport_type: str = "football"):
    """Initialize the data agent with API key."""
    try:
        st.session_state.data_agent = DataAgent(sport_type=sport_type)
        st.session_state.sport_type = sport_type
        st.session_state.db_initialized = True
        return True
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        return False

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect("betting_edge.db")

# In streamlit_app.py

def fetch_matches_from_db(sport_type: str, include_past=True, include_future=True, limit=100):
    """Fetch matches from database with filtering options."""
    conn = get_db_connection()
    
    # --- MODIFICATION START ---
    params = [sport_type] # Start with sport_type as the first parameter
    conditions = ["sport_type = ?"] # Start with the sport_type filter
    
    if not include_past:
        conditions.append("match_date >= datetime('now')")
    if not include_future:
        conditions.append("match_date < datetime('now')")
    
    where_clause = f"WHERE {' AND '.join(conditions)}"
    
    query = f"""
        SELECT match_id, league_name, match_date, 
               home_team_name, away_team_name, 
               home_score, away_score, status
        FROM matches
        {where_clause}
        ORDER BY match_date DESC
        LIMIT ?
    """
    params.append(limit) # Add limit as the last parameter
    
    df = pd.read_sql_query(query, conn, params=tuple(params)) # Pass params tuple
    # --- MODIFICATION END ---
    
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
st.markdown("*AI-Powered Sports Betting Intelligence System*")
st.divider()

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Sport Type Selection
    sport_type = st.radio(
        "Select Sport",
        options=["football", "college_football"],
        format_func=lambda x: "⚽ Soccer (API-Football)" if x == "football" else "🏈 College Football",
        index=0 if st.session_state.sport_type == "football" else 1
    )
    
    # API Key Display (masked)
    if sport_type == "football":
        current_key = st.session_state.api_key_football
        st.text_input(
            "API-Football Key",
            value="****" + current_key[-8:],
            disabled=True,
            help="Pre-configured API key"
        )
    else:
        current_key = st.session_state.api_key_cfb
        st.text_input(
            "College Football Key",
            value="****" + current_key[-8:],
            disabled=True,
            help="Pre-configured API key"
        )
    
    if st.button("🔌 Initialize Agent"):
        with st.spinner("Initializing..."):
            if init_data_agent(sport_type):
                st.success(f"✅ {sport_type.replace('_', ' ').title()} Agent Connected!")
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
                min_value=2020,
                max_value=2025,
                value=2023,
                help="Free plan supports 2021-2023. For most leagues, use the year the season starts"
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
                            for match in matches[:50]:  # Limit to 50 to avoid rate limits
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
        
        else:  # college_football
            year = st.number_input(
                "Year",
                min_value=2020,
                max_value=2025,
                value=2024,
                help="College football season year"
            )
            
            week = st.number_input(
                "Week (optional)",
                min_value=0,
                max_value=15,
                value=0,
                help="Leave at 0 for all weeks, or specify a week number"
            )
            
            if st.button("📥 Fetch Games"):
                with st.spinner(f"Fetching CFB games for {year}..."):
                    try:
                        # First, let's test the raw API response
                        if st.session_state.data_agent:
                            import requests
                            test_url = f"{st.session_state.data_agent.base_url}/games"
                            test_params = {'year': year, 'week': 1}  # Just week 1 for testing
                            
                            with st.expander("🔍 API Test (Week 1 sample)"):
                                test_response = requests.get(
                                    test_url, 
                                    headers=st.session_state.data_agent.headers, 
                                    params=test_params
                                )
                                if test_response.status_code == 200:
                                    test_data = test_response.json()
                                    if test_data and len(test_data) > 0:
                                        st.json(test_data[0])  # Show first game
                                    else:
                                        st.warning("No data returned")
                                else:
                                    st.error(f"API Error: {test_response.status_code}")
                        
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
tab1, tab2, tab3, tab4 = st.tabs(["🏠 Dashboard", "⚽ Matches", "📊 Statistics", "💰 Odds"])

with tab1:
    st.header("Dashboard Overview")
    
    if os.path.exists("betting_edge.db"):
        col1, col2, col3 = st.columns(3)
        
        conn = get_db_connection()
        
        # Recent matches count
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM matches 
            WHERE match_date >= datetime('now', '-7 days')
        """)
        recent_matches = cursor.fetchone()[0]
        
        # Upcoming matches count
        cursor.execute("""
            SELECT COUNT(*) FROM matches 
            WHERE match_date >= datetime('now')
            AND status NOT IN ('Match Finished', 'Match Cancelled')
        """)
        upcoming_matches = cursor.fetchone()[0]
        
        # Total odds entries
        cursor.execute("SELECT COUNT(DISTINCT match_id) FROM odds")
        matches_with_odds = cursor.fetchone()[0]
        
        conn.close()
        
        with col1:
            st.metric("Recent Matches (7 days)", recent_matches, delta="Live")
        
        with col2:
            st.metric("Upcoming Matches", upcoming_matches, delta="Scheduled")
        
        with col3:
            st.metric("Matches with Odds", matches_with_odds, delta="Ready")
        
        st.divider()
        
        # Recent matches table
        st.subheader("📅 Latest Matches")
        
        # Add filter options
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_past = st.checkbox("Past", value=True, key="dash_past")
        with col_f2:
            filter_future = st.checkbox("Future", value=True, key="dash_future")
        with col_f3:
            show_count = st.slider("Show", 10, 100, 20)
        
        matches_df = fetch_matches_from_db(
            sport_type=st.session_state.sport_type, # <-- ADD THIS
            include_past=filter_past, 
            include_future=filter_future,
            limit=show_count
        )
        
        if not matches_df.empty:
            # Debug: Show raw data sample
            with st.expander("🔍 Debug: View Raw Data Sample"):
                st.dataframe(matches_df.head(5), use_container_width=True)
            
            # Format the display
            matches_df['match_date'] = pd.to_datetime(matches_df['match_date']).dt.strftime('%Y-%m-%d %H:%M')
            matches_df['Score'] = matches_df.apply(
                lambda x: f"{x['home_score']} - {x['away_score']}" 
                if pd.notna(x['home_score']) else "vs", 
                axis=1
            )
            
            display_df = matches_df[[
                'league_name', 'match_date', 'home_team_name', 
                'Score', 'away_team_name', 'status'
            ]].head(20)
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No matches in database. Use the sidebar to fetch data.")
    else:
        st.info("🔧 Initialize the database by entering your API key in the sidebar.")

with tab2:
    st.header("Match Details")
    
    # Add filters
    col1, col2 = st.columns(2)
    with col1:
        show_past = st.checkbox("Show Past Matches", value=True)
    with col2:
        show_future = st.checkbox("Show Future Matches", value=True)
    
    if os.path.exists("betting_edge.db"):
        matches_df = fetch_matches_from_db(
            sport_type=st.session_state.sport_type, # <-- ADD THIS
            include_past=show_past, 
            include_future=show_future
        )
        
        if not matches_df.empty and len(matches_df) > 0:
            st.info(f"Showing {len(matches_df)} matches")
            
            # Create match selector
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
                match_id = selected_match['match_id']
                
                # Display match info
                col1, col2, col3 = st.columns([2, 1, 2])
                
                with col1:
                    st.subheader(selected_match['home_team_name'])
                    st.metric("Home Score", selected_match['home_score'] if pd.notna(selected_match['home_score']) else "-")
                
                with col2:
                    st.markdown("<h3 style='text-align: center;'>VS</h3>", unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align: center;'>{selected_match['status']}</p>", unsafe_allow_html=True)
                
                with col3:
                    st.subheader(selected_match['away_team_name'])
                    st.metric("Away Score", selected_match['away_score'] if pd.notna(selected_match['away_score']) else "-")
                
                st.divider()
                
                # Fetch detailed stats if available
                if st.session_state.data_agent:
                    if st.button("🔄 Refresh Match Data"):
                        with st.spinner("Fetching latest data..."):
                            try:
                                st.session_state.data_agent.refresh_data_for_match(match_id)
                                st.success("Data refreshed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                
                # Display stats
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
                    st.info("No statistics available for this match")
        else:
            st.info("No matches available. Use the sidebar to fetch data.")
    else:
        st.info("Database not initialized")

with tab3:
    st.header("Team Statistics")
    
    if os.path.exists("betting_edge.db"):
        conn = get_db_connection()
        
        # --- MODIFICATION START ---
        # Get unique teams FOR THE CURRENT SPORT
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
        # Pass the sport_type as a parameter twice (for the UNION)
        teams_df = pd.read_sql_query(query, conn, params=(st.session_state.sport_type, st.session_state.sport_type))
        # --- MODIFICATION END ---
        
        conn.close()
        
        if not teams_df.empty:
            selected_team = st.selectbox(
                "Select a team",
                teams_df['team_name'].tolist()
            )
            
            if selected_team:
                team_id = teams_df[teams_df['team_name'] == selected_team]['team_id'].iloc[0]
                
                # Get team's recent matches
                if st.session_state.data_agent:
                    recent_matches = st.session_state.data_agent.get_recent_matches(team_id, limit=10)
                    
                    if recent_matches:
                        st.subheader(f"Recent Form - {selected_team}")
                        
                        # Calculate form
                        wins = sum(1 for m in recent_matches if 
                                 (m['home_team_id'] == team_id and m['home_score'] > m['away_score']) or
                                 (m['away_team_id'] == team_id and m['away_score'] > m['home_score']))
                        
                        draws = sum(1 for m in recent_matches if m['home_score'] == m['away_score'])
                        losses = len(recent_matches) - wins - draws
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Wins", wins, delta=f"{wins/len(recent_matches)*100:.0f}%")
                        col2.metric("Draws", draws)
                        col3.metric("Losses", losses)
                        
                        # Display recent matches
                        st.dataframe(
                            pd.DataFrame(recent_matches)[[
                                'match_date', 'home_team_name', 'home_score', 
                                'away_score', 'away_team_name'
                            ]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No recent matches found")
        else:
            st.info("No teams in database")
    else:
        st.info("Database not initialized")

with tab4:
    st.header("Betting Odds")
    
    if os.path.exists("betting_edge.db"):
        matches_df = fetch_matches_from_db(sport_type=st.session_state.sport_type)
        
        if not matches_df.empty and len(matches_df) > 0:
            # Filter matches with odds
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
                    lambda x: f"{x['home_team_name']} vs {x['away_team_name']}",
                    axis=1
                ).tolist()
                
                selected_match_idx = st.selectbox(
                    "Select a match to view odds",
                    range(len(match_options)),
                    format_func=lambda x: match_options[x]
                )
                
                if selected_match_idx is not None:
                    selected_match = matches_with_odds_df.iloc[selected_match_idx]
                    match_id = selected_match['match_id']
                    
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
                        
                        # Calculate implied probabilities
                        st.subheader("Implied Probabilities")
                        avg_home = odds_df['home_odds'].mean()
                        avg_draw = odds_df['draw_odds'].mean()
                        avg_away = odds_df['away_odds'].mean()
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Home Win", f"{(1/avg_home)*100:.1f}%")
                        col2.metric("Draw", f"{(1/avg_draw)*100:.1f}%")
                        col3.metric("Away Win", f"{(1/avg_away)*100:.1f}%")
                    else:
                        st.info("No odds data available")
            else:
                st.info("No matches with odds data. Fetch odds using the Data Agent.")
        else:
            st.info("No matches in database")
    else:
        st.info("Database not initialized")

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: gray;'>
    Built by Siddhant, Aryan, Ameya & Gautam | Syracuse University
    </div>
""", unsafe_allow_html=True)