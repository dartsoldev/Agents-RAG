"""Validate intake, staff updates and attorney decisions before persistence."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginInput(InputModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: str = Field(min_length=3, max_length=250)
    password: str = Field(min_length=1, max_length=200)


class CaseInput(InputModel):
    client_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=250, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str = Field(default="", max_length=60)
    accident_date: date
    jurisdiction: str = Field(min_length=2, max_length=100)
    case_type: str = Field(default="Auto accident", max_length=100)
    injuries: str = Field(default="", max_length=8000)
    attorney: str = Field(default="Unassigned", max_length=120)
    paralegal: str = Field(default="Unassigned", max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator("accident_date")
    @classmethod
    def past_accident(cls, value):
        if value > date.today():
            raise ValueError("Accident date cannot be in the future")
        return value


class MedicalInput(InputModel):
    provider: str = Field(default="", max_length=200)
    diagnosis: str = Field(default="", max_length=4000)
    treatment: str = Field(default="", max_length=2000)
    last_visit: date | None = None
    status: Literal["unknown", "ongoing", "complete"] = "unknown"
    bills_cents: int = Field(default=0, ge=0, le=100_000_000_000)

    @field_validator("last_visit")
    @classmethod
    def past_visit(cls, value):
        if value and value > date.today():
            raise ValueError("Last recorded visit cannot be in the future")
        return value


class InsuranceInput(InputModel):
    carrier: str = Field(default="", max_length=200)
    claim_number: str = Field(default="", max_length=100)
    policy_number: str = Field(default="", max_length=100)
    adjuster: str = Field(default="", max_length=200)
    last_response: date | None = None
    policy_limit_cents: int = Field(default=0, ge=0, le=100_000_000_000)
    offer_cents: int = Field(default=0, ge=0, le=100_000_000_000)
    liability: str = Field(default="Unverified", max_length=2000)

    @field_validator("last_response")
    @classmethod
    def past_response(cls, value):
        if value and value > date.today():
            raise ValueError("Last recorded response cannot be in the future")
        return value


class TaskInput(InputModel):
    title: str = Field(min_length=3, max_length=250)
    due_date: date
    priority: Literal["normal", "high"] = "normal"


class TaskUpdate(InputModel):
    completed: bool


class QuestionInput(InputModel):
    question: str = Field(min_length=3, max_length=2000)


class DecisionInput(InputModel):
    decision: Literal["approved", "rejected"]
    body: str | None = Field(default=None, max_length=30000)
    note: str = Field(default="", max_length=2000)


class StageInput(InputModel):
    stage: Literal[
        "intake",
        "documents",
        "treatment",
        "demand",
        "negotiation",
        "settled",
        "litigation",
        "closed",
    ]
    settlement_cents: int | None = Field(default=None, ge=1, le=100_000_000_000)
    note: str = Field(min_length=3, max_length=2000)


class UserInput(InputModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=250)
    name: str = Field(min_length=2, max_length=120)
    role: Literal["admin", "attorney", "paralegal"]
    password: str = Field(min_length=12, max_length=200)


class FilevineLinkInput(InputModel):
    project_id: str = Field(pattern=r"^[0-9]{1,20}$")
