import sys
from typing import Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END, MessagesState
from IPython.display import Image, display

import init_creds as creds
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from langchain.tools import tool

# Set up system path for local modules
sys.path.insert(1, '../../')

## Configure Azure OpenAI
AZURE_OPENAI_KEY = creds.get_api_key()
AZURE_OPENAI_ENDPOINT = creds.get_endpoint()
AZURE_OPENAI_API_VERSION = "2025-04-01-preview"

if not AZURE_OPENAI_KEY:
    raise ValueError("No AZURE_OPENAI_KEY set for Azure OpenAI API")
if not AZURE_OPENAI_ENDPOINT:
    raise ValueError("No AZURE_OPENAI_ENDPOINT set for Azure OpenAI API")

# Initialize LLM
llm = AzureChatOpenAI(
    model="gpt-4o-mini",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)

# Note: Ensure your 'llm' instance is initialized before running the sections below.
# Example: 
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4o")

# ==========================================
# 1. Schema for Structured Output
# ==========================================

class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query that is optimized web search.")
    justification: str = Field(
        None, description="Why this query is relevant to the user's request."
    )

# Augment the LLM with schema for structured output
structured_llm = llm.with_structured_output(SearchQuery)

# Invoke the augmented LLM
output = structured_llm.invoke("How does Calcium CT score relate to high cholesterol?")
print(output.search_query)
print(output.justification)
print(output)


# ==========================================
# 2. Tool Calling
# ==========================================

# Define a tool
def multiply(a: int, b: int) -> int:
    return a * b

# Augment the LLM with tools
llm_with_tools = llm.bind_tools([multiply])

# Invoke the LLM with input that triggers the tool call
msg = llm_with_tools.invoke("What is 2 times 4?")

# Get the tool call
print(msg)

# Print msg content
print(msg.content)

# Process the tool call
tool_call = msg.tool_calls[0]
result = multiply(**tool_call['args'])
print(result)

# ==========================================
# 3. Pass result back to LLM for final answer
# ==========================================

# We need to pass the conversation history: 
# [UserMessage, AIMessage (with tool call), ToolMessage (with result)]
messages = [
    HumanMessage(content="What is 2 times 4?"),
    msg,
    ToolMessage(tool_call_id=tool_call['id'], content=str(result))
]

final_response = llm_with_tools.invoke(messages)
print(final_response.content)