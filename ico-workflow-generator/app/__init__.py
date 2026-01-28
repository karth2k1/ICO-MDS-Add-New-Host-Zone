"""Flask application factory."""

from flask import Flask
import os


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Default configuration
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
        TEMPLATES_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)), "workflow_templates"),
        RULES_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules"),
        SCHEMAS_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas"),
    )
    
    if config:
        app.config.update(config)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app
