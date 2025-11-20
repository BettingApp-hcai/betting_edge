# /streamlit_app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from data_agent import DataAgent
from dotenv import load_dotenv
from typing import Optional

# Existing query agent import (still used inside the pipeline)
from query_agent import parse_user_query

# New unified multi agent flow
from pipelines.pipeline import BettingEdgePipeline

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
if "api_key_football" not in st.session_state:
    st.session_state.api_key_football = os.getenv("API_KEY_FOOTBALL", "KEY_NOT_FOUND")
if "api_key_cfb" not in st.session_state:
    st.session_state.api_key_cfb = os.getenv("API_KEY_CFB", "KEY_NOT_FOUND")
if "api_key_basketball" not in st.session_state:
    st.session_state.api_key_basketball = os.getenv("API_KEY_BASKETBALL", "KEY_NOT_FOUND")

if "data_agent" not in st.session_state:
    st.session_state.data_agent = None
if "sport_type" not in st.session_state:
    st.session_state.sport_type = "football"
if "db_initialized" not in st.session_state:
    st.session_state.db_initialized = False


def init_data_agent(sport_type: str = "football"):
    """Initialize the data agent with API key."""
    try:
        st.session_state.data_agent = DataAgent(
            sport_type=sport_type,
            db_path="betting_edge.db"
        )
        st.session_state.sport_type = sport_type
        st.session_state.db_initialized = True
        return True
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        return False


def get_db_connection():
    """Get database connection."""
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
        return ["All Leagues"] + df["league_name"].tolist()
    except Exception as e:
        print(f"Error getting unique leagues: {e}")
        conn.close()
        return ["All Leagues"]


def fetch_matches_from_db(
    sport_type: str,
    league_name: Optional[str] = None,
    include_past: bool = True,
    include_future: bool = True,
    limit: int = 100,
):
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

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    sport_type = st.radio(
        "Select Sport",
        options=["football", "college_football", "basketball"],
        format_func=lambda x: {
            "football": "⚽ Soccer (Football-Data.org)",
            "college_football": "🏈 College Football",
            "basketball": "🏀 College Basketball",
        }.get(x),
        index=["football", "college_football", "basketball"].index(
            st.session_state.sport_type
        ),
    )

    # API Key Display
    if sport_type == "football":
        current_key = st.session_state.api_key_football
        st.text_input(
            "API Key",
            value="****" + current_key[-8:]
            if current_key != "KEY_NOT_FOUND"
            else "Not Set",
            disabled=True,
        )
    elif sport_type == "college_football":
        current_key = st.session_state.api_key_cfb
        st.text_input(
            "API Key",
            value="****" + current_key[-8:]
            if current_key != "KEY_NOT_FOUND"
            else "Not Set",
            disabled=True,
        )
    elif sport_type == "basketball":
        current_key = st.session_state.api_key_basketball
        st.text_input(
            "API Key",
            value="****" + current_key[-8:]
            if current_key != "KEY_NOT_FOUND"
            else "Not Set",
            disabled=True,
        )

    if st.button("🔌 Initialize Agent"):
        with st.spinner("Initializing..."):
            if init_data_agent(sport_type):
                st.success(f"✅ {sport_type.replace('_', ' ').title()} Agent Connected!")
                st.rerun()
            else:
                st.error("Failed to initialize agent")

    st.divider()

    # Database status
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

    # Manual data fetching
    if st.session_state.data_agent:
        with st.expander("🛠️ Manual Data Tools"):
            st.subheader("Fetch Data Manually")

            if st.session_state.sport_type == "football":
                league_options = {
                    "Premier League": 39,
                    "La Liga": 140,
                    "Serie A": 135,
                    "Bundesliga": 78,
                    "Ligue 1": 61,
                }
                selected_league = st.selectbox(
                    "Select League", options=list(league_options.keys())
                )
                season = st.number_input(
                    "Season", min_value=2020, max_value=2025, value=2023
                )

                if st.button("📥 Fetch Matches"):
                    with st.spinner("Fetching..."):
                        try:
                            league_id = league_options[selected_league]
                            matches = st.session_state.data_agent.fetch_matches(
                                league_id=league_id, season=season
                            )
                            if matches:
                                count = 0
                                for m in matches:
                                    st.session_state.data_agent.store_match(m)
                                    count += 1
                                st.success(f"Stored {count} matches!")
                            else:
                                st.warning("No matches found.")
                        except Exception as e:
                            st.error(f"Error: {e}")

            else:
                year = st.number_input(
                    "Year", min_value=2020, max_value=2025, value=2024
                )
                if st.button("📥 Fetch Games"):
                    with st.spinner("Fetching..."):
                        try:
                            matches = st.session_state.data_agent.fetch_matches(
                                year=year
                            )
                            if matches:
                                count = 0
                                for m in matches:
                                    st.session_state.data_agent.store_match(m)
                                    count += 1
                                st.success(f"Stored {count} games!")
                            else:
                                st.warning("No games found.")
                        except Exception as e:
                            st.error(f"Error: {e}")


# Main content
if not st.session_state.data_agent:
    st.info("👋 Welcome! Please select a sport and click 'Initialize Agent' in the sidebar to begin.")
else:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🤖 AI Assistant", "🏠 Dashboard", "⚽ Matches", "📊 Statistics", "💰 Odds"]
    )

    # AI Assistant tab using unified pipeline
    with tab1:
        st.header("🤖 AI Sports Assistant")
        st.markdown(
            "Use natural language to query the multi agent flow. "
            "The system will parse your request, fetch data, run prediction, verification, behavior selection, recommendation, and ethics checks."
        )

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.info("Try: 'Fetch Premier League matches for Liverpool this season'")
        with col_ex2:
            st.info("Try: 'Get 2024 college basketball games for Duke'")

        user_query = st.text_input(
            "Ask the Assistant:", placeholder="Type your request here..."
        )
        
        # Initialize session state for pipeline results if not present
        if "pipeline_results" not in st.session_state:
            st.session_state.pipeline_results = None

        if st.button("🚀 Run Flow") and user_query:
            pipeline = BettingEdgePipeline()

            with st.spinner("Running initial query and data fetching..."):
                # Run the first part of the pipeline (Query -> Data Fetch -> Filter)
                result = pipeline.run(user_query)
                st.session_state.pipeline_results = result

        # Display results if they exist in session state
        if st.session_state.pipeline_results:
            result = st.session_state.pipeline_results

            if result.get("status") == "query_error" or result.get("status") == "no_matches":
                st.error(result.get("message", "Flow failed"))
            else:
                # 1. Show what the agent understood
                with st.expander("Structured Query Analysis"):
                    st.json(result["structured_query"])

                # 2. Get the filtered matches list
                all_filtered_matches = result.get("filtered_matches", [])

                if all_filtered_matches:
                    st.subheader(f"Found {len(all_filtered_matches)} Matching Games:")
                    
                    # Create a nice DataFrame for display
                    matches_display_df = pd.DataFrame([
                        {
                            "Date": m['fixture']['date'][:10], # Simple string slice for date
                            "League": m['league']['name'],
                            "Home Team": m['teams']['home']['name'],
                            "Away Team": m['teams']['away']['name'],
                            "Score": f"{m['goals']['home']}-{m['goals']['away']}" if m['fixture']['status']['long'] in ['FINISHED', 'Match Finished'] else "N/A"
                        } for m in all_filtered_matches
                    ])
                    
                    st.dataframe(matches_display_df, use_container_width=True, hide_index=True)

                    # 3. Let user SELECT one match for deep analysis
                    match_options = matches_display_df.apply(
                        lambda x: f"{x['Home Team']} vs {x['Away Team']} ({x['Date']})",
                        axis=1
                    ).tolist()
                    
                    selected_match_idx = st.selectbox(
                        "Select a match for detailed prediction and recommendation:",
                        range(len(match_options)),
                        format_func=lambda x: match_options[x],
                        key="selected_pipeline_match"
                    )

                    # 4. Run Deep Analysis on the SELECTED match
                    if st.button("🔮 Analyze Selected Match"):
                        selected_match_data = all_filtered_matches[selected_match_idx]
                        
                        # Re-initialize pipeline to run the downstream agents
                        pipeline = BettingEdgePipeline() 
                        
                        with st.spinner(f"Running deep analysis for {selected_match_data['teams']['home']['name']} vs {selected_match_data['teams']['away']['name']}..."):
                            deep_analysis_result = pipeline.run_deep_analysis(selected_match_data)
                        
                        if deep_analysis_result.get("status") == "ok":
                            # Store match in DB for persistence
                            if st.session_state.data_agent:
                                try:
                                    st.session_state.data_agent.store_match(deep_analysis_result["match"])
                                except Exception as e:
                                    print(f"DB Store error: {e}")

                            st.success("Analysis Complete!")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("Prediction Model")
                                st.json(deep_analysis_result["prediction"])
                                
                                st.subheader("Verification Agent")
                                st.json(deep_analysis_result["verification"])

                            with col2:
                                st.subheader("Behavior Action")
                                st.write(deep_analysis_result["action"])
                                
                                st.subheader("Ethics Check")
                                st.json(deep_analysis_result["ethics"])

                            st.divider()
                            st.subheader("📝 Final Recommendation")
                            st.info(deep_analysis_result["recommendation"])

                        else:
                            st.error(deep_analysis_result.get("message", "Deep analysis failed."))
                else:
                    st.warning(f"Agent understood the query, but found no matches involving '{result['structured_query'].get('team_name')}'.")


    # Dashboard tab
    with tab2:
        st.header(
            f"Dashboard Overview ({st.session_state.sport_type.replace('_', ' ').title()})"
        )

        if os.path.exists("betting_edge.db"):
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM matches WHERE match_date >= datetime('now', '-7 days') AND sport_type = ?",
                (st.session_state.sport_type,),
            )
            recent_matches = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM matches WHERE match_date >= datetime('now') "
                "AND status NOT IN ('Match Finished', 'Match Cancelled', 'completed') "
                "AND sport_type = ?",
                (st.session_state.sport_type,),
            )
            upcoming_matches = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT m.match_id) "
                "FROM odds o JOIN matches m ON o.match_id = m.match_id "
                "WHERE m.sport_type = ?",
                (st.session_state.sport_type,),
            )
            matches_with_odds = cursor.fetchone()[0]
            conn.close()

            col1, col2, col3 = st.columns(3)
            col1.metric("Recent Matches", recent_matches)
            col2.metric("Upcoming Matches", upcoming_matches)
            col3.metric("Matches with Odds", matches_with_odds)

            st.divider()
            st.subheader("📅 Latest Matches")

            leagues = get_unique_leagues(st.session_state.sport_type)
            col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1, 1, 2])

            with col_f1:
                selected_league_filter = st.selectbox(
                    "Filter by League",
                    options=leagues,
                    key="dash_league_filter",
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
                include_past=filter_past,
                include_future=filter_future,
                limit=show_count,
            )

            if not matches_df.empty:
                matches_df["match_date"] = pd.to_datetime(
                    matches_df["match_date"]
                ).dt.strftime("%Y-%m-%d %H:%M")
                matches_df["Score"] = matches_df.apply(
                    lambda x: f"{int(x['home_score']) if pd.notna(x['home_score']) else 0} - "
                    f"{int(x['away_score']) if pd.notna(x['away_score']) else 0}",
                    axis=1,
                )
                st.dataframe(
                    matches_df[
                        [
                            "league_name",
                            "match_date",
                            "home_team_name",
                            "Score",
                            "away_team_name",
                            "status",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No matches in database. Use the AI Assistant or sidebar tools.")
        else:
            st.info("🔧 Database not found.")

    # Match details tab
    with tab3:
        st.header("Match Details")
        col1, col2 = st.columns(2)
        with col1:
            show_past = st.checkbox("Show Past Matches", value=True, key="tab3_past")
        with col2:
            show_future = st.checkbox(
                "Show Future Matches", value=True, key="tab3_future"
            )

        if os.path.exists("betting_edge.db"):
            matches_df = fetch_matches_from_db(
                sport_type=st.session_state.sport_type,
                league_name="All Leagues",
                include_past=show_past,
                include_future=show_future,
                limit=500,
            )

            if not matches_df.empty:
                match_options = matches_df.apply(
                    lambda x: f"{x['home_team_name']} vs {x['away_team_name']} ({x['match_date'][:10]})",
                    axis=1,
                ).tolist()

                selected_match_idx = st.selectbox(
                    "Select a match",
                    range(len(match_options)),
                    format_func=lambda x: match_options[x],
                )

                if selected_match_idx is not None:
                    selected_match = matches_df.iloc[selected_match_idx]
                    match_id = int(selected_match["match_id"])

                    c1, c2, c3 = st.columns([2, 1, 2])
                    c1.subheader(selected_match["home_team_name"])
                    c1.metric(
                        "Home",
                        int(selected_match["home_score"])
                        if pd.notna(selected_match["home_score"])
                        else "-",
                    )
                    c2.markdown(
                        "<h3 style='text-align: center;'>VS</h3>",
                        unsafe_allow_html=True,
                    )
                    c2.markdown(
                        f"<p style='text-align: center;'>{selected_match['status']}</p>",
                        unsafe_allow_html=True,
                    )
                    c3.subheader(selected_match["away_team_name"])
                    c3.metric(
                        "Away",
                        int(selected_match["away_score"])
                        if pd.notna(selected_match["away_score"])
                        else "-",
                    )

                    if st.session_state.sport_type == "football":
                        stats_df = fetch_match_stats(match_id)
                        if not stats_df.empty:
                            st.divider()
                            st.subheader("Statistics")
                            st.dataframe(stats_df, use_container_width=True)
            else:
                st.info("No matches available.")
        else:
            st.info("Database not found.")

    # Statistics tab
    with tab4:
        st.header("Team Statistics")
        if os.path.exists("betting_edge.db"):
            conn = get_db_connection()
            query = (
                "SELECT DISTINCT home_team_name as team_name, home_team_id as team_id "
                "FROM matches WHERE sport_type = ? "
                "UNION "
                "SELECT DISTINCT away_team_name, away_team_id FROM matches WHERE sport_type = ? "
                "ORDER BY team_name"
            )
            teams_df = pd.read_sql_query(
                query,
                conn,
                params=(st.session_state.sport_type, st.session_state.sport_type),
            )
            conn.close()

            if not teams_df.empty:
                selected_team = st.selectbox(
                    "Select Team", teams_df["team_name"].tolist(), key="stats_team_select"
                )
                if selected_team:
                    team_id = int(
                        teams_df[teams_df["team_name"] == selected_team]["team_id"].iloc[
                            0
                        ]
                    )
                    if st.session_state.data_agent:
                        recent = st.session_state.data_agent.get_recent_matches(team_id)
                        if recent:
                            st.subheader(f"Recent Form - {selected_team}")
                            wins = sum(
                                1
                                for m in recent
                                if (
                                    m["home_team_id"] == team_id
                                    and m["home_score"] > m["away_score"]
                                )
                                or (
                                    m["away_team_id"] == team_id
                                    and m["away_score"] > m["home_score"]
                                )
                            )
                            losses = len(recent) - wins
                            st.metric(
                                "Win Rate (Last 5)",
                                f"{(wins / len(recent) * 100):.0f}%",
                            )
                            st.dataframe(
                                pd.DataFrame(recent)[
                                    [
                                        "match_date",
                                        "home_team_name",
                                        "home_score",
                                        "away_score",
                                        "away_team_name",
                                    ]
                                ],
                                use_container_width=True,
                            )

    # Odds tab
    with tab5:
        st.header("Betting Odds")
        if st.session_state.sport_type != "football":
            st.info(
                "Odds are currently only available for Soccer via API-Football (not supported on Football-Data.org free tier)."
            )
        else:
            st.info("Odds data integration for Football-Data.org is coming soon.")