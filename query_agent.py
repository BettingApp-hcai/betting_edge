# /agent_modules/query_agent.py
import datetime
from typing import Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser # <-- Standard Parser

# 1. Define the Output Schema
class SportsDataQuery(BaseModel):
    """Structured parameters for querying the sports data API."""
    
    sport_type: Literal["football", "college_football", "basketball"] = Field(
        ..., 
        description="The sport to fetch. 'football' means Soccer."
    )
    
    team_name: Optional[str] = Field(
        None, 
        description="The name of the specific team to filter for (e.g., 'Liverpool', 'Syracuse')."
    )
    
    competition_code: Optional[str] = Field(
        None, 
        description="For Soccer ONLY: The competition code. Map to: 'PL', 'PD', 'SA', 'BL1', 'FL1', 'CL'."
    )
    
    season: int = Field(
        ..., 
        description="The 4-digit year of the season start."
    )

# 2. Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 3. Set up the Parser (The Fix)
parser = PydanticOutputParser(pydantic_object=SportsDataQuery)

# 4. Define the Prompt
current_year = datetime.datetime.now().year

system_prompt = f"""
You are an expert sports data query translator. 
Your job is to convert natural language user questions into structured API parameters.

Current Year: {current_year}

RULES:
1. **Soccer/Football**: Map league names to these EXACT codes: Premier League -> 'PL', La Liga -> 'PD', Serie A -> 'SA', Bundesliga -> 'BL1', Ligue 1 -> 'FL1'.
2. **College Sports**: If the user mentions 'NCAA', 'College', 'Cuse', 'Bama', map to 'college_football' or 'basketball'.
3. **Season**: If the user says "this season" or "current", assume {current_year}. For "last season", subtract 1.
4. **Team Names**: Extract the core team name (e.g., "Liverpool FC" -> "Liverpool").

{parser.get_format_instructions()}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{query}"),
])

# 5. The Agent Function
def parse_user_query(user_query: str) -> SportsDataQuery:
    """
    Analyzes the user's natural language query and returns structured API params.
    """
    print(f"🤖 Query Agent: Analyzing '{user_query}'...")
    
    # Create the chain with the parser
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"query": user_query})
        print(f"✅ Query Agent: Mapped to {result}")
        return result
    except Exception as e:
        print(f"❌ Query Agent Error: {e}")
        return None