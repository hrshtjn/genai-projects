from google.adk.agents import Agent

root_agent = Agent(
    model="gemini-2.5-flash",
    name="chat_agent",
    description="A helpful, friendly AI assistant.",
    instruction="""You are a helpful, friendly AI assistant.
Answer questions clearly and concisely.
If you are unsure about something, say so honestly.
Be conversational and engaging.""",
)
