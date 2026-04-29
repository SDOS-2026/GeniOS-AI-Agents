from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class ScoredItem(BaseModel):
    """
    Validation schema for a single prioritized item from Gemini.
    """
    id: str = Field(..., description="The unique tool-specific ID of the item")
    score: float = Field(..., ge=0, le=100, description="Priority score from 0 to 100")
    category: str = Field(..., description="Semantic category of the item")
    reasons: List[str] = Field(default_factory=list, description="Reasoning for the score")

class BatchScoredResponse(BaseModel):
    """
    Validation schema for a batch of prioritized items.
    """
    items: List[ScoredItem]

class EmailBrief(BaseModel):
    """
    Validation schema for a single email brief.
    """
    brief: str = Field(..., description="Short one-line summary")
    reasoning: List[str] = Field(..., description="1-2 short reasons for attention")
