"""Flask routes for the ICO Workflow Generator."""

from flask import Blueprint, Response, current_app, jsonify, render_template, request
import json
from app.debug_utils import debug_requested
from app.llm_settings import (
    LLM_MODEL_DISPLAY_NAME,
    LLMSettingsStore,
    is_effectively_configured,
    masked_settings,
    resolve_effective_settings,
)

main_bp = Blueprint("main", __name__)


def is_llm_configured() -> bool:
    """Check if LLM credentials are configured."""
    store = get_llm_settings_store()
    return is_effectively_configured(resolve_effective_settings(store))


def get_context_repo():
    """Get context repository configured for this app."""
    from app.context_store import ContextRepository

    return ContextRepository(current_app.config["CONTEXT_STORE_PATH"])


def get_llm_settings_store() -> LLMSettingsStore:
    """Get LLM settings store configured for this app."""
    return LLMSettingsStore(current_app.config["LLM_SETTINGS_PATH"])


def build_llm_client():
    """Build LLM client from local settings (with env fallback)."""
    from app.llm_client import CiscoLLMClient

    settings = resolve_effective_settings(get_llm_settings_store())
    return CiscoLLMClient(
        client_id=settings.get("client_id"),
        client_secret=settings.get("client_secret"),
        appkey=settings.get("appkey"),
        username=settings.get("username") or None,
        oauth_url=settings.get("oauth_url") or None,
        chat_url=settings.get("chat_url") or None,
    )


def is_debug_capability_enabled() -> bool:
    """Check whether debug capability is enabled in server config."""
    return bool(current_app.config.get("DEBUG_MODE_ENABLED", False))


@main_bp.route("/")
def index():
    """Home page with JIRA input form."""
    return render_template("input.html")


@main_bp.route("/context-manager")
def context_manager():
    """Dedicated page for context source configuration."""
    return render_template("context.html")


@main_bp.route("/llm-setup")
def llm_setup_page():
    """Dedicated page for LLM setup and connectivity checks."""
    return render_template("llm_setup.html")


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
            "error": (
                "LLM not configured. Set CISCO_CLIENT_ID, CISCO_CLIENT_SECRET, "
                "and CISCO_APPKEY environment variables."
            ),
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
        llm_client = build_llm_client()
        selected_context, context_diagnostics = context_repo.select_for_prompt(
            jira_text=jira_text,
            selected_artifact_ids=selected_context_ids,
            available_budget_tokens=12000,
            max_artifacts=5,
        )
        
        result = generate_workflow_with_llm(
            jira_text,
            llm_client=llm_client,
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
            "hint": "Set CISCO_CLIENT_ID, CISCO_CLIENT_SECRET, and CISCO_APPKEY environment variables"
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
            "hint": "Set CISCO_CLIENT_ID, CISCO_CLIENT_SECRET, and CISCO_APPKEY environment variables"
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

        analysis = analyze_jira_text(jira_text, llm_client=build_llm_client())
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
            "hint": "Set CISCO_CLIENT_ID, CISCO_CLIENT_SECRET, and CISCO_APPKEY environment variables"
        }), 503
    
    data = request.get_json()
    if not data or not data.get("requirements"):
        return jsonify({"error": "Please provide workflow requirements"}), 400
    
    try:
        from app.llm_generator import generate_custom_workflow

        result = generate_custom_workflow(data["requirements"], llm_client=build_llm_client())
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/generate/openapi", methods=["POST"])
def generate_from_openapi():
    """Generate workflow from uploaded OpenAPI specification."""
    from app.context_ingestors.openapi_ingestor import OpenAPIIngestor
    from app.openapi_generator import generate_workflow_from_openapi_spec

    file_obj = request.files.get("openapi_file") or request.files.get("file")
    if file_obj is None:
        return jsonify({"error": "Missing OpenAPI file upload. Use multipart field 'openapi_file'."}), 400

    filename = (file_obj.filename or "").strip()
    if not filename:
        return jsonify({"error": "Uploaded OpenAPI file must have a filename."}), 400

    lowered = filename.lower()
    if not (lowered.endswith(".json") or lowered.endswith(".yaml") or lowered.endswith(".yml")):
        return jsonify({"error": "OpenAPI upload must be .json, .yaml, or .yml"}), 400

    try:
        raw_bytes = file_obj.read()
        spec = OpenAPIIngestor().parse_spec(raw_bytes, filename)
        max_operations = request.form.get("max_operations")
        path_prefix = request.form.get("path_prefix")
        tag = request.form.get("tag")
        include_sample_workflow_raw = request.form.get("include_sample_workflow")
        include_sample_workflow = True
        if isinstance(include_sample_workflow_raw, str) and include_sample_workflow_raw.strip():
            include_sample_workflow = include_sample_workflow_raw.strip().lower() not in {"0", "false", "no", "off"}

        result = generate_workflow_from_openapi_spec(
            spec,
            max_operations=int(max_operations) if max_operations else None,
            path_prefix=path_prefix,
            tag=tag,
            include_sample_workflow=include_sample_workflow,
        )
        if not result.get("success"):
            return jsonify(result), 400
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@main_bp.route("/status")
def status():
    """
    Get service status including LLM configuration.
    
    Returns:
        JSON with service status
    """
    effective_llm_settings = resolve_effective_settings(get_llm_settings_store())
    return jsonify({
        "service": "ICO Workflow Generator",
        "version": "1.0.0",
        "llm_configured": is_effectively_configured(effective_llm_settings),
        "llm_provider": "LLM",
        "llm_model": LLM_MODEL_DISPLAY_NAME,
        "debug_mode_enabled": is_debug_capability_enabled(),
        "debug_policy": {
            "requires_per_request_toggle": True,
            "max_payload_chars": int(current_app.config.get("DEBUG_MODE_MAX_PAYLOAD_CHARS", 16000)),
            "redaction_enabled": True,
        },
        "endpoints": {
            "llm_based": "/generate/llm",
            "openapi_based": "/generate/openapi",
            "analyze": "/analyze",
            "custom": "/generate/custom",
            "llm_setup_page": "/llm-setup",
            "llm_setup": "/llm/setup",
            "llm_test": "/llm/test",
            "context_manager": "/context-manager",
            "context_upload": "/context/upload",
            "context_github_public": "/context/github/public",
            "context_list": "/context",
        }
    })


@main_bp.route("/llm/setup", methods=["GET"])
def get_llm_setup():
    """Get merged LLM settings for setup UI (masked)."""
    store = get_llm_settings_store()
    effective = resolve_effective_settings(store)
    local = store.load_local()
    return jsonify(
        {
            "model": LLM_MODEL_DISPLAY_NAME,
            "configured": is_effectively_configured(effective),
            "settings": masked_settings(effective),
            "meta": {
                "source": "local+env",
                "has_local_settings": bool(local),
            },
        }
    )


@main_bp.route("/llm/setup", methods=["POST"])
def save_llm_setup():
    """Persist editable LLM settings to local file."""
    payload = request.get_json(silent=True) or {}
    store = get_llm_settings_store()
    try:
        saved = store.save(payload)
        from app.llm_client import reset_llm_client

        reset_llm_client()
        return jsonify(
            {
                "success": True,
                "model": LLM_MODEL_DISPLAY_NAME,
                "configured": is_effectively_configured(saved),
                "settings": masked_settings(saved),
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@main_bp.route("/llm/test", methods=["POST"])
def test_llm_setup():
    """Validate LLM connectivity for current effective settings."""
    try:
        client = build_llm_client()
        token = client._get_access_token()
        if not token:
            raise RuntimeError("Access token acquisition returned empty token")
        return jsonify(
            {
                "success": True,
                "model": LLM_MODEL_DISPLAY_NAME,
                "message": "LLM connectivity check passed",
            }
        )
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "model": LLM_MODEL_DISPLAY_NAME,
                "error": str(exc),
            }
        ), 400


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
