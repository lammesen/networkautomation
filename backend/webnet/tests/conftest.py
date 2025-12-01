import os
import pytest
from cryptography.fernet import Fernet


# Enable DEBUG mode for tests before Django settings load
os.environ.setdefault("DEBUG", "true")


@pytest.fixture(autouse=True)
def set_encryption_key(settings):
    """Ensure ENCRYPTION_KEY is set for tests using Credential encryption."""
    key = Fernet.generate_key().decode()
    settings.ENCRYPTION_KEY = key
    os.environ["ENCRYPTION_KEY"] = key
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
