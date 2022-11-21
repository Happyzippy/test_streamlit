from pydantic import BaseModel, Field
from uuid import uuid4
from typing import Optional, List
from datetime import datetime

from brevettiai.platform.datamodel.tag import Tag


class Dataset(BaseModel):
    """
    Model defining a dataset on the Brevetti platform
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    bucket: Optional[str]
    name: str
    created: datetime = Field(default=datetime.utcnow())
    locked: bool = False
    reference: Optional[str] = ""
    notes: Optional[str] = ""
    tags: List[Tag] = Field(default_factory=list, description="tags on dataset")
