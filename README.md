# Ryker Room — Unified Multi-Standard Compliance Vault

An automated, continuous compliance and evidence vault supporting **AICPA SOC 2 (Type II)**, **ISO/IEC 27001:2022**, and **NIST CSF 2.0**.

## Core Architecture & Capabilities

- **Continuous Ingestion Telemetry**: Ingests automated SecOps events via GitHub PR webhooks and AWS CloudTrail console logins.
- **Cryptographic Evidence Vault**: Seals evidence artifacts with canonical SHA-256 digests and enforces an immutable 7-year WORM retention hold.
- **Cross-Framework Control Mapping**: Eliminates audit redundancy with a 2.67x evidence re-use ratio across SOC 2 (CC6.1, CC7.1, CC8.1), ISO 27001 (Annex A.8.28, A.5.15, A.8.8), and NIST CSF 2.0 (PR.PS-01, PR.AA-01, DE.CM-01).
- **Deterministic SSAE 18 Attribute Sampler**: Cryptographically seeded pseudo-random audit sampling for reproducible population testing.
- **Continuous Drift Detection Engine**: Detects branch protection deviations and MFA policy exemptions in real time.
- **Signed Auditor Workpapers**: Generates dynamic, partner-attested compliance workpaper PDFs backed by Merkle root consistency verification.

## Quickstart (Docker Stack)

```bash
# Build and launch PostgreSQL and API services
docker compose up -d

# Verify container health
docker compose ps

# Access Portal and Swagger UI
# Portal:    http://localhost:8000/portal
# API Docs:  http://localhost:8000/docs

# Verified branch protection rule
