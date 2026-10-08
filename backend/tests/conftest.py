import os
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp(prefix="outlier-test-")
os.environ["OUTLIER_DATA_DIR"] = _tmp
os.environ["OUTLIER_RUN_WORKER"] = "false"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

from outlier.config import reset_caches  # noqa: E402
from outlier.db import reset_engine  # noqa: E402

reset_caches()
reset_engine()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from outlier.main import create_app

    app = create_app(run_worker=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def demo(client):
    r = client.post("/api/demo/run")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def tmp_png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def data_dir() -> Path:
    return Path(_tmp)
