"""Flask routes for the ICO Workflow Generator."""

import os
from flask import Blueprint, Response, current_app, jsonify, render_template, request
import json
from app.debug_utils import debug_requested

main_bp = Blueprint("main", __name__)


def is_llm_configured() -> bool:
    """Check if LLM credentials are configured."""
    return bool(os.environ.get("CISCO_CLIENT_ID") and os.environ.get("CISCO_CLIENT_SECRET"))


def get_context_repo():
    """Get context repository configured for this app."""
    from app.context_store import ContextRepository

    return ContextRepository(current_app.config["CONTEXT_STORE_PATH"])


def is_debug_capability_enabled() -> bool:
    """Check whether debug capability is enabled in server config."""
    return bool(current_app.config.get("DEBUG_MODE_ENABLED", False))


@main_bp.route("/")
def index():
    """Home page with JIRA input form."""
    return render_template("input.html")


@main_bp.route("/generate", methods=["POST"])
def generate():
    """Generate workflow from JIRA requirements."""
    from app.parser import parse_jira_text
    from app.rule_engine import RuleEngine
    from app.generator import WorkflowGenerator
    from app.validator import WorkflowValidator
    
    # Get JIRA text from form
    jira_text = request.form.get("jira_text", "")
    
    if not jira_text.strip():
        return jsonify({"error": "Please provide JIRA requirements text"}), 400
    
    try:
        # Parse the JIRA text to extract requirements
        requirements = parse_jira_text(jira_text)
        
        # Use rule engine to match requirements to templates
        rule_engine = RuleEngine()
        matched_templates = rule_engine.match(requirements)
        
        if not matched_templates:
            return jsonify({
                "error": "No matching workflow templates found for the given requirements",
                "parsed_requirements": requirements
            }), 404
        
        # Generate workflow from templates
        generator = WorkflowGenerator()
        workflow_json = generator.generate(matched_templates, requirements)
        
        # Validate the generated workflow
        validator = WorkflowValidator()
        validation_result = validator.validate(workflow_json)
        
        # Generate Mermaid diagram for preview
        mermaid_diagram = generator.generate_mermaid(workflow_json)
        
        return jsonify({
            "success": True,
            "workflow": workflow_json,
            "mermaid": mermaid_diagram,
            "validation": validation_result,
            "matched_templates": [t["name"] for t in matched_templates]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/preview", methods=["POST"])
def preview():
    """Preview generated workflow with Mermaid diagram."""
    data = request.get_json()
    
    if not data or "workflow" not in data:
        return jsonify({"error": "No workflow data provided"}), 400
    
    from app.generator import WorkflowGenerator
    
    generator = WorkflowGenerator()
    mermaid_diagram = generator.generate_mermaid(data["workflow"])
    
    return jsonify({
        "mermaid": mermaid_diagram,
        "workflow": data["workflow"]
    })


@main_bp.route("/export", methods=["POST"])
def export():
    """Export workflow as downloadable JSON file."""
    data = request.get_json()
    
    if not data or "workflow" not in data:
        return jsonify({"error": "No workflow data provided"}), 400
    
    workflow_json = json.dumps(data["workflow"], indent=2)
    
    return Response(
        workflow_json,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=intersight_workflow.json"}
    )


@main_bp.route("/validate", methods=["POST"])
def validate():
    """Validate a workflow JSON."""
    data = request.get_json()
    
    if not data or "workflow" not in data:
        return jsonify({"error": "No workflow data provided"}), 400
    
    from app.validator import WorkflowValidator
    
    validator = WorkflowValidator()
    result = validator.validate(data["workflow"])
    
    return jsonify(result)


@main_bp.route("/templates")
def list_templates():
    """List available workflow templates."""
    from app.rule_engine import RuleEngine
    
    rule_engine = RuleEngine()
    templates = rule_engine.list_templates()
    
    return jsonify({"templates": templates})


# ============================================================================
# LLM-Based Generation Endpoints
# ============================================================================

@main_bp.route("/generate/llm", methods=["POST"])
def generate_with_llm():
    """
    Generate workflow from JIRA text using GPT-4.1 LLM.
    
    This endpoint uses Cisco's Chat AI to intelligently parse JIRA text
    and generate the appropriate workflow.
    
    Request body (form or JSON):
        jira_text: The JIRA ticket text to analyze
        
    Returns:
        JSON with workflow, analysis, validation, and mermaid diagram
    """
    if not is_llm_configured():
        return jsonify({
            "error": "LLM not configured. Set CISCO_CLIENT_ID and CISCO_CLIENT_SECRET environment variables.",
            "hint": "Copy .env.example to .env and add your credentials"
        }), 503
    
    # Get JIRA text from form or JSON
    selected_context_ids = None
    debug_mode = is_debug_capability_enabled() and debug_requested(request)
    if request.is_json:
        data = request.get_json()
        jira_text = data.get("jira_text", "")
        selected_context_ids = data.get("context_ids", [])
    else:
        jira_text = request.form.get("jira_text", "")
        raw_context_ids = request.form.get("context_ids", "").strip()
        if raw_context_ids:
            selected_context_ids = [item.strip() for item in raw_context_ids.split(",") if item.strip()]
    
    if not jira_text.strip():
        return jsonify({"error": "Please provide JIRA requirements text"}), 400
    
    try:
        from app.llm_generator import generate_workflow_with_llm
        context_repo = get_context_repo()
        selected_context, context_diagnostics = context_repo.select_for_prompt(
            jira_text=jira_text,
            selected_artifact_ids=selected_context_ids,
            available_budget_tokens=12000,
            max_artifacts=5,
        )
        
        result = generate_workflow_with_llm(
            jira_text,
            context_artifacts=[artifact.to_dict() for artifact in selected_context],
            context_diagnostics=context_diagnostics,
            debug_mode=debug_mode,
            debug_max_payload_chars=int(current_app.config.get("DEBUG_MODE_MAX_PAYLOAD_CHARS", 16000)),
        )
        
        if not result.get("success"):
            analysis = result.get("analysis", {})
            if not isinstance(analysis, dict):
                analysis = {}
            return jsonify({
                "error": result.get("error", "Failed to generate workflow"),
                "analysis": analysis,
                "warnings": analysis.get("warnings", []),
                "raw_response": result.get("raw_response", "")[:500] if result.get("raw_response") else None,
                "traceback": result.get("traceback"),
                "debug": result.get("debug") if debug_mode else None,
            }), 400
        if not debug_mode:
            result.pop("debug", None)
        return jsonify(result)
        
    except ValueError as e:
        # Credentials error
        return jsonify({
            "error": str(e),
            "hint": "Set CISCO_CLIENT_ID and CISCO_CLIENT_SECRET environment variables"
        }), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/analyze", methods=["POST"])
def analyze_jira():
    """
    Analyze JIRA text without generating a workflow.
    
    Useful for understanding what the LLM extracted from the text.
    
    Request body (form or JSON):
        jira_text: The JIRA ticket text to analyze
        
    Returns:
        JSON with analysis results
    """
    if not is_llm_configured():
        return jsonify({
            "error": "LLM not configured",
            "hint": "Set CISCO_CLIENT_ID and CISCO_CLIENT_SECRET environment variables"
        }), 503
    
    # Get JIRA text
    if request.is_json:
        data = request.get_json()
        jira_text = data.get("jira_text", "")
    else:
        jira_text = request.form.get("jira_text", "")
    
    if not jira_text.strip():
        return jsonify({"error": "Please provide JIRA requirements text"}), 400
    
    try:
        from app.llm_generator import analyze_jira_text
        
        analysis = analyze_jira_text(jira_text)
        return jsonify({"analysis": analysis})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/generate/custom", methods=["POST"])
def generate_custom_workflow():
    """
    Generate a completely custom workflow using LLM.
    
    This is an advanced feature where the LLM designs the entire workflow
    from detailed requirements.
    
    Request body (JSON):
        requirements: Detailed workflow requirements
        
    Returns:
        JSON with generated workflow
    """
    if not is_llm_configured():
        return jsonify({
            "error": "LLM not configured",
            "hint": "Set CISCO_CLIENT_ID and CISCO_CLIENT_SECRET environment variables"
        }), 503
    
    data = request.get_json()
    if not data or not data.get("requirements"):
        return jsonify({"error": "Please provide workflow requirements"}), 400
    
    try:
        from app.llm_generator import generate_custom_workflow
        
        result = generate_custom_workflow(data["requirements"])
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/status")
def status():
    """
    Get service status including LLM configuration.
    
    Returns:
        JSON with service status
    """
    return jsonify({
        "service": "ICO Workflow Generator",
        "version": "1.0.0",
        "llm_configured": is_llm_configured(),
        "llm_provider": "Cisco Chat AI (GPT-4.1)" if is_llm_configured() else None,
        "debug_mode_enabled": is_debug_capability_enabled(),
        "debug_policy": {
            "requires_per_request_toggle": True,
            "max_payload_chars": int(current_app.config.get("DEBUG_MODE_MAX_PAYLOAD_CHARS", 16000)),
            "redaction_enabled": True,
        },
        "endpoints": {
            "rule_based": "/generate",
            "llm_based": "/generate/llm",
            "analyze": "/analyze",
            "custom": "/generate/custom",
            "context_upload": "/context/upload",
            "context_github_public": "/context/github/public",
            "context_list": "/context",
        }
    })


@main_bp.route("/context", methods=["GET"])
def list_context_artifacts():
    """List available uploaded/imported context artifacts."""
    repo = get_context_repo()
    artifacts = [artifact.to_dict() for artifact in repo.list_artifacts()]
    return jsonify({"artifacts": artifacts})


@main_bp.route("/context/<artifact_id>", methods=["DELETE"])
def delete_context_artifact(artifact_id: str):
    """Delete a context artifact by ID."""
    repo = get_context_repo()
    deleted = repo.delete_artifact(artifact_id)
    if not deleted:
        return jsonify({"error": "Artifact not found"}), 404
    return jsonify({"success": True, "artifact_id": artifact_id})


@main_bp.route("/context/upload", methods=["POST"])
def upload_context_artifact():
    """Upload ICO workflow/task JSON files for ad-hoc context."""
    from app.context_ingestors.upload_ingestor import UploadIngestor

    if "files" not in request.files:
        return jsonify({"error": "No files provided. Use multipart field 'files'"}), 400

    files = request.files.getlist("files")
    max_files = int(current_app.config.get("CONTEXT_MAX_UPLOAD_FILES", 10))
    if len(files) > max_files:
        return jsonify({"error": f"Too many files uploaded. Maximum is {max_files}"}), 400

    ingestor = UploadIngestor()
    repo = get_context_repo()
    accepted = []
    rejected = []

    for file_obj in files:
        try:
            raw_bytes = file_obj.read()
            artifact = ingestor.ingest(file_obj.filename, raw_bytes, owner="user")
            repo.upsert_artifact(artifact)
            accepted.append(artifact.to_dict())
        except Exception as exc:
            rejected.append({"name": getattr(file_obj, "filename", "unknown"), "error": str(exc)})

    return jsonify({"accepted": accepted, "rejected": rejected})


@main_bp.route("/context/github/public", methods=["POST"])
def import_context_from_github_public():
    """Ingest ICO context artifacts from a public GitHub repository."""
    from app.context_ingestors.github_public_ingestor import GitHubPublicIngestor

    data = request.get_json(silent=True) or {}
    repo_url = data.get("repo_url", "").strip()
    if not repo_url:
        return jsonify({"error": "Missing required field: repo_url"}), 400

    try:
        ingestor = GitHubPublicIngestor(max_files=10)
        artifacts = ingestor.ingest_repo(repo_url=repo_url, owner="user")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    repo = get_context_repo()
    for artifact in artifacts:
        repo.upsert_artifact(artifact)

    return jsonify(
        {
            "success": True,
            "repo_url": repo_url,
            "imported_count": len(artifacts),
            "artifacts": [artifact.to_dict() for artifact in artifacts],
        }
    )
