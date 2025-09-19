from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class ExamItem(BaseModel):
    question: str
    options: List[str] = Field(min_length=4, max_length=4)
    answer: str
    notes: Optional[str] = None

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str, values):
        if v not in {"A", "B", "C", "D"}:
            raise ValueError("answer must be one of A,B,C,D")
        return v

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: List[str]):
        if len(v) != 4:
            raise ValueError("There must be exactly 4 options")
        return v 