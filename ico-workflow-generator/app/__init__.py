"""Flask application factory."""

from flask import Flask
import os


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Default configuration
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
        SCHEMAS_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas"),
        CONTEXT_STORE_PATH=os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "context_artifacts.json",
        ),
        LLM_SETTINGS_PATH=os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "llm_settings.json",
        ),
        CONTEXT_MAX_UPLOAD_FILES=10,
        CONTEXT_MAX_UPLOAD_BYTES=2 * 1024 * 1024,
        DEBUG_MODE_ENABLED=os.environ.get("DEBUG_MODE_ENABLED", "false").lower() == "true",
        DEBUG_MODE_MAX_PAYLOAD_CHARS=int(os.environ.get("DEBUG_MODE_MAX_PAYLOAD_CHARS", "16000")),
    )
    
    if config:
        app.config.update(config)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app
