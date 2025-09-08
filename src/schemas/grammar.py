from pydantic import BaseModel

 
class GrammarItem(BaseModel):
    input: str
    correction: str
    explanation: str 