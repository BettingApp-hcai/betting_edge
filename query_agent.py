# /agent_modules/query_agent.py
import datetime
from typing import Optional, Literal
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

# 1. Schema definition
class SportsDataQuery(BaseModel):
    sport_type: Literal["football", "college_football", "basketball"] = Field(
        ..., description="The sport to fetch. 'football' means Soccer."
    )
    team_name: Optional[str] = Field(
        None, description="Team to filter (e.g. 'Liverpool')"
    )
    competition_code: Optional[str] = Field(
        None, description="For Soccer only: PL, PD, SA, BL1, FL1, CL"
    )
    season: int = Field(..., description="YYYY season start")

# 2. LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 3. Parser
parser = PydanticOutputParser(pydantic_object=SportsDataQuery)

# 4. Prompt
current_year = datetime.datetime.now().year

system_template = """
You are an expert sports data query translator.
Your job is to convert natural language questions into structured JSON parameters.

Current Year: {current_year}

RULES:
1. Soccer leagues -> codes: PL, PD, SA, BL1, FL1.
2. "College", "NCAA" -> college_football or basketball.
3. "this season" -> {current_year}. "last season" -> {current_year_minus_1}.
4. Extract clean team names.

{format_instructions}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_template),
    ("user", "{query}")
])

safe_prompt = prompt.partial(
    current_year=str(current_year),
    current_year_minus_1=str(current_year - 1),
    format_instructions=parser.get_format_instructions()
)

# 5. Query parser
def parse_user_query(user_query: str) -> SportsDataQuery:
    print(f"🤖 Query Agent: Analyzing '{user_query}'...")

    # old-LangChain compatible chain
    chain = safe_prompt | llm

    # run LLM
    response = chain.invoke({"query": user_query})

    # parse structured output
    structured = parser.parse(response.content)

    print(f"✅ Query Agent: Parsed to {structured}")
    return structured
