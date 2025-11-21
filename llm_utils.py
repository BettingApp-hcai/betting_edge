# /llm_utils.py
"""
Holds utility functions that use LLMs to assist other agents.
"""
from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Initialize the LLM (this will be used by multiple agents)
# It's fast, smart, and cheap.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def analyze_api_error(failed_url: str, status_code: int, raw_text: str) -> str:
    """
    Uses an LLM to analyze a failed API response and return a
    human-readable cause.
    """
    print("LLM Error Analyzer: Analyzing failed API call...")
    
    # We only need the first 1000 chars of HTML, not the whole page
    snippet = raw_text[:1000]

    system_prompt = """
    You are a data pipeline debugging assistant. An API call has failed. 
    Based on the URL, status code, and raw response snippet, determine the *probable cause* and state it in one simple sentence.
    
    Common causes:
    - Invalid API Key: (Look for 'unauthorized', '401', 'forbidden', 'invalid key')
    - Bad Endpoint/URL: (Look for 'Not Found', '404', 'Swagger UI', 'HTML <title>')
    - Rate Limit Exceeded: (Look for 'too many requests', '429', 'rate limit')
    - Server Error: (Look for '500', 'internal server error')
    - Bad Request: (Look for '400', 'missing parameter')

    Respond with *only* the single-sentence explanation.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", 
         f"URL: {failed_url}\n"
         f"Status Code: {status_code}\n"
         f"Raw Response Snippet:\n{snippet}")
    ])
    
    parser = StrOutputParser()
    chain = prompt | llm | parser
    
    try:
        explanation = chain.invoke({})
        return explanation
    except Exception as e:
        print(f"LLM Error Analyzer failed: {e}")
        return "An unknown analysis error occurred."