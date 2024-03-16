from backend.app import app
from typing import Any

class SelfReferentialMeta(type):
    """A metaclass that returns the class itself for any attribute access."""
    def __getattr__(cls, name):
        # Return the class itself for any attribute access
        if name == 'get':
            return app.get
        return cls

class PromptServer(metaclass=SelfReferentialMeta):
    """Your PromptServer class using the SelfReferentialMeta metaclass."""
