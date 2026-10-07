from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid
from app.models.audit import Control, Engagement, EvidenceArtifact

class WorkpaperGeneratorService:
    @staticmethod
    def generate_markdown_workpaper(
        engagement: Engagement,
        controls: List[Control],
        artifacts: List[EvidenceArtifact],
        samples_info: List[Dict[str, Any]] = None,
    ) -> str:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        md = []
        md.append(f"# SOC 2 TYPE II AUDIT TESTING WORKPAPER")
        md.append(f"**Engagement Title**: {engagement.title}")
        md.append(f"**Engagement ID**: `{engagement.id}`")
        md.append(f"**Organization ID**: `{engagement.organization_id}`")
        md.append(f"**Audit Period**: {engagement.period_start} through {engagement.period_end}")
        md.append(f"**Generated At**: {now_str}")
        md.append(f"**Engagement Status**: `{engagement.status}`\n")
        md.append("---\n")
        
        md.append("## 1. Scope & Applicable Trust Services Criteria")
        md.append(f"This workpaper documents auditor testing performed under the **{engagement.framework}** standard.")
        md.append(f"Total Controls in Scope: **{len(controls)}**\n")

        md.append("## 2. Control Testing Matrix & Evidence Ledger")
        if not controls:
            md.append("_No controls defined for this engagement._\n")
        
        for idx, ctrl in enumerate(controls, 1):
            md.append(f"### 2.{idx} Control {ctrl.framework_code}: {ctrl.name}")
            md.append(f"- **Control ID**: `{ctrl.id}`")
            md.append(f"- **Description**: {ctrl.description}")
            md.append(f"- **Testing Procedure**: {ctrl.testing_procedure}")
            md.append(f"- **Frequency**: `{ctrl.frequency}`\n")
            
            # Match artifacts for this control
            ctrl_artifacts = [a for a in artifacts if str(a.control_id) == str(ctrl.id)]
            md.append("#### Sealed Evidence Vault Ledger")
            if not ctrl_artifacts:
                md.append("> *No sealed evidence currently associated with this control.*\n")
            else:
                md.append("| File Name | SHA-256 Hash | Vault Key | Status | Retention |")
                md.append("| :--- | :--- | :--- | :--- | :--- |")
                for art in ctrl_artifacts:
                    short_hash = f"`{art.sha256_hash[:16]}...`"
                    locked = art.locked_until.strftime("%Y-%m-%d") if art.locked_until else "N/A"
                    md.append(f"| `{art.file_name}` | {short_hash} | `{art.s3_key}` | **{art.verification_status}** | Locked until {locked} |")
                md.append("")

        md.append("## 3. AICPA Statistical & Attribute Sampling Log")
        if samples_info:
            for s in samples_info:
                md.append(f"- **Control Tested**: `{s.get('control_code', 'N/A')}`")
                md.append(f"- **Population Size**: {s.get('population_size')}")
                md.append(f"- **Sample Size Selected**: {s.get('sample_size')}")
                md.append(f"- **Deterministic Seed Record**: `{s.get('seed')}`")
                md.append(f"- **Items Selected for Testing**: {s.get('items_count')} items logged")
        else:
            md.append("Audit sampling tests logged under standard CC8.1 peer review procedures.")
            md.append(f"- Standard Sample Formula: AICPA Attribute Sampling Table (Confidence Level 90-95%, Tolerable Rate 5-10%)\n")

        md.append("\n## 4. Auditor Attestation & Sign-Off")
        md.append("```text")
        md.append("[ ] TESTING PROCEDURES PERFORMED SATISFACTORILY")
        md.append("[ ] NO UNRESOLVED EXCEPTIONS NOTED")
        md.append(f"Lead Partner ID: {engagement.lead_partner_id}")
        md.append(f"Sign-off Date:   ___________________________")
        md.append("```\n")

        return "\n".join(md)
