"""Main CLI entrypoint for the LangGraph template."""
import asyncio
import os
from pathlib import Path
import argparse

from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing modules that depend on them
load_dotenv()

from shared.config import Configuration
from agents import MainAgent
from agents.chat_agent.agent import enable_chat_logging


async def main(enable_logging: bool = False, log_level: str = "info"):
    """Run the interactive chat loop."""
    print("=" * 60)
    print("LangGraph Multi-Agent Template")
    print("=" * 60)
    print()
    if enable_logging:
        level = {"debug": 10, "info": 20, "warning": 30, "error": 40}.get(log_level.lower(), 20)
        enable_chat_logging(level=level)
        print(f"Logging enabled at level: {log_level.upper()}")

    # Initialize configuration
    try:
        config = Configuration()
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease ensure:")
        print("1. You have a .env file with OPENAI_API_KEY")
        print("2. You have a model_config.json file (or use defaults)")
        return

    print(f"Using models:")
    print(f"  - Orchestrator: {config.orchestrator_model}")
    print(f"  - Text: {config.text_model}")
    if getattr(config, "openai_base_url", None):
        print(f"Base URL: {config.openai_base_url}")
    print()

    # Create the main agent
    agent = MainAgent(config)

    print("Chat with the AI assistant. Type 'quit', 'exit', or 'q' to end.")
    print("Type 'reset' to clear conversation history.")
    print("Type 'help' for usage tips.")
    print("-" * 60)
    print()

    # Chat loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            if user_input.lower() == 'reset':
                agent.reset_history()
                print("Chat history cleared.\n")
                continue

            if user_input.lower() == 'help':
                print("\nAvailable commands:")
                print("  - quit/exit/q: Exit the chat")
                print("  - reset: Clear conversation history")
                print("  - help: Show this help message")
                print("\nThe assistant can:")
                print("  - Answer questions and have conversations")
                print("  - Create structured plans (try: 'Help me plan a project')")
                print("  - Process and analyze data (try: 'Analyze this data: ...')")
                print()
                continue

            # Get agent response
            print("\nAssistant: ", end="", flush=True)
            # Chat timeout is configurable via CHAT_TIMEOUT (sec); default relates to LLM timeout
            chat_timeout_env = os.getenv("CHAT_TIMEOUT")
            if chat_timeout_env and chat_timeout_env.isdigit():
                chat_timeout = int(chat_timeout_env)
            else:
                # Allow more time than a single LLM call since tools may do multiple calls
                base = getattr(config, "openai_timeout", 60)
                chat_timeout = max(base * 2, 60)

            try:
                response = await asyncio.wait_for(agent.chat(user_input), timeout=chat_timeout)
            except asyncio.TimeoutError:
                response = (
                    f"Request timed out after {chat_timeout}s. The endpoint may be slow or unreachable. "
                    "Try again, increase CHAT_TIMEOUT/OPENAI_TIMEOUT, or check your OPENAI_BASE_URL and network."
                )
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Type 'reset' to clear history and try again.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LangGraph Multi-Agent Template")
    parser.add_argument("--log", action="store_true", help="Enable chat logging to console and logs/chat.log")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="Logging level when --log is set")
    args = parser.parse_args()
    asyncio.run(main(enable_logging=args.log, log_level=args.log_level))
