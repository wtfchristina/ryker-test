import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class EngagementCreate(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Alpha SOC 2 Type II - 2026"})
    framework: str = Field(..., json_schema_extra={"example": "SOC2_TYPE_II"})
    period_start: date
    period_end: date
    lead_partner_id: uuid.UUID

class EngagementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    framework: str
    period_start: date
    period_end: date
    status: str

class ControlCreate(BaseModel):
    framework_code: str = Field(..., json_schema_extra={"example": "CC8.1"})
    name: str = Field(..., json_schema_extra={"example": "Change Management & Peer Review"})
    description: str
    testing_procedure: str
    frequency: str = "CONTINUOUS"

class ControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    framework_code: str
    name: str
    description: str
    testing_procedure: str
    frequency: str

class IngestEvidenceRequest(BaseModel):
    control_id: uuid.UUID
    control_code: str
    source_name: str
    file_name: str
    payload: Dict[str, Any]
    uploaded_by: uuid.UUID

class SamplingRequest(BaseModel):
    control_id: uuid.UUID
    population: List[Dict[str, Any]]
    seed_override: Optional[str] = None
