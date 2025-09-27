import asyncio
import os
import json
import argparse
from typing import List, Dict, Any, Optional

from fastmcp import Client
from fastmcp.server import Tool
from openai import AsyncOpenAI, APIError

# --- CONFIGURATION ---
# The high-level goal for the agent to accomplish.
# This goal is designed to require multiple steps.
USER_GOAL = "Drive forward for 2 seconds and then tell me what you see."

# The location of the hardware server.
SERVER_SOURCE = "my_hardware_server.py"

# Default LLM model if not specified via command line.
DEFAULT_LLM_MODEL = "gpt-4-turbo-preview"
# ---------------------


async def get_llm_plan(
    user_goal: str, tools_from_server: List[Tool], model_name: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Asks an LLM to generate a multi-step plan of tool calls to achieve a goal.

    Args:
        user_goal: The natural language command from the user.
        tools_from_server: The list of Tool objects discovered from the server.
        model_name: The specific OpenAI model to use for planning.

    Returns:
        A list of action dictionaries, where each dictionary contains a
        'tool_name' and 'arguments'. Returns None on failure.
    """
    print("\n🤖 BRAIN: Planning sequence of actions...")

    llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    api_tools = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools_from_server
    ]

    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant that controls a physical robot. "
                       "Your task is to translate a user's command into a sequence of "
                       "executable tool calls. If the goal requires multiple actions, "
                       "plan all the necessary steps in the correct order. "
                       "You must only use the provided tools."
        },
        {"role": "user", "content": user_goal},
    ]

    print(f"🤖 BRAIN: Sending goal to '{model_name}' with {len(api_tools)} available tools...")

    try:
        response = await llm_client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=api_tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
    except APIError as e:
        print(f"\n--- ERROR ---")
        print(f"FATAL: An error occurred with the OpenAI API: {e}")
        return None
    except Exception as e:
        print(f"\n--- ERROR ---")
        print(f"FATAL: A network or unexpected error occurred: {e}")
        return None

    if not response_message.tool_calls:
        print("🤖 BRAIN: The LLM decided not to call any tools.")
        if response_message.content:
            print(f"🤖 BRAIN: LLM text response: '{response_message.content}'")
        return None

    # Process all tool calls returned by the LLM into a plan
    plan = []
    for tool_call in response_message.tool_calls:
        tool_name = tool_call.function.name
        try:
            arguments = json.loads(tool_call.function.arguments)
            plan.append({"tool_name": tool_name, "arguments": arguments})
        except json.JSONDecodeError:
            print(f"\n--- ERROR ---")
            print(f"WARNING: LLM returned invalid JSON for arguments: {tool_call.function.arguments}")
            # We choose to skip this invalid step and continue
            continue
    
    print(f"🤖 BRAIN: LLM created a plan with {len(plan)} step(s).")
    return plan


async def main(model_name: str):
    """
    The main execution loop for the agent.
    """
    print("--- Robot Agent Initializing ---")
    print(f"Goal: '{USER_GOAL}'")
    print(f"Using LLM Model: '{model_name}'")
    print(f"Connecting to server: '{SERVER_SOURCE}'")

    # Pre-flight check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n--- FATAL ERROR ---")
        print("The OPENAI_API_KEY environment variable is not set.")
        print("Please set it before running the script.")
        print("---------------------\n")
        return

    client = Client(SERVER_SOURCE)

    try:
        async with client:
            print(f"\n▶️ AGENT: Connected to server. Discovering tools...")
            available_tools = await client.list_tools()
            if not available_tools:
                print("▶️ AGENT: Server has no tools available. Exiting.")
                return

            # Get the multi-step plan from the LLM
            llm_plan = await get_llm_plan(USER_GOAL, available_tools, model_name)

            # Execute the plan if one was generated
            if not llm_plan:
                print("\n▶️ AGENT: No executable plan was generated. Shutting down.")
                return

            print(f"\n▶️ AGENT: Starting execution of {len(llm_plan)}-step plan...")
            for i, action in enumerate(llm_plan, 1):
                tool_name = action["tool_name"]
                arguments = action["arguments"]

                print(f"--- [Step {i}/{len(llm_plan)}] Executing: {tool_name}({arguments}) ---")
                
                try:
                    result = await client.call_tool(tool_name, arguments)
                    print(f"✅ Step {i} complete. Result: '{result}'")
                except Exception as e:
                    print(f"❌ Step {i} failed! Error: {e}")
                    print("▶️ AGENT: Halting plan execution due to error.")
                    break # Stop the plan if one step fails
            
            print("\n▶️ AGENT: Plan execution finished.")

    except Exception as e:
        print(f"\n--- FATAL ERROR ---")
        print(f"An error occurred during client operation: {e}")
        print("Please ensure the server script is running and accessible.")
        print("---------------------\n")

    print("\n--- Robot Agent Shutting Down ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An agent to control a hardware server using an LLM.")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_LLM_MODEL,
        help=f"The OpenAI model to use for planning. Defaults to '{DEFAULT_LLM_MODEL}'. "
             "Example: gpt-3.5-turbo"
    )
    args = parser.parse_args()

    asyncio.run(main(model_name=args.model))