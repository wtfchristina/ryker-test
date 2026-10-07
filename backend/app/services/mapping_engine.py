from typing import Dict, List

# Authoritative SOC 2 -> ISO 27001 & NIST CSF cross-framework dictionary
FRAMEWORK_MAPPINGS: Dict[str, List[Dict[str, str]]] = {
    "CC6.1": [
        {"framework": "ISO_27001", "code": "A.5.15", "name": "Access Control", "description": "Authenticated access control policy"},
        {"framework": "ISO_27001", "code": "A.8.5", "name": "Secure Authentication", "description": "Mandatory multi-factor authentication"},
        {"framework": "NIST_CSF", "code": "PR.AA-01", "name": "Identities & Credentials", "description": "Identity assertions and lifecycle"},
        {"framework": "NIST_CSF", "code": "PR.AA-03", "name": "Authentication", "description": "MFA and cryptographic identity verification"}
    ],
    "CC8.1": [
        {"framework": "ISO_27001", "code": "A.8.28", "name": "Secure Coding", "description": "Peer reviews and branch protection gates"},
        {"framework": "ISO_27001", "code": "A.8.32", "name": "Change Management", "description": "Production change authorization"},
        {"framework": "NIST_CSF", "code": "PR.PS-01", "name": "Configuration Management", "description": "System changes verified and approved"}
    ],
    "CC7.1": [
        {"framework": "ISO_27001", "code": "A.8.8", "name": "Vulnerability Management", "description": "Technical vulnerability identification"},
        {"framework": "NIST_CSF", "code": "DE.CM-01", "name": "Continuous Monitoring", "description": "Automated pipeline and container scans"}
    ]
}

class CrossFrameworkMappingService:
    @staticmethod
    def get_mappings_for_code(control_code: str) -> List[Dict[str, str]]:
        return FRAMEWORK_MAPPINGS.get(control_code, [])

    @staticmethod
    def get_all_mappings() -> Dict[str, List[Dict[str, str]]]:
        return FRAMEWORK_MAPPINGS
