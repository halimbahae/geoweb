# GeoWeb — server tests (stdlib HTTP only; no uv/network needed).
# Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>
import http.client
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

TOKEN = "test-token-1234567890"


def _serve(tmp_path: Path, port: int) -> threading.Thread:
    server.Handler.root = tmp_path
    server.Handler.token = TOKEN
    server.Handler.bind_host = "127.0.0.1"
    srv = server.ThreadingHTTPServer(("127.0.0.1", port), server.Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def _free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str, token: str | None = TOKEN, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url)
    if token is not None:
        req.add_header(server.TOKEN_HEADER, token)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def _conn(base: str) -> http.client.HTTPConnection:
    """A raw connection, so a test can set the Host / Origin / Cookie headers itself."""
    host, port = base[len("http://"):].rsplit(":", 1)
    return http.client.HTTPConnection(host, int(port), timeout=20)


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
    assert health["authenticated"] is True
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


# --- authentication ---------------------------------------------------------- #

def test_api_without_token_is_unauthorized(srv):
    base, _ = srv
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{base}/api/sessions", token=None)
    assert e.value.code == 401


def test_api_with_wrong_token_is_unauthorized(srv):
    base, _ = srv
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{base}/api/sessions", token="not-the-token")
    assert e.value.code == 401


def test_health_is_public_but_reveals_nothing(srv):
    base, _ = srv
    health = json.loads(_get(f"{base}/api/health", token=None))
    assert health == {"ok": True, "authenticated": False}
    assert "repo" not in health and "uv" not in health


def test_token_cookie_authenticates_api(srv):
    base, _ = srv
    conn = _conn(base)
    conn.request("GET", "/api/sessions", headers={"Cookie": f"{server.TOKEN_COOKIE}={TOKEN}"})
    resp = conn.getresponse()
    assert resp.status == 200
    assert json.loads(resp.read())["sessions"] == []
    conn.close()


def test_token_url_hands_off_a_strict_cookie(srv):
    base, _ = srv
    conn = _conn(base)
    conn.request("GET", f"/?token={TOKEN}")
    resp = conn.getresponse()
    resp.read()
    assert resp.status == 303
    assert resp.getheader("Location") == "/"
    cookie = resp.getheader("Set-Cookie")
    assert f"{server.TOKEN_COOKIE}={TOKEN}" in cookie
    assert "SameSite=Strict" in cookie and "HttpOnly" in cookie
    conn.close()


def test_token_url_with_bad_token_is_unauthorized(srv):
    base, _ = srv
    conn = _conn(base)
    conn.request("GET", "/?token=nope")
    resp = conn.getresponse()
    resp.read()
    assert resp.status == 401
    assert resp.getheader("Set-Cookie") is None
    conn.close()


def test_api_still_open_when_no_token_configured(srv):
    """An empty token is the explicit opt-out (tests, embedded use)."""
    base, _ = srv
    server.Handler.token = ""
    assert json.loads(_get(f"{base}/api/sessions", token=None))["sessions"] == []


# --- network protection ------------------------------------------------------ #

def test_non_loopback_host_header_is_blocked(srv):
    """Anti DNS-rebinding: a page that resolves evil.example → 127.0.0.1 gets nothing."""
    base, _ = srv
    conn = _conn(base)
    conn.request("GET", "/api/health", headers={"Host": "evil.example"})
    resp = conn.getresponse()
    resp.read()
    assert resp.status == 403
    conn.close()


def test_loopback_host_header_is_allowed(srv):
    base, _ = srv
    conn = _conn(base)
    conn.request("GET", "/api/health", headers={"Host": f"localhost:{base.rsplit(':', 1)[1]}",
                                                server.TOKEN_HEADER: TOKEN})
    resp = conn.getresponse()
    assert resp.status == 200
    resp.read()
    conn.close()


def test_cross_origin_write_is_blocked(srv):
    base, _ = srv
    conn = _conn(base)
    conn.request("POST", "/api/session/whatever/recon", body=b"{}",
                 headers={server.TOKEN_HEADER: TOKEN, "Origin": "https://evil.example",
                          "Content-Type": "application/json"})
    resp = conn.getresponse()
    resp.read()
    assert resp.status == 403
    conn.close()


def test_same_origin_write_reaches_the_router(srv):
    base, _ = srv
    conn = _conn(base)
    conn.request("POST", "/api/session/whatever/recon", body=b"{}",
                 headers={server.TOKEN_HEADER: TOKEN, "Origin": base,
                          "Content-Type": "application/json"})
    resp = conn.getresponse()
    resp.read()
    assert resp.status == 400          # no such session — the guard let it through
    conn.close()


def test_host_allowed_helper():
    assert server.host_allowed("127.0.0.1:8787", "127.0.0.1") is True
    assert server.host_allowed("localhost", "127.0.0.1") is True
    assert server.host_allowed("[::1]:8787", "127.0.0.1") is True
    assert server.host_allowed("evil.example", "127.0.0.1") is False
    assert server.host_allowed("192.168.1.9", "127.0.0.1") is False
    # bound to a real interface: no name to pin down, so anything goes
    assert server.host_allowed("geoweb.lan", "0.0.0.0") is True


def test_token_ok_helper():
    assert server.token_ok("abc", "abc") is True
    assert server.token_ok("abd", "abc") is False
    assert server.token_ok("", "abc") is False
    assert server.token_ok("anything", "") is True     # auth disabled


def test_origin_allowed_helper():
    assert server.origin_allowed("", "127.0.0.1") is True
    assert server.origin_allowed("http://127.0.0.1:8787", "127.0.0.1") is True
    assert server.origin_allowed("https://evil.example", "127.0.0.1") is False


# --- helpers ----------------------------------------------------------------- #

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
