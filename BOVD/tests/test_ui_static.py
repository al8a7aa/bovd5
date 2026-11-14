"""Static UI integrity: every interactive element has a real handler (no dead buttons), assets exist,
no inline scripts (CSP), every view in the navigation is implemented, every evidence id used by the UI exists."""
import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
JS = {p.name: p.read_text(encoding="utf-8") for p in WEB.glob("*.js")}
ALL = "\n".join(JS.values())


def test_every_data_act_has_a_handler():
    used = set(re.findall(r'data-act="([A-Za-z0-9_]+)"', ALL)) | set(re.findall(r"data-act=\\?\"([A-Za-z0-9_]+)", ALL))
    defined = set(re.findall(r"ACTIONS\.([A-Za-z0-9_]+)\s*=", ALL))
    missing = sorted(used - defined)
    assert not missing, f"buttons without handlers: {missing}"


def test_every_nav_view_is_implemented():
    nav = re.search(r"const NAV = \{(.*?)\n\};", JS["app.js"], re.S).group(1)
    views = set(re.findall(r'"([a-z0-9_]+)"', nav)) - {"astronaut", "cmo", "bhs", "flight_surgeon", "researcher"}
    defined = set(re.findall(r"VIEWS\.([a-z0-9_]+)\s*=", ALL))
    assert views <= defined, views - defined


def test_no_inline_scripts_or_handlers():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html)
    assert not re.search(r"\son[a-z]+=", html)


def test_scripts_and_sw_assets_exist():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for src in re.findall(r'<script src="([^"]+)"', html):
        assert (WEB / src).exists(), src
    sw = JS["sw.js"]
    for a in re.findall(r'"/([a-z0-9_.]+)"', sw):
        assert (WEB / a).exists(), a


def test_ui_evidence_ids_exist():
    ids = {e["id"] for e in json.loads((WEB.parent / "config" / "evidence.json").read_text(encoding="utf-8"))["entries"]}
    used = set(re.findall(r'"(E-[A-Z0-9]+-\d\d)"', ALL))
    assert used and used <= ids, used - ids


def test_camera_never_claims_vitals():
    txt = JS["pose.js"]
    assert "لا تقيس" in txt and "does NOT measure" in txt
