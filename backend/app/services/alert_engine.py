import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

class AlertNotificationService:
    @staticmethod
    def dispatch_drift_alert(
        webhook_url: Optional[str],
        tenant_name: str,
        drifts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Dispatches structured alert payloads to Slack/Discord/custom SecOps webhook endpoints.
        """
        if not drifts:
            return {"dispatched": False, "reason": "No drifts detected"}

        slack_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Ryker Room Compliance Drift Alert: {tenant_name}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Timestamp:* `{datetime.now(timezone.utc).isoformat()}`\n*Violations Detected:* `{len(drifts)}`"
                }
            },
            {"type": "divider"}
        ]

        for d in drifts:
            slack_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{d.get('control_code')}* — *{d.get('title')}* [{d.get('severity')}]\n>{d.get('detail')}"
                }
            })

        payload = {"blocks": slack_blocks, "text": f"Ryker Room Drift Alert: {len(drifts)} violations detected"}

        if webhook_url:
            try:
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    return {"dispatched": True, "http_status": response.status}
            except Exception as e:
                return {"dispatched": False, "error": str(e)}

        return {"dispatched": True, "dry_run_payload": payload}


class LedgerIntegrityService:
    @staticmethod
    def compute_merkle_root(hashes: List[str]) -> str:
        """
        Builds a canonical Merkle tree root hash across all sealed artifacts.
        Proves ledger integrity across continuous audit periods.
        """
        if not hashes:
            return hashlib.sha256(b"EMPTY_LEDGER").hexdigest()

        current_level = sorted(hashes)
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = hashlib.sha256(f"{left}:{right}".encode("utf-8")).hexdigest()
                next_level.append(combined)
            current_level = next_level

        return current_level[0]
