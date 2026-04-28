from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, RootModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class CameraCreate(BaseModel):
    user_id: int
    name: str
    source: str
    selected_model: str = "ppe"


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    source: str
    selected_model: str
    is_active: bool
    last_status: str | None = None
    last_error: str | None = None


class CameraBatchItem(BaseModel):
    name: str
    source: str
    selected_model: str = "ppe"


class CameraBatchCreate(BaseModel):
    user_id: int
    cameras: List[CameraBatchItem]


class FrameSummaryCreate(BaseModel):
    user_id: int
    camera_id: int
    frame_index: int
    wearing: int
    not_wearing: int
    persons: int
    in_count: int
    out_count: int
    inference_ms: float


class CountResponse(BaseModel):
    in_: int
    out: int
    total_inside: int


class PPESummaryResponse(BaseModel):
    hardhat: int
    mask: int
    gloves: int
    vest: int
    wearing: int
    not_wearing: int
    compliance_rate: str


class ViolationDailyResponse(RootModel[Dict[str, int]]):
    pass


class LatestViolation(BaseModel):
    image_url: str
    gate: str
    issues: List[str]


class FrameNotificationCreate(BaseModel):
    user_id: int
    camera_id: int
    frame_index: int
    person_id: int
    violation_type: str
    message: str
    image_url: str | None = None


class FrameNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    frame_index: int
    person_id: int
    violation_type: str
    message: str
    timestamp: str
    camera_id: int
    image_url: str | None = None


class PPEAlertItem(BaseModel):
    count: int
    drop: float


class PPEAlertSummaryResponse(BaseModel):
    hardhat: PPEAlertItem
    vest: PPEAlertItem
    mask: PPEAlertItem
    gloves: PPEAlertItem


class PersonPPEStatusCreate(BaseModel):
    user_id: int
    camera_id: int
    frame_index: int
    person_id: int
    person: str
    gloves: str
    hardhat: str
    mask: str
    vest: str


class PersonPPEStatusOut(PersonPPEStatusCreate):
    model_config = ConfigDict(from_attributes=True)
    timestamp: datetime