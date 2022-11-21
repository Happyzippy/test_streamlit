from pydantic import BaseModel, Field, root_validator, PrivateAttr
from uuid import uuid4
from typing import Optional, List, Dict, Any
from datetime import datetime
from brevettiai.io import IoTools, io_tools
from brevettiai.platform.datamodel import Tag
from brevettiai.platform.datamodel import backend as platform_backend
from brevettiai.platform.datamodel import PlatformBackend

from brevettiai.platform.datamodel.tag import Tag

DATASET_LOCATIONS = dict(
    annotations=".annotations",
    meta=".meta",
    samples=".samples",
    data="",
)

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

    _io: IoTools = PrivateAttr(default=None)
    _backend: PlatformBackend = PrivateAttr(default=None)
    _uri_offset = PrivateAttr(default=None)

    def __init__(self, io=io_tools, backend=platform_backend, resolve_access_rights: bool = False, **data) -> None:
        super().__init__(**data)

        self._io = io
        self._backend = backend

        if self.bucket is None:
            self.bucket = backend.resource_path(self.id)

        if resolve_access_rights:
            self.resolve_access_rights()

    @root_validator(pre=True, allow_reuse=True)
    def parse_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["tags"] = [Tag(id=x, name="<Unknown>") for x in values.pop("tagIds", tuple())]
        return values

    @property
    def backend(self):
        return self._backend

    @property
    def io(self):
        assert self._io is not None, "Remember to call start_job()"
        return self._io
    def resolve_access_rights(self):
        self.io.resolve_access_rights(path=self.bucket, resource_id=self.id, resource_type="dataset", mode='w')

    def get_location(self, mode, *path):
        """Get path to object, prefixing 'annotations', 'data', 'samples' with . if they are in the first argument """
        location = DATASET_LOCATIONS.get(mode, mode)

        path = (location, *path) if location else path
        return self.io.path.join(self.bucket, *path)
