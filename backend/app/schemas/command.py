from pydantic import BaseModel
from typing import List, Optional, Dict

class CommandRun(BaseModel):
    targets: Dict
    commands: List[str]
    timeout_sec: Optional[int] = 60
