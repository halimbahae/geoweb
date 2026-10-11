# GeoWeb — server tests (stdlib HTTP only; no uv/network needed).
# Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
APP_PY = REPO / "web" / "app.py"

spec = importlib.util.spec_from_file_location("geoweb_server", APP_PY)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


def _serve(tmp_path: Path, port: int) -> threading.Thread:
    srv = server.ThreadingHTTPServer(("127.0.0.1", port), server.Handler)
    server.Handler.root = tmp_path
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def _free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as r:
        return r.read()


@pytest.fixture()
def srv(tmp_path: Path):
    s = _serve(tmp_path, _free_port())
    yield f"http://127.0.0.1:{s.server_address[1]}", tmp_path
    s.shutdown()
    s.server_close()


def test_health_and_index(srv):
    base, _ = srv
    health = json.loads(_get(f"{base}/api/health"))
    assert health["ok"] is True
    index = _get(f"{base}/").decode()
    assert "<title>GeoWeb</title>" in index
    css = _get(f"{base}/static/styles.css").decode()
    assert ":root" in css


def test_list_sessions_empty_then_with_folder(srv):
    base, root = srv
    assert json.loads(_get(f"{base}/api/sessions"))["sessions"] == []
    sess = root / "2026-01-01_00-00-00+0000"
    (sess / "original").mkdir(parents=True)
    (sess / "session.json").write_text(json.dumps({
        "kind": "photo", "status": "pending", "started_at": "2026-01-01T00:00:00.000000+00:00",
        "original": {"relative_path": "original/x.jpg"},
    }))
    (sess / "original" / "x.jpg").write_bytes(b"fakejpeg")
    sessions = json.loads(_get(f"{base}/api/sessions"))["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["kind"] == "photo"
    assert sessions[0]["status"] == "pending"


def test_path_traversal_blocked(srv):
    base, root = srv
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{base}/static/../app.py")
    assert e.value.code in (403, 404)
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{base}/static/%2e%2e/app.py")
    assert e.value.code in (403, 404)


def test_list_sessions_helper_is_sorted_newest_first(tmp_path: Path):
    for i, name in enumerate(["2026-01-01_00-00-00+0000", "2026-02-01_00-00-00+0000"]):
        folder = tmp_path / name
        (folder).mkdir()
        (folder / "session.json").write_text(json.dumps({"kind": "photo", "status": "done",
                                                         "started_at": f"2026-0{i + 1}-01T00:00:00.000000+00:00"}))
    names = [s["name"] for s in server.list_sessions(tmp_path)]
    assert names == ["2026-02-01_00-00-00+0000", "2026-01-01_00-00-00+0000"]


def test_session_name_validation():
    with pytest.raises(ValueError):
        server.session_folder(Path("/tmp/nonexistent-root"), "../escape")
    with pytest.raises(ValueError):
        server.session_folder(Path("/tmp/nonexistent-root"), "bad/name")