# models/notify_request.py
from pydantic import BaseModel, Field
from typing import List

class NotifyRequest(BaseModel):
    tx_hash: str = Field(..., regex="^0x[a-fA-F0-9]{64}$")
    from_account: List[str] = Field(..., min_items=1)
    amounts: List[str]
