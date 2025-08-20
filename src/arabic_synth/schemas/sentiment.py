from pydantic import BaseModel, field_validator


class SentimentItem(BaseModel):
    text: str
    sentiment: str

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str):
        v_norm = v.lower().strip()
        if v_norm not in {"positive", "negative", "neutral"}:
            raise ValueError("sentiment must be positive|negative|neutral")
        return v_norm 