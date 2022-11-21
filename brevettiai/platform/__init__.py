"""
Interfaces to Brevetti AI platform and backend features
"""
from .datamodel.platform_backend import backend, PlatformBackend
from .datamodel import Dataset
from .web_api import PlatformAPI

BrevettiAI = PlatformAPI
