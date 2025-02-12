
import os
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def patch_env():
    with patch(
        "src.kraken_api.load_dotenv",
        lambda *args, **kwargs: None
    ):
        with patch.dict(
            os.environ,
            {"API_KEY": "test_key", "API_SECRET": "test_secret"},
            clear=True
        ):
            yield
