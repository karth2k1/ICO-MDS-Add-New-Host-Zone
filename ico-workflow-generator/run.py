#!/usr/bin/env python3
"""
ICO Workflow Generator - Flask Application Entry Point

Run this script to start the web application:
    python run.py

Then open http://localhost:5080 in your browser.

For LLM-based generation, set environment variables:
    export CISCO_CLIENT_ID=your_client_id
    export CISCO_CLIENT_SECRET=your_client_secret
    export CISCO_APPKEY=your_appkey

Or create a .env file (copy from .env.example).
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}")
except ImportError:
    pass  # python-dotenv not installed, use system env vars

from flask import Flask
from app.llm_settings import LLM_MODEL_DISPLAY_NAME, LLMSettingsStore, is_effectively_configured, resolve_effective_settings


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="app/templates",
        static_folder="app/static"
    )
    
    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.config["CONTEXT_STORE_PATH"] = os.path.join(
        os.path.dirname(__file__),
        "data",
        "context_artifacts.json",
    )
    app.config["LLM_SETTINGS_PATH"] = os.path.join(
        os.path.dirname(__file__),
        "data",
        "llm_settings.json",
    )
    app.config["CONTEXT_MAX_UPLOAD_FILES"] = 10
    app.config["CONTEXT_MAX_UPLOAD_BYTES"] = 2 * 1024 * 1024
    app.config["DEBUG_MODE_ENABLED"] = os.environ.get("DEBUG_MODE_ENABLED", "false").lower() == "true"
    app.config["DEBUG_MODE_MAX_PAYLOAD_CHARS"] = int(os.environ.get("DEBUG_MODE_MAX_PAYLOAD_CHARS", "16000"))
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app


def main():
    """Run the Flask development server."""
    app = create_app()
    
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 5080))
    host = os.environ.get("HOST", "127.0.0.1")
    
    # Check LLM configuration
    llm_configured = is_effectively_configured(
        resolve_effective_settings(LLMSettingsStore(app.config["LLM_SETTINGS_PATH"]))
    )
    
    print("=" * 60)
    print("ICO Workflow Generator")
    print("=" * 60)
    print(f"\nStarting server at http://{host}:{port}")
    
    print("\n--- LLM Status ---")
    if llm_configured:
        print(f"  LLM ({LLM_MODEL_DISPLAY_NAME}): CONFIGURED")
    else:
        print(f"  LLM ({LLM_MODEL_DISPLAY_NAME}): NOT CONFIGURED")
        print("  Configure values from /llm-setup (or via environment variables)")
    
    print("\n--- Endpoints ---")
    print(f"  Home:              http://{host}:{port}/")
    print(f"  LLM Setup:         http://{host}:{port}/llm-setup")
    print(f"  Context Sources:   http://{host}:{port}/context-manager")
    print(f"  Status:            http://{host}:{port}/status")
    print("\n  LLM-based generation (requires credentials):")
    print(f"    POST /generate/llm    - Generate using GPT-4.1")
    print("\n  OpenAPI generation:")
    print(f"    POST /generate/openapi - Generate from uploaded OpenAPI spec")
    print(f"    POST /analyze         - Analyze JIRA text only")
    print(f"    POST /generate/custom - Custom workflow generation")
    print("\n--- Debug Mode ---")
    print(f"  Capability enabled: {'YES' if app.config['DEBUG_MODE_ENABLED'] else 'NO'}")
    print("  Activation: set debug=true in request or X-Debug-Mode: true")
    
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60 + "\n")
    
    app.run(host=host, port=port, debug=app.config["DEBUG"])


if __name__ == "__main__":
    main()
