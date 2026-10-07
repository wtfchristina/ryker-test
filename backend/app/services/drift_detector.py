from datetime import datetime, timezone
from typing import Any, Dict, List

class DriftDetectionEngine:
    @staticmethod
    def evaluate_posture(controls_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        drifts = []
        passing = 0

        for item in controls_data:
            code = item.get("code")
            payload = item.get("payload", {})

            if code == "CC8.1":
                if payload.get("required_approving_review_count", 0) < 1 or not payload.get("enforce_admins"):
                    drifts.append({
                        "control_code": "CC8.1",
                        "severity": "CRITICAL",
                        "title": "Branch Protection Compromised",
                        "detail": "Admin enforcement is disabled or review count is below minimum threshold.",
                        "detected_at": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    passing += 1

            elif code == "CC6.1":
                if payload.get("enforcement") != "REQUIRED" or payload.get("exemptions_count", 0) > 0:
                    drifts.append({
                        "control_code": "CC6.1",
                        "severity": "HIGH",
                        "title": "MFA Exemption Policy Drift",
                        "detail": f"{payload.get('exemptions_count', 0)} active exemptions detected on SSO provider.",
                        "detected_at": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    passing += 1

            elif code == "CC7.1":
                vulns = payload.get("vulnerabilities", {})
                if vulns.get("critical", 0) > 0 or vulns.get("high", 0) > 0:
                    drifts.append({
                        "control_code": "CC7.1",
                        "severity": "CRITICAL",
                        "title": "Unpatched Critical Vulnerability in CI",
                        "detail": f"{vulns.get('critical')} critical, {vulns.get('high')} high vulnerabilities detected.",
                        "detected_at": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    passing += 1

        overall_status = "COMPLIANT" if not drifts else "DRIFT_DETECTED"
        return {
            "status": overall_status,
            "passing_controls": passing,
            "total_evaluated": len(controls_data),
            "drifts": drifts,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
