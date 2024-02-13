from typing import Any, Dict, List, Union
from dataclasses import dataclass, field
import string
import asyncio
from datetime import datetime
import time
import json
import httpx
from nicegui import app, ui  # type: ignore


class Tab:
    def __init__(self, host=None) -> None:
        self.host: str = host
        self._build()

    def _build(self):
        pass
