# GenAI Projects: LangGraph Agents

This project contains practical examples and demonstrations of building AI agents using LangGraph and Azure OpenAI. It includes a utility script to securely fetch API credentials using Doppler and a set of lessons/scripts to explore different LangGraph capabilities.

## Project Structure

- `import_creds.py`: A Python script that uses the Doppler SDK to fetch your Azure OpenAI API key and endpoint, and exports them to your `~/.bashrc` file.
- `langgraph/`: A directory containing sequential examples of using LangGraph:
  - `01_simple_agent.py`: Demonstrates the basics of creating a simple agent.
  - `02_memory.py`: Shows how to add memory/state to your agent across interactions.
  - `03_human_in_the_loop.py`: Illustrates how to implement human-in-the-loop (approval or interruption) in your agent workflow.

## Prerequisites

- Python 3.x
- [Doppler](https://www.doppler.com/) account and a Doppler Service Token (`DOPPLER_AIGUILD_TOKEN`).
- Appropriate Python packages (e.g., `dopplersdk`, `langgraph`, `langchain`, `langchain-openai`).

## Setup Instructions

1. **Install Dependencies:**
   Ensure you have the required Python packages installed. You can install the Doppler SDK using pip:
   ```bash
   pip install dopplersdk
   ```
   *(Note: You will also likely need LangGraph, LangChain, and their dependencies depending on what is used in the `langgraph/` scripts).*

2. **Configure Credentials:**
   The project uses Doppler to manage secrets (`AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_API_BASE`).

   First, export your Doppler token in your terminal:
   ```bash
   export DOPPLER_AIGUILD_TOKEN="your_doppler_token_here"
   ```

   Then, run the credential import script:
   ```bash
   python import_creds.py
   ```
   This script will fetch the necessary Azure OpenAI credentials from the Doppler project (`dep-training`, config `prod_ai_guild_genai_practicum`) and append them to your `~/.bashrc` file.

3. **Apply Environment Variables:**
   After running the script, reload your `.bashrc` so the variables take effect in your current terminal session:
   ```bash
   source ~/.bashrc
   ```

## Running the Examples

Once your credentials are set up in your environment, you can run the LangGraph examples sequentially:

```bash
python langgraph/01_simple_agent.py
python langgraph/02_memory.py
python langgraph/03_human_in_the_loop.py
```
