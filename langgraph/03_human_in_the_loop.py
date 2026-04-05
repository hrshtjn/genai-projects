import sys
import uuid
from typing import Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END, MessagesState
from IPython.display import Image, display

import init_creds as creds
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

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

# Note: 'llm' should be initialized here (e.g., from langchain_openai import ChatOpenAI)
# llm = ChatOpenAI(model="gpt-4o")

# --- 1. State Definition ---
class State(TypedDict):
    linkedin_topic: str
    # add_messages allows the lists to be appended rather than overwritten
    generated_post: Annotated[List[str], add_messages]
    human_feedback: Annotated[List[str], add_messages]

# --- 2. Node Functions ---

def model(state: State):
    """Uses the LLM to generate a LinkedIn post with human feedback incorporated."""
    print("[model] Generating content")
    linkedin_topic = state["linkedin_topic"]
    # Check for existing feedback; use a default if none exists
    feedback = state.get("human_feedback", [])
    current_feedback = feedback[-1] if feedback else "No feedback yet"
    
    # Define the prompt
    prompt = f"""
    LinkedIn Topic: {linkedin_topic}
    Human Feedback: {current_feedback}
    
    Generate a structured and well-written LinkedIn post based on the given topic.
    Consider previous human feedback to refine the response.
    """
    
    # Invoke LLM
    response = llm.invoke([
        SystemMessage(content="You are an expert LinkedIn content writer"),
        HumanMessage(content=prompt)
    ])
    
    generated_linkedin_post = response.content
    print(f"[model_node] Generated post:\n{generated_linkedin_post}\n")
    
    return {
        "generated_post": [AIMessage(content=generated_linkedin_post)],
        "human_feedback": feedback
    }

def human_node(state: State):
    """Human Intervention node - pauses execution until input is provided."""
    print("\n[human_node] awaiting human feedback...")
    generated_post = state["generated_post"]
    
    # Interrupt execution to get user feedback
    user_feedback = interrupt(
        {
            "generated_post": generated_post,
            "message": "Provide feedback or type 'done' to finish"
        }
    )
    print(f"[human_node] Received human feedback: {user_feedback}")

    # If user types "done", transition to the end node
    if user_feedback.lower() == "done":
        return Command(
            update={"human_feedback": ["Finalised"]}, 
            goto="end_node"
        )
    
    # Otherwise, update feedback and loop back to 'model' for re-generation
    return Command(
        update={"human_feedback": [user_feedback]}, 
        goto="model"
    )

def end_node(state: State):
    """Final node to display the finished product."""
    print("\n[end_node] Process finished")
    print("Final Generated Post:", state["generated_post"][-1])
    print("Final Human Feedback:", state["human_feedback"])
    return {
        "generated_post": state["generated_post"], 
        "human_feedback": state["human_feedback"]
    }

# --- 3. Conditional Logic ---

def should_continue(state: State):
    """Determines the next node based on human feedback state."""
    last_feedback = state["human_feedback"][-1]
    if last_feedback == "Finalised":
        return "end_node"
    return "model"

# --- 4. Building the Graph ---

graph = StateGraph(State)

# Add nodes
graph.add_node("model", model)
graph.add_node("human_node", human_node)
graph.add_node("end_node", end_node)

# Define the flow
graph.add_edge(START, "model")
graph.add_edge("model", "human_node")

# Conditional routing logic
graph.add_conditional_edges(
    "human_node",
    should_continue
)

graph.add_edge("end_node", END)

# Enable Interrupt/Persistence mechanism
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# --- 5. Execution Loop ---

# Configuration for checkpointing (pause and resume)
thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

linkedin_topic = input("Enter your LinkedIn topic: ")
initial_state = {
    "linkedin_topic": linkedin_topic,
    "generated_post": [],
    "human_feedback": []
}

# Run the graph using stream to handle interrupts
for chunk in app.stream(initial_state, config=thread_config):
    for node_id, value in chunk.items():
        # Check if the graph has paused at an interrupt
        if node_id == "__interrupt__":
            while True:
                user_feedback = input("Provide feedback (or type 'done' when finished): ")
                
                # Resume execution by passing the user feedback back to the Command
                app.invoke(Command(resume=user_feedback), config=thread_config)
                
                # Exit the local input loop if the user is finished
                if user_feedback.lower() == "done":
                    break