import hmac
import hashlib
import json
from typing import Any, Dict, Optional
import uuid
from app.services.vault import EvidenceVaultService

class GitHubWebhookService:
    @staticmethod
    def verify_signature(payload_bytes: bytes, secret: str, signature_header: Optional[str]) -> bool:
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected_sig = signature_header.split("sha256=")[-1]
        computed_sig = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed_sig, expected_sig)

    @staticmethod
    def process_pull_request_event(
        event_data: Dict[str, Any],
        organization_id: uuid.UUID,
        engagement_id: uuid.UUID,
        control_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        action = event_data.get("action")
        pr = event_data.get("pull_request", {})
        merged = pr.get("merged", False)

        if action == "closed" and merged:
            payload = {
                "pr_number": pr.get("number"),
                "title": pr.get("title"),
                "base_branch": pr.get("base", {}).get("ref"),
                "merged_by": pr.get("merged_by", {}).get("login"),
                "merged_at": pr.get("merged_at"),
                "commits_count": pr.get("commits"),
                "review_comments": pr.get("review_comments"),
            }
            vault = EvidenceVaultService()
            raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            
            result = vault.seal_evidence_payload(
                organization_id=organization_id,
                engagement_id=engagement_id,
                control_id=control_id,
                control_code="CC8.1",
                source_name="GITHUB_WEBHOOK",
                file_name=f"pr_{pr.get('number')}_audit_trail.json",
                raw_bytes=raw_bytes,
                uploaded_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            )
            return result
        return None
