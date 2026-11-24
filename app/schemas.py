"""Shapes of request and response bodies."""

from pydantic import BaseModel, Field


class ValidateRequest(BaseModel):
    value: str = Field(min_length=1, max_length=64, examples=["AAAPA1234A"])


class ValidationResponse(BaseModel):
    id_type: str
    is_valid: bool
    masked_value: str
    errors: list[str]
    details: dict[str, str]


class BatchItem(BaseModel):
    id_type: str = Field(examples=["pan"])
    value: str = Field(min_length=1, max_length=64, examples=["AAAPA1234A"])


class BatchRequest(BaseModel):
    items: list[BatchItem] = Field(min_length=1, max_length=100)


class BatchResponse(BaseModel):
    total: int
    valid: int
    invalid: int
    results: list[ValidationResponse]


class GstinPanMatchRequest(BaseModel):
    gstin: str = Field(min_length=1, max_length=64)
    pan: str = Field(min_length=1, max_length=64)


class GstinPanMatchResponse(BaseModel):
    gstin_valid: bool
    pan_valid: bool
    match: bool


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["my-app"])


class ApiKeyCreated(BaseModel):
    id: int
    name: str
    api_key: str


class TypeStats(BaseModel):
    id_type: str
    total: int
    valid: int
    invalid: int


class DailyStats(BaseModel):
    day: str
    requests: int
    running_total: int


class StatsResponse(BaseModel):
    total_validations: int
    by_type: list[TypeStats]
    daily: list[DailyStats]
