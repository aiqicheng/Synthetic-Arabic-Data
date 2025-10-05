from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class MMLUItem(BaseModel):
    """Schema for Arabic MMLU dataset items"""
    question: str = Field(..., description="The question text in Arabic")
    options: List[str] = Field(min_length=4, max_length=4, description="List of 4 answer options")
    answer: str = Field(..., description="Correct answer letter (A, B, C, or D)")
    context: Optional[str] = Field(None, description="Optional context or additional information")
    subject: Optional[str] = Field(None, description="Subject area (e.g., Computer Science)")
    level: Optional[str] = Field(None, description="Difficulty level (e.g., High School)")
    country: Optional[str] = Field(None, description="Country of origin")
    group: Optional[str] = Field(None, description="Subject group (e.g., STEM)")
    is_few_shot: Optional[bool] = Field(False, description="Whether this is a few-shot example")

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str):
        if v not in {"A", "B", "C", "D"}:
            raise ValueError("answer must be one of A,B,C,D")
        return v

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: List[str]):
        if len(v) != 4:
            raise ValueError("There must be exactly 4 options")
        return v

    @field_validator("question")
    @classmethod
    def validate_question_not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class MMLURawItem(BaseModel):
    """Schema for raw MMLU CSV data before processing"""
    ID: str
    Country: Optional[str] = None
    Group: Optional[str] = None
    Subject: str
    Level: str
    Question: str
    Context: Optional[str] = None
    Answer_Key: str = Field(alias="Answer Key")  # Map "Answer Key" column
    Option_1: str = Field(alias="Option 1")      # Map "Option 1" column
    Option_2: str = Field(alias="Option 2")      # Map "Option 2" column
    Option_3: str = Field(alias="Option 3")      # Map "Option 3" column
    Option_4: str = Field(alias="Option 4")      # Map "Option 4" column
    Option_5: Optional[str] = Field(None, alias="Option 5")  # Map "Option 5" column
    is_few_shot: Optional[bool] = False

    class Config:
        populate_by_name = True

    @field_validator("Answer_Key")
    @classmethod
    def validate_answer_key(cls, v: str):
        """Accept A, B, C, D, or E as valid answer keys in raw data"""
        if v.upper() not in {"A", "B", "C", "D", "E"}:
            raise ValueError("Answer_Key must be one of A,B,C,D,E")
        return v.upper()

    def to_mmlu_item(self) -> MMLUItem:
        """Convert raw MMLU item to processed MMLU item"""
        # Filter out empty options and collect all non-empty ones
        all_options = [opt.strip() for opt in [self.Option_1, self.Option_2, self.Option_3, self.Option_4, self.Option_5] if opt and opt.strip()]
        
        # Handle 5-option questions: if we have 5 options and answer is E, map E to D
        original_answer = self.Answer_Key.strip().upper()
        processed_answer = original_answer
        
        if len(all_options) == 5 and original_answer == "E":
            # For 5-option questions with E answer, take first 4 options and map E->D
            options = all_options[:4]
            processed_answer = "D"
        elif len(all_options) >= 4:
            # Take first 4 options for standard processing
            options = all_options[:4]
            # If original answer was E but we only have 4 options, map E->D
            if original_answer == "E":
                processed_answer = "D"
        else:
            # If we have fewer than 4 options, pad with empty strings
            options = all_options[:4]
            while len(options) < 4:
                options.append("")
        
        return MMLUItem(
            question=self.Question.strip(),
            options=options,
            answer=processed_answer,
            context=self.Context.strip() if self.Context else None,
            subject=self.Subject.strip(),
            level=self.Level.strip(),
            country=self.Country,
            group=self.Group,
            is_few_shot=self.is_few_shot
        )
