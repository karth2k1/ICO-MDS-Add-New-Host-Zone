"""Context artifact models for dynamic LLM prompt enrichment."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
import hashlib


def utc_now_iso() -> str:
    """Return current UTC time in ISO8601 format."""
    return datetime.now(timezone.utc).isoformat()


def short_sha256(value: str) -> str:
    """Return short SHA256 fingerprint for deterministic IDs."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:16]


@dataclass
class ContextArtifact:
    """Represents a user-provided workflow/task artifact for context."""

    artifact_id: str
    name: str
    source_type: str
    source_reference: str
    domain: str = "generic"
    validation_status: str = "validated"
    validated_on: str = field(default_factory=utc_now_iso)
    owner: str = "user"
    created_at: str = field(default_factory=utc_now_iso)
    content: List[Dict[str, Any]] = field(default_factory=list)
    content_preview: str = ""
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to a serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ContextArtifact":
        """Create an artifact object from serialized data."""
        return cls(**payload)

