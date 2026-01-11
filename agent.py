"""
Legacy Agent Entry Point

This file is maintained for backward compatibility.
It imports and runs the new enterprise-structured agent entrypoint.
"""

# CRITICAL: Set Google API key BEFORE any other imports
# This must happen before Google GenAI SDK initialization
# The Google GenAI SDK reads GOOGLE_API_KEY when modules are imported
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env.local from project root (parent directory)
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(env_path, override=True)
    # Immediately set Google API key in environment
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        google_api_key = google_api_key.strip()
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
        else:
            raise RuntimeError("GOOGLE_API_KEY is empty in .env.local")
    else:
        raise RuntimeError("GOOGLE_API_KEY not found in .env.local - required at startup")

# NOW import other modules (after environment is set)
from app.agents.entrypoint import entrypoint
from livekit import agents
from app.config import get_config
from app.utils.logger import get_logger
import sys

logger = get_logger(__name__)

if __name__ == "__main__":
    config = get_config()
    
    logger.info("=" * 60)
    logger.info("🔧 AGENT WORKER STARTING (Legacy Entry Point)")
    logger.info("=" * 60)
    logger.info(f"   Agent Name: '{config.livekit.agent_name}'")
    logger.info(f"   Status: Registering with LiveKit Cloud...")
    logger.info(f"   Waiting for job dispatch...")
    logger.info("=" * 60)
    
    # If no command is provided, default to 'dev' to start the worker
    if len(sys.argv) == 1:
        sys.argv.append('dev')
    
    # NOTE: If you see a warning/error about "model_q8.onnx" not found during startup, this is EXPECTED and HARMLESS.
    # 
    # What's happening:
    # - The LiveKit agents framework automatically tries to initialize the turn detector inference runner
    # - We use VAD-based turn detection (which doesn't require the ML model)
    # - The framework logs an error but continues successfully (agent still works)
    #
    # This is expected behavior when using VAD-based turn detection (recommended for production).
    # The agent will work correctly without the ML turn detector model.
    #
    # To suppress the warning (optional, not required):
    #   python agent.py download-files  # Downloads the model (not needed if using VAD)
    #
    # Or simply ignore the warning - VAD-based turn detection works perfectly without it.
    
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name=config.livekit.agent_name,
    ))
