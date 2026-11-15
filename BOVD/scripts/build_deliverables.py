"""
Build deliverables A–D into ./deliverables and the project root (python-docx / python-pptx).
Run:  python scripts/build_deliverables.py
Theme: navy #0B1F3A, white, cyan #00B4D8, green/amber/red. APA 7 in-text citations + reference list.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches
from pptx.util import Pt as PPt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import content as C  # noqa: E402

from astra import config  # noqa: E402
from astra.server import ROUTES, VERSION  # noqa: E402

OUT = ROOT / "deliverables"
IMG = OUT / "img"
NAVY, CYAN, WHITE = RGBColor(0x0B, 0x1F, 0x3A), RGBColor(0x00, 0xB4, 0xD8), RGBColor(0xFF, 0xFF, 0xFF)
GREEN, AMBER, RED = RGBColor(0x2E, 0xCC, 0x71), RGBColor(0xF5, 0xA6, 0x23), RGBColor(0xFF, 0x4D, 0x4F)
REFS = config.references()
STD = config.load("standards")["register"]
TODAY = date.today().isoformat()

# APA 7 in-text citations (n.d. items from the same author get a/b/c… suffixes)
INTEXT = {
    "nasa_std_3001_v1": "NASA, 2023a", "nasa_std_3001_v2": "NASA, 2023b", "hrp_hazards": "NASA Human Research Program, n.d.",
    "hrp_oi_2015": "NASA Human Research Program, 2015a", "nasa_cv_risk": "NASA, n.d.-b", "nasa_ensuring_health": "NASA, n.d.-c",
    "nasa_sans_risk": "NASA, n.d.-d", "lee_2020": "Lee et al., 2020", "brunstetter_2023": "Brunstetter, 2023",
    "barger_2014": "Barger et al., 2014", "ochmo_sleep_2023": "NASA Office of the Chief Health and Medical Officer, 2023",
    "hrp_bmed_2015": "NASA Human Research Program, 2015b", "picano_2024": "Picano, 2024", "mishra_2026": "Mishra et al., 2026",
    "hrp_team_2022": "NASA Human Research Program, 2022", "nasa_team_risk_2025": "NASA, 2025", "levin_2023": "Levin et al., 2023",
    "exmc_cdss_2022": "NASA Exploration Medical Capability, 2022", "exmc_eimo_2024": "NASA Exploration Medical Capability, 2024",
    "george_2024": "George et al., 2024", "nasa_artemis_rad": "NASA, n.d.-a", "smith_1999": "Smith et al., 1999",
    "smith_2012": "Smith et al., 2012", "scott_2023": "Scott et al., 2023", "english_2020": "English et al., 2020",
    "vanbaalen_2017": "Van Baalen, 2017", "lsda_2024": "NASA Life Sciences Data Archive, 2024", "osdr": "NASA, n.d.-e", "nlsp": "NASA, n.d.-f",
    "hrp_risks_2026": "NASA Human Research Program, 2026a", "hrp_research_2026": "NASA Human Research Program, 2026b",
    "csa_radiation_2026": "Canadian Space Agency, 2026", "csa_science_2025": "Canadian Space Agency, 2025",
}


def cite(*keys: str) -> str:
    return "(" + "; ".join(INTEXT[k] for k in keys) + ")"


def ref_list() -> list[str]:
    def norm(a: str) -> str:
        return a.replace("National Aeronautics and Space Administration", "NASA")
    items = sorted(((k, v) for k, v in REFS.items() if k != "clinical_default"), key=lambda kv: norm(kv[1]["apa"]).lower())
    return [f"{v['apa']} {v['url']}".strip() for _, v in items]


# ====================================================================== DOCX helpers
def _field(par, instr: str, placeholder: str = "") -> None:
    r = par.add_run()
    for tag, txt in (("begin", None), ("instr", instr), ("separate", None), ("text", placeholder), ("end", None)):
        if tag == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
            r._r.append(el)
        elif tag == "text":
            el = OxmlElement("w:t")
            el.text = txt or ""
            r._r.append(el)
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
            r._r.append(el)


def _shade(cell, hex_: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_)
    tcPr.append(sh)


class Doc:
    def __init__(self, title: str, subtitle: str) -> None:
        self.d = Document()
        self.fig = 0
        self.tab = 0
        st = self.d.styles
        st["Normal"].font.name = "Calibri"
        st["Normal"].font.size = Pt(10.5)
        for lvl, size in ((1, 18), (2, 14), (3, 12)):
            h = st[f"Heading {lvl}"]
            h.font.name = "Calibri"
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = NAVY if lvl != 2 else RGBColor(0x00, 0x7A, 0x99)
            h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        sec = self.d.sections[0]
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.different_first_page_header_footer = True
        hp = sec.header.paragraphs[0]
        hp.text = f"BÖVD · {title} · hackathon prototype – not a medical device"
        hp.runs[0].font.size = Pt(8)
        hp.runs[0].font.color.rgb = RGBColor(0x55, 0x66, 0x77)
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fp.add_run("NASA Space Apps Challenge 2026 · Page ").font.size = Pt(8)
        _field(fp, "PAGE", "1")
        fp.add_run(" of ").font.size = Pt(8)
        _field(fp, "NUMPAGES", "1")
        # update fields (TOC, page numbers) automatically when opened
        s = self.d.settings.element
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        s.append(uf)
        self._cover(title, subtitle)

    def _cover(self, title: str, subtitle: str) -> None:
        t = self.d.add_table(rows=1, cols=1)
        c = t.rows[0].cells[0]
        _shade(c, "0B1F3A")
        p = c.paragraphs[0]
        p.paragraph_format.space_before = Pt(60)
        r = p.add_run("🛰  BÖVD")
        r.font.size, r.font.bold, r.font.color.rgb = Pt(34), True, WHITE
        p2 = c.add_paragraph()
        r = p2.add_run(title)
        r.font.size, r.font.color.rgb = Pt(22), CYAN
        p3 = c.add_paragraph()
        r = p3.add_run(subtitle)
        r.font.size, r.font.color.rgb = Pt(12), WHITE
        p4 = c.add_paragraph()
        p4.paragraph_format.space_after = Pt(60)
        r = p4.add_run(f"NASA Space Apps Challenge 2026 · Create Health Monitoring Software for Astronauts on Space Missions\nVersion {VERSION} · {TODAY}")
        r.font.size, r.font.color.rgb = Pt(10), WHITE
        self.d.add_paragraph()
        box = self.d.add_table(rows=1, cols=1)
        bc = box.rows[0].cells[0]
        _shade(bc, "FFF4E0")
        bp = bc.paragraphs[0]
        rr = bp.add_run("Honesty statement. ")
        rr.bold = True
        bp.add_run(C.HONESTY)
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.h("Table of contents", 1)
        self.toc_par = self.d.add_paragraph()
        self.heads: list[tuple[int, str]] = []
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def h(self, text: str, lvl: int = 1) -> None:
        self.d.add_heading(text, lvl)
        if hasattr(self, "heads") and lvl <= 2:
            self.heads.append((lvl, text))

    def _finish_toc(self) -> None:
        """TOC field whose cached result lists the headings (Word refreshes page numbers on open)."""
        tp = self.toc_par
        def fc(par, kind: str) -> None:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), kind); par.add_run()._r.append(el)
        fc(tp, "begin")
        it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = 'TOC \\o "1-2" \\h \\z \\u'
        tp.add_run()._r.append(it)
        fc(tp, "separate")
        anchor = tp._p
        last = None
        for lvl, text in self.heads:
            np_ = self.d.add_paragraph()
            np_.paragraph_format.left_indent = Cm(0.8 * (lvl - 1))
            np_.paragraph_format.space_after = Pt(1)
            r = np_.add_run(text); r.font.size = Pt(10 if lvl == 1 else 9.5); r.bold = lvl == 1
            anchor.addnext(np_._p); anchor = np_._p; last = np_
        fc(last or tp, "end")

    def p(self, text: str, bold_lead: str | None = None) -> None:
        par = self.d.add_paragraph()
        if bold_lead:
            par.add_run(bold_lead).bold = True
        par.add_run(text)

    def bullets(self, items: list[str]) -> None:
        for it in items:
            self.d.add_paragraph(it, style="List Bullet")

    def code(self, text: str) -> None:
        for line in text.strip("\n").split("\n"):
            par = self.d.add_paragraph()
            par.paragraph_format.space_after = Pt(0)
            r = par.add_run(line)
            r.font.name = "Consolas"
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(0x0B, 0x1F, 0x3A)

    def caption(self, kind: str, text: str) -> None:
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER if kind == "Figure" else WD_ALIGN_PARAGRAPH.LEFT
        r = par.add_run(f"{kind} ")
        r.bold, r.italic = True, False
        if kind == "Figure":
            self.fig += 1
            _field(par, "SEQ Figure \\* ARABIC", str(self.fig))
        else:
            self.tab += 1
            _field(par, "SEQ Table \\* ARABIC", str(self.tab))
        par.add_run(". " + text).italic = True

    def table(self, header: list[str], rows: list[tuple | list], caption: str, widths: list[float] | None = None, font: float = 8.5) -> None:
        self.caption("Table", caption)
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, htxt in enumerate(header):
            c = t.rows[0].cells[i]
            _shade(c, "0B1F3A")
            c.text = ""
            r = c.paragraphs[0].add_run(htxt)
            r.bold, r.font.color.rgb, r.font.size = True, WHITE, Pt(font)
        for k, row in enumerate(rows):
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                r = cells[i].paragraphs[0].add_run(str(v))
                r.font.size = Pt(font)
                sv = str(v)
                if sv in ("Low", "green"):
                    _shade(cells[i], "DFF7E8")
                elif sv in ("Medium", "yellow"):
                    _shade(cells[i], "FFF1D6")
                elif sv in ("High", "red"):
                    _shade(cells[i], "FFE0E0")
                elif k % 2:
                    _shade(cells[i], "F2F7FB")
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        self.d.add_paragraph()

    def image(self, name: str, caption: str, width_cm: float = 15) -> None:
        f = IMG / name
        if f.exists():
            self.d.add_picture(str(f), width=Cm(width_cm))
            self.d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            self.caption("Figure", caption)

    def references(self) -> None:
        self.h("References", 1)
        for r in ref_list():
            par = self.d.add_paragraph(r)
            par.paragraph_format.left_indent = Cm(1.27)
            par.paragraph_format.first_line_indent = Cm(-1.27)
            par.runs[0].font.size = Pt(9.5)

    def save(self, path: Path) -> None:
        self._finish_toc()
        self.d.save(str(path))


# ====================================================================== A. CODE_EXPLAINED
FOLDER_TREE = """BÖVD/
├── start.bat              one-click start (Windows)   · start.sh (macOS/Linux) · docker-compose.yml
├── run_tests.bat          tests + coverage            · reset_data.bat
├── config/                every clinical value lives here (reviewable JSON)
│   ├── thresholds.json    default thresholds + citations + "review needed"
│   ├── gravity_contexts.json   ISS / Moon / Mars transit / Mars surface / rover + GTP
│   ├── cdss_protocols.json     F4 decision trees + approved onboard items
│   ├── features.json      flags, consent categories, coach bounds, menu, habitat zones
│   ├── body_regions.json  body figure texts, five hazards
│   ├── references.json    APA 7 list (PART 7)   · standards.json · project_status.json
├── astra/                 Python package (standard library only)
│   ├── config.py  crypto.py  fhir.py  storage.py  validation.py  engine.py
│   ├── alerts.py  auth.py  consent.py  service.py  synthetic.py  server.py
│   ├── ingest/osdr.py     REAL-data loader (NASA OSDR) + README + mapping example
│   └── features/          cdss · radiation · vision · urine · coach · voice · crew · connection · blackbox
├── web/                   HTML/CSS/JS UI (no build step): index.html app.js features.js voice.js i18n.js sw.js
├── tests/                 pytest: test_core.py test_features.py test_api.py
├── scripts/               coverage_lite.py · build_deliverables.py · content.py
├── data/                  db/ (encrypted SQLite, keys) · raw/ (downloaded datasets) · media/<id>/ (family media)
└── deliverables/          docx · pptx · img/"""

MODULES = [
    ("config.py", "Loads JSON configuration; resolves citation keys to APA strings; unknown keys become [CITATION NEEDED].", "ISO 13485 §4.2.4 document control", "def cite(keys):\n    ...\n    if r is None:\n        out.append({'key': k, 'apa': '[CITATION NEEDED]', 'url': ''})"),
    ("crypto.py", "AES-256-GCM. Uses OpenSSL via 'cryptography' when present; otherwise a pure-Python NIST SP 800-38D implementation (T-table AES + GHASH) verified bit-for-bit against OpenSSL in tests. Tokens are 'v1:' + base64(nonce‖ciphertext‖tag).", "ISO/IEC 27002 §8.24; ISO 27799", "def encrypt(self, plaintext, aad=b''):\n    nonce = os.urandom(12)\n    ct = self._fast.encrypt(nonce, plaintext, aad or None) if self._fast else py_encrypt(...)\n    return 'v1:' + base64.b64encode(nonce + ct).decode()"),
    ("fhir.py", "Builds FHIR R4 Observations: LOINC + internal indicator coding, UCUM valueQuantity, ISO 8601 UTC time, measurement-condition and gravity-context extensions, provenance in meta.tag.", "HL7 FHIR R4, LOINC, UCUM, ISO 8601, ISO 13606", "'meta': {'tag': [{'system': '.../provenance', 'code': prov['type'], 'display': prov['ref']}]},\n'valueQuantity': {'value': value, 'unit': ind['unit'], 'system': 'http://unitsofmeasure.org', 'code': ind['ucum']}"),
    ("storage.py", "SQLite in WAL mode with field-level encryption of all health payloads. The black box table is append-only (triggers) and SHA-256 hash-chained; every write lands there.", "ISO/IEC 27002 §8.15; ISO 14721", "CREATE TRIGGER bb_no_update BEFORE UPDATE ON blackbox\n  BEGIN SELECT RAISE(ABORT, 'black box is append-only'); END;\nh = sha256(prev ‖ ts ‖ actor ‖ category ‖ payload_enc)"),
    ("validation.py", "Plausibility ranges, unit conversion to SI/UCUM, systolic > diastolic, and condition metadata (rule 2) that lowers confidence when incomplete.", "ISO/IEC 25012; ISO 80000; IEC 62366-1 §5.7", "REQUIRED_CONDITIONS = ('time_of_day', 'restrained', 'arm_position', 'rested_5min')"),
    ("engine.py", "Gravity-aware personal baseline (early-flight in 0 g, pre-flight in 1 g/partial g) → Earth thresholds → trend rules → composite 0–20 → WHY panel with hazard, explanation, actions, contact, protocol link and citations.", "IEC 62304 class B; ISO 14971 controls R-01…R-06; ISO/IEC 22989 transparency", "if dev:\n    level = worst(level, 'yellow')\nelif base and e_level == 'yellow' and soften:\n    level = 'green'   # RED is never softened"),
    ("alerts.py", "Three priorities, de-duplication, repeat-until-ack, escalation crew → CMO → flight surgeon, store-and-forward queue with light-time delay in both directions.", "IEC 60601-1-8 §6.1/§6.3; EIMO", "POLICY = {'high': {'repeat_s': 30, 'escalate_s': 120}, 'medium': {...600, 1800}, 'low': {None, None}}"),
    ("auth.py / consent.py", "PBKDF2 passwords, HS256 JWT, 5 roles with least-privilege permissions; consent gate called by every feature before any write.", "ISO/IEC 27002 §5.15, §8.5; ISO/IEC 29100 §5.2", "def require(store, feature, aid, category=None):\n    if not is_enabled(store, feature): raise ConsentError(...)"),
    ("service.py", "Orchestrates the workflow input → validation → assessment → explanation → action → escalation → follow-up; dashboard aggregation; Gravity Transition Protocol and stand test.", "IEC 62304 §5.3", "v = validation.validate(...); a = engine.assess(...); store.add_observation(obs); alerts.raise_alert(store, aid, a)"),
    ("synthetic.py", "Ten scenarios calibrated on published ranges; every value tagged SYNTHETIC(<scenario>).", "ISO 14971 R-15", "fhir.make_observation(aid, ind, v, ts, {'type': 'SYNTHETIC', 'ref': scen}, ...)"),
    ("server.py", "Standard-library HTTP server on 127.0.0.1: REST API (route table → OpenAPI 3), static UI, 5-s background tick, polling endpoint instead of WebSocket.", "ISO/IEC 27002 §8.20", "@route('POST', '/api/readings')\ndef r_readings(c): ..."),
    ("web/*", "Vanilla JS UI: Arabic/English with RTL, high-contrast and glove modes, body SVG, SVG charts with baseline band and gravity markers, measurement wizard, IndexedDB offline outbox, service worker.", "IEC 62366-1; ISO 9241-110/-125; WCAG AA", "const lvl = (l) => `<span class=\"lvl ${l}\">${ICON[l]} ${t('level_' + l)}</span>`;  // colour + icon + text"),
]

MICRO_RULES = [
    ("1 Personal baseline first", "engine.baseline / engine.assess", "z-score vs own early-flight (0 g) or pre-flight baseline, then Earth thresholds"),
    ("2 Fixed measurement conditions", "validation.REQUIRED_CONDITIONS, fhir EXT_CONDITIONS, wizard step 1", "conditions stored with every reading; confidence lowered if missing"),
    ("3 No standing in 0 g", "service.record_stand_test, start_gtp", "stand test only where context allows; landing triggers GTP"),
    ("4 Body mass via mass-measurement device", "indicator body_mass, MICRO.mass", "manual entry; % loss feeds coach"),
    ("5 Sleep vs crew schedule", "DEFAULT_ROUTINE, MICRO.sleep, trend rule", "16 sunrises/day note; consecutive short-night rule"),
    ("6 Exercise vs plan", "features/coach.py", "ARED/treadmill/cycle minutes inside prescription bounds"),
    ("7 Gravity context switch", "config/gravity_contexts.json, alerts.current_delay_s, set_gravity", "changes baseline, tests, delay and advice"),
    ("8 UI for floating users", "web/styles.css (.big, .hc), wizard", "56–72 px targets, any orientation, visual alarms"),
]


def build_code_explained() -> None:
    D = Doc("Code Explained", "Architecture, modules, microgravity rules, features F1–F9, worked examples, API, tests")
    D.h("1. Overview and run guide", 1)
    D.p("BÖVD is an offline-first health decision-support prototype for astronauts. It runs entirely on one computer: "
        "a Python standard-library server (127.0.0.1:8765) serves an HTML/JavaScript interface. No cloud, no hardware, no sensors. "
        "Inputs are keyboard/mouse entry, optional microphone and webcam (processed on-device), file import, NASA open data via a loader, "
        "and a clearly labelled synthetic generator " + cite("osdr", "nasa_std_3001_v1") + ".")
    D.p(" The brief proposed React + FastAPI; at the team's request the delivered build uses plain HTML for the interface and Python for all logic, "
        "launched by a .bat file. The architecture layers are unchanged.", "Implementation choice.")
    D.h("1.1 Run", 2)
    D.bullets(["Windows: install Python 3.10+ (tick 'Add to PATH'), unzip, double-click start.bat. The browser opens automatically.",
               "macOS/Linux: ./start.sh · Docker: docker compose up (published on 127.0.0.1 only).",
               "Demo accounts: astro1, astro3, cmo1, bhs1, surgeon1, research1 – password astra2026 (prototype only).",
               "Optional package 'cryptography' is installed by start.bat if internet is available; otherwise the verified pure-Python AES-256-GCM is used.",
               "Tests: run_tests.bat (pytest + standard-library coverage report). Reset demo data: reset_data.bat."])
    D.h("1.2 Two-minute judge demo", 2)
    D.bullets(C.DEMO_SCRIPT)
    D.image("dashboard.png", "Dashboard: status ring (composite 0–20), interactive body figure, latest readings with provenance badges.")

    D.h("2. Architecture", 1)
    D.p("One module per layer, following the brief: ingest → validation → storage → engine → alerts → api → ui. "
        "Clinical logic (engine), alarm logic (alerts) and orchestration (service) are separated so that each can be verified on its own (IEC 62304 §5.3).")
    D.code("""inputs: keyboard · mic* · webcam* · files · OSDR loader · synthetic
        (* features only – raw media never stored)
   │
   ▼  ingest/ → validation.py
   ▼  fhir.py + storage.py   SQLite WAL · AES-256-GCM · black box
   ▼  engine.py              baseline → Earth range → trends → score → WHY
   ▼  alerts.py              3 priorities · escalation · delay queue
   ▼  server.py              REST + polling · OpenAPI · RBAC
   ▼  web/                   HTML UI · AR/EN · PWA""")
    D.caption("Figure", "Layered architecture (software-only, offline, loopback network).")
    D.h("2.1 Folder tree", 2)
    D.code(FOLDER_TREE)

    D.h("3. Module-by-module walkthrough", 1)
    for name, desc, std, snip in MODULES:
        D.h(name, 2)
        D.p(desc)
        D.p(std, "Standard clauses (alignment): ")
        D.code(snip)

    D.h("4. Microgravity rules and where they are coded", 1)
    D.p("The ~2 L headward fluid shift and the absence of a standing posture change what 'normal' means in flight "
        + cite("hrp_oi_2015", "nasa_cv_risk") + "; astronauts sleep less in flight " + cite("barger_2014") + ".")
    D.table(["Rule", "Where in code", "Behaviour"], C.MICRO_RULES if hasattr(C, "MICRO_RULES") else MICRO_RULES, "Microgravity rules → code.", [4.5, 6, 6.5])

    D.h("5. Data provenance", 1)
    D.p("Every value carries a provenance badge: REAL (dataset ID) | SYNTHETIC (scenario) | USER-ENTERED (user). Synthetic values are never shown as real readings.")
    D.table(["Source", "Status in prototype", "Fields", "Transformation"], [
        ("NASA OSDR " + cite("osdr"), "Loader + mapping implemented; no dataset bundled – download required", "columns chosen in mapping.json", "CSV → validation → FHIR Observation, provenance REAL(OSD-n)"),
        ("NASA Life Sciences Portal " + cite("nlsp"), "Manual download after data request", "as above", "same mapping approach"),
        ("HRP evidence reports", "Used as evidence for thresholds", "—", "citations in config/thresholds.json"),
        ("Synthetic generator", "10 scenarios", "all indicators + features", "SYNTHETIC(<scenario>) tag")], "Data sources and provenance.", [4, 4.5, 3.5, 5])

    D.h("6. Features F1–F9", 1)
    for fid, title, mod, text, cites in C.FEATURES:
        D.h(f"{fid} · {title}", 2)
        D.p(mod, "Module: ")
        D.p(text + f" ({cites}).")
    D.image("vision.png", "F2 Eye of Truth: screen calibration, logMAR chart, Amsler grid, symptoms (Arabic interface, RTL).", 14)
    D.image("radiation.png", "F5 Personal Radiation Map: cumulative dose vs limit and habitat heat map.", 14)

    D.h("7. Rules-engine worked examples", 1)
    D.h("7.1 Mars-landing orthostatic case", 2)
    D.p("Crew member lands on Mars (event 'landing' → mars_surface). The Gravity Transition Protocol starts (fluid loading, compression garment, "
        "seated stand test at +2 h and +24 h). Stand test: seated HR 62, SBP 112; standing HR 98, SBP 98 → HR rise 36 > 30 → YELLOW; if standing SBP < 90 → RED. "
        "WHY: hazard 'Gravity fields', actions 'no unassisted standing/EVA, inform CMO', protocol 'Post-landing dizziness' " + cite("hrp_oi_2015") + ".")
    D.h("7.2 Five-night sleep debt", 2)
    D.p("Early-flight baseline 6.1 ± 0.5 h (0 g). Nights: 5.4, 5.2, 5.0, 4.8. The value 4.8 h is Earth-RED (<5 h) and below the personal band; "
        "three consecutive short nights trigger the trend rule → RED, composite score rises, Insomnia protocol offered with a stop criterion before critical tasks " + cite("barger_2014", "ochmo_sleep_2023") + ".")
    D.h("7.3 Solar particle event shelter", 2)
    D.p("Mars transit background 1.8 mSv/day (synthetic). SPE multiplier ×50 → 90 mSv/day in the lab (shield 1.0) vs 27 mSv/day in the water-wall shelter (0.3). "
        "For a 12-h event the estimated dose saved is (90 − 27) × 0.5 = 31.5 mSv. A HIGH alert is raised for every crew member with countdown and checklist " + cite("george_2024", "nasa_artemis_rad") + ".")
    D.image("measure.png", "Measurement workflow result: status, WHY, next step, who to contact, escalation and follow-up.", 13)

    D.h("8. API", 1)
    rows = [(m, pat.pattern.strip("^$").replace("(?P<", "{").replace(">[^/]+)", "}"), perm or "public", doc[:70]) for m, pat, _, perm, doc in ROUTES]
    D.table(["Method", "Path", "Permission", "Purpose"], rows, "REST API (generated from the route table; OpenAPI at /api/openapi.json).", [1.6, 5.5, 2.8, 7], 7.5)

    D.h("9. Testing", 1)
    D.p("140 automated tests (pytest): unit tests per layer, 33 threshold boundary cases, 10 scenario tests (one per synthetic scenario), hash-chain tamper test, "
        "8 consent-off tests plus a feature-flag-off test proving nothing is stored, RBAC tests, and an AES-GCM equivalence test against OpenSSL. "
        "Coverage (standard-library tracer, scripts/coverage_lite.py): engine + validation + features ≈ 97 %, whole package ≈ 88 %. "
        "Static checks: ruff (incl. flake8-bandit security rules) clean, mypy --strict clean, headless-browser UI run without console errors.")
    D.h("10. How to extend", 1)
    D.bullets(["New indicator: add it to config/thresholds.json (LOINC, UCUM, region, rules, citation) – UI and engine pick it up.",
               "New protocol: add a tree to config/cdss_protocols.json; the lint test enforces stop criteria and approved items.",
               "New hardware (e.g. automated urinalysis): POST the documented JSON schema to /api/urine.",
               "New gravity context: add to config/gravity_contexts.json with g and delay range.",
               "New language: add a dictionary to web/i18n.js and _xx fields in configuration."])
    D.h("11. Arabic–English glossary", 1)
    D.table(["English", "العربية"], C.GLOSSARY, "Glossary.", [7, 9])
    D.references()
    D.save(OUT / "CODE_EXPLAINED.docx")


# ====================================================================== B. ISO alignment
def build_iso() -> None:
    D = Doc("ISO Standards Alignment", "Designed in alignment with – not audited, not certified")
    D.h("1. Disclaimer", 1)
    D.p(C.HONESTY)
    D.h("2. Executive summary", 1)
    D.p(f"BÖVD maps {len(STD)} standards to concrete code locations, tests and evidence. Each entry states the gap that formal certification would still require. "
        "Risk management follows ISO 14971 with 25 identified risks; alarms follow IEC 60601-1-8 principles; data follow HL7 FHIR R4/LOINC/UCUM; "
        "security and privacy controls follow ISO/IEC 27002, ISO 27799 and ISO/IEC 29100. Space-medicine content is cited to NASA-STD-3001 and HRP evidence "
        + cite("nasa_std_3001_v1", "nasa_std_3001_v2", "hrp_hazards") + ".")
    D.h("3. Scope, intended use and not-intended use", 1)
    D.bullets(["Intended use: decision support and training for crew self-monitoring in hackathon/analog settings; explains status, next step and who to contact.",
               "Users: astronaut, crew medical officer, behavioral health specialist, flight surgeon, researcher.",
               "Environments: ISS (0 g), lunar base (1/6 g), Mars transit (0 g), Mars surface (3/8 g), pressurized rover.",
               "Not intended: diagnosis, treatment decisions, prescribing, operational flight use, replacement for flight-surgeon judgement, intracranial pressure measurement."])
    D.h("4. Standards register", 1)
    D.table(["Standard", "Title", "Area", "Clauses", "Where in code", "Evidence"],
            [(s["id"], s["title"], s["area"], s["clauses"], s["where"], s["evidence"]) for s in STD], "Standards register.", [2.4, 3.2, 2, 3.4, 3.2, 2.8], 7)
    D.h("5. Standard-by-standard", 1)
    for s in STD:
        D.h(s["id"], 2)
        D.p(s["title"] + ".", "Title: ")
        D.p(s["clauses"], "Requirement focus: ")
        D.p(f"{s['evidence']} – {s['where']}.", "How applied: ")
        D.p(s["gap"], "Gaps / what certification would need: ")
    D.h("6. IEC 62304 software safety classification", 1)
    D.p("Proposed class B: a software failure could contribute to a hazardous situation leading to non-serious injury (e.g. a missed yellow trend), "
        "while serious-injury pathways are mitigated by external controls – the crew medical officer and flight surgeon remain in the loop, red results always "
        "escalate, and the software never prescribes. Class C would apply if the software were used for autonomous treatment decisions; that is explicitly out of scope.")
    D.h("7. ISO 14971 risk register", 1)
    D.table(["ID", "Hazardous situation", "Harm", "S", "P", "Risk control", "Where", "Verification", "Residual"], C.RISKS,
            "Risk register (S = severity 1–5, P = probability 1–5, before controls).", [1, 3.2, 2, 0.6, 0.6, 3.6, 2.2, 2.6, 1.4], 6.5)
    D.h("8. IEC 62366-1 use scenarios", 1)
    D.table(["ID", "Use scenario", "Design response"], C.USE_SCENARIOS, "Use scenarios including floating and gloved use.", [1.2, 7, 8.5])
    D.h("9. Alarm design (IEC 60601-1-8 style)", 1)
    D.table(["Priority", "Trigger", "Signal", "Repeat until ack", "Escalation", "To ground"], C.ALARMS, "Alarm design table.", [2, 3, 3.6, 2.5, 3, 3])
    D.image("alerts.png", "Alerts view: priority colour, tier, repeats, acknowledge, WHY.", 14)
    D.h("10. Security controls", 1)
    D.table(["Control area", "Implementation", "Reference"], C.SECURITY, "Security and privacy controls.", [3.5, 9, 4])
    D.h("11. AI risk table (ISO/IEC 23894)", 1)
    D.table(["AI component", "Risk", "Mitigation in prototype", "Further validation"], C.AI_RISKS, "AI risks.", [3.2, 4, 5.5, 4])
    D.h("12. Traceability matrix", 1)
    D.table(["Requirement", "Source", "Module", "Test / evidence"], C.TRACE, "Requirement → code → test.", [5, 2, 4.5, 5.5], 7.5)
    D.h("13. SBOM / SOUP", 1)
    D.table(["Component", "Version", "License", "Use"], C.SBOM, "Software bill of materials (see sbom.spdx.json).", [5, 3, 5, 4])
    D.p("SOUP evaluation (IEC 62304 §5.3.3): only the Python standard library and SQLite are required; 'cryptography' is optional and its output is verified against the in-house implementation in tests.")
    D.h("14. Roadmap", 1)
    D.table(["Horizon", "Activities"], C.ROADMAP, "Roadmap toward a certifiable product.", [3, 14])
    D.references()
    D.save(OUT / "ISO_STANDARDS_ALIGNMENT.docx")


# ====================================================================== C. Presentation
P_NAVY, P_CYAN, P_WHITE = PRGB(0x0B, 0x1F, 0x3A), PRGB(0x00, 0xB4, 0xD8), PRGB(0xFF, 0xFF, 0xFF)
P_GREEN, P_AMBER, P_RED, P_MUTED = PRGB(0x2E, 0xCC, 0x71), PRGB(0xF5, 0xA6, 0x23), PRGB(0xFF, 0x4D, 0x4F), PRGB(0x9D, 0xB3, 0xCC)


def build_pptx() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    n = [0]

    def bg(s):
        f = s.background.fill
        f.solid()
        f.fore_color.rgb = P_NAVY

    def tb(s, x, y, w, h, text, size=18, color=P_WHITE, bold=False, align=PP_ALIGN.LEFT):
        box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        lines = text if isinstance(text, list) else [text]
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            r = p.add_run()
            r.text = ln
            r.font.size, r.font.color.rgb, r.font.bold = PPt(size), color, bold
            p.space_after = PPt(6)
        return box

    def card(s, x, y, w, h, title, body, accent=P_CYAN, size=13):
        sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = PRGB(0x13, 0x2A, 0x4B)
        sh.line.color.rgb = accent
        sh.adjustments[0] = 0.08
        tb(s, x + 0.15, y + 0.1, w - 0.3, 0.5, title, 16, accent, True)
        tb(s, x + 0.15, y + 0.6, w - 0.3, h - 0.7, body, size, P_WHITE)

    def slide(title, notes, criteria=""):
        n[0] += 1
        s = prs.slides.add_slide(blank)
        bg(s)
        tb(s, 0.5, 0.3, 10.5, 0.8, title, 30, P_WHITE, True)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.05), Inches(1.2), Emu(45000))
        bar.fill.solid()
        bar.fill.fore_color.rgb = P_CYAN
        bar.line.fill.background()
        if criteria:
            tb(s, 9.6, 0.38, 3.3, 0.5, "Judging: " + criteria, 11, P_MUTED, align=PP_ALIGN.RIGHT)
        tb(s, 0.5, 7.0, 12.3, 0.4, f"BÖVD · NASA Space Apps 2026 · prototype – not a medical device · {n[0]}", 10, P_MUTED)
        s.notes_slide.notes_text_frame.text = notes
        return s

    def pic(s, name, x, y, w=None, h=None):
        f = IMG / name
        if f.exists():
            s.shapes.add_picture(str(f), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)

    # 1 title
    n[0] += 1
    s = prs.slides.add_slide(blank)
    bg(s)
    tb(s, 0.8, 1.6, 11, 1.2, "🛰  BÖVD", 54, P_WHITE, True)
    tb(s, 0.8, 2.9, 11.5, 1, "Explainable, offline health monitoring for astronauts – in microgravity and every gravity field", 24, P_CYAN)
    tb(s, 0.8, 4.2, 11.5, 1.4, ["NASA Space Apps Challenge 2026 · Create Health Monitoring Software for Astronauts on Space Missions",
                                "Software-only · HTML interface + Python engine · runs locally from one .bat file",
                                "Decision support & training prototype – NOT a certified medical device"], 16, P_WHITE)
    s.notes_slide.notes_text_frame.text = "Introduce the team and the one-sentence pitch: BÖVD tells an astronaut their status, why, what to do next and who to contact – with no Earth link required."

    s = slide("Five hazards of human spaceflight", "NASA HRP groups risks into five hazards (NASA Human Research Program, n.d.). Every alert in BÖVD names the hazard it relates to.", "Relevance")
    for i, (t_, b_) in enumerate([("☢️ Radiation", "GCR + solar particle events beyond LEO"), ("🧠 Isolation & confinement", "sleep, mood, team cohesion"),
                                  ("📡 Distance from Earth", "4–24 min Mars delay → Earth-independent care"), ("🪐 Gravity fields", "0 g ↔ 1/6 g ↔ 3/8 g ↔ 1 g transitions"),
                                  ("🏭 Hostile / closed environment", "CO2, closed cabin, limited resources")]):
        card(s, 0.5 + i * 2.5, 1.6, 2.35, 3.2, t_, b_)
    tb(s, 0.5, 5.2, 12, 1, "Source: NASA Human Research Program (n.d.). Five hazards of human spaceflight.", 12, P_MUTED)

    s = slide("Microgravity changes the body", "Explain why Earth thresholds alone are wrong in flight: fluid shift lowers in-flight HR/BP baseline (NASA Human Research Program, 2015a), bone loss raises urinary calcium (Smith et al., 2012), SANS (Lee et al., 2020), sleep deficiency (Barger et al., 2014).", "Validity")
    for i, (t_, b_) in enumerate([("💧 Fluid shift", "≈2 L headward; orthostatic intolerance on return to gravity (HRP, 2015a)"),
                                  ("🦴 Bone & kidney", "calcium leaves bone → urinary calcium ↑, stone risk ↑ (Smith et al., 2012)"),
                                  ("👁️ Eyes – SANS", "optic-disc oedema, globe flattening (Lee et al., 2020)"),
                                  ("😴 Sleep", "~6 h in flight, 16 sunrises/day (Barger et al., 2014)")]):
        card(s, 0.5 + i * 3.1, 1.6, 2.95, 3.4, t_, b_, size=14)
    tb(s, 0.5, 5.4, 12.3, 1, "➡ Rule 1: compare with the astronaut's OWN early-flight baseline first, Earth ranges second.", 20, P_CYAN, True)

    s = slide("Personas", "Five roles with least-privilege access. The isolation signal is visible only to the individual and the behavioral health specialist.", "Impact")
    for i, (t_, b_) in enumerate([("👩‍🚀 Noor – astronaut", "gloved, floating; wants a 60-second check and a clear next step"),
                                  ("🩺 Sami – CMO", "crew doctor onboard; needs alerts, protocols, crew view"),
                                  ("🧠 BHS", "behavioral health specialist; sees mood/isolation signals only"),
                                  ("🌍 Flight surgeon", "on Earth; sees only what arrived over the delayed link"),
                                  ("🔬 Researcher", "pseudonymised, consented export only")]):
        card(s, 0.5 + i * 2.5, 1.6, 2.35, 3.6, t_, b_, size=13)

    s = slide("Solution: status + WHY + next step + who to contact", "Walk through the workflow chain. Emphasise that the app never diagnoses.", "Creativity · Validity")
    steps = ["Input", "Validation", "Assessment", "Explanation", "Action", "Escalation", "Follow-up"]
    for i, st_ in enumerate(steps):
        sh = s.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(0.4 + i * 1.8), Inches(1.7), Inches(1.75), Inches(0.9))
        sh.fill.solid()
        sh.fill.fore_color.rgb = P_CYAN if i % 2 == 0 else PRGB(0x00, 0x7A, 0x99)
        sh.line.fill.background()
        sh.text_frame.text = st_
        sh.text_frame.paragraphs[0].runs[0].font.size = PPt(10.5)
        sh.text_frame.word_wrap = False
        sh.text_frame.paragraphs[0].runs[0].font.bold = True
    pic(s, "measure.png", 0.5, 2.9, h=3.9)
    tb(s, 7.6, 3.0, 5.2, 3.8, ["• Personal baseline ±2 SD (gravity-aware)", "• Earth thresholds (config, cited, review needed)",
                               "• Trend rules: 3 short nights → RED; mood decline", "• Composite score 0–20", "• WHY: hazard, explanation, actions, contact, APA sources"], 16)

    s = slide("Live demo flow (2 minutes)", "Follow README demo script. Have start.bat already running.", "Presentation")
    tb(s, 0.5, 1.5, 6.3, 5.3, [f"{i + 1}. {x}" for i, x in enumerate(C.DEMO_SCRIPT)], 14)
    pic(s, "dashboard.png", 7.0, 1.4, w=5.8)

    for part, rng in ((1, C.FEATURES[:5]), (2, C.FEATURES[5:])):
        s = slide(f"Nine advanced features ({part}/2)", "Each feature has its own module, feature flag, consent screen, privacy note, explainer, citations and tests.", "Creativity · Impact")
        for i, (fid, title, _, text, _) in enumerate(rng):
            card(s, 0.5 + (i % 3) * 4.15, 1.5 + (i // 3) * 2.75, 4.0, 2.6, f"{fid} {title}", text[:210] + ("…" if len(text) > 210 else ""), size=11)

    s = slide("Architecture – software-only, offline", "Python standard library only; optional OpenSSL crypto. Binds to 127.0.0.1. Encrypted SQLite. One-command start.", "Validity")
    for i, (t_, b_) in enumerate([("web/ (HTML UI)", "AR/EN RTL · PWA · glove mode · body map · charts"), ("server.py", "REST + polling · OpenAPI · JWT + RBAC"),
                                  ("engine · alerts", "baseline → thresholds → trends → WHY · 3 priorities · delay queue"),
                                  ("storage", "SQLite WAL · AES-256-GCM · FHIR R4 · hash-chained black box"), ("ingest · synthetic", "NASA OSDR loader · 10 scenarios")]):
        card(s, 0.5, 1.4 + i * 1.08, 7.2, 0.98, t_, b_, size=12)
    tb(s, 8.2, 1.5, 4.7, 5, ["▶ start.bat", "  → finds Python", "  → optional pip cryptography", "  → python -m astra.server", "  → opens http://127.0.0.1:8765", "",
                             "No cloud · no sensors · no Arduino", "Mic/webcam: features computed in the browser, raw media discarded"], 15, P_CYAN)

    s = slide("NASA data + provenance", "Never invent data: REAL only after downloading an OSDR dataset with the loader; synthetic always labelled.", "Validity · Relevance")
    for i, (t_, b_, col) in enumerate([("REAL", "NASA OSDR / NLSP via loader + mapping → provenance REAL(OSD-n)", P_GREEN),
                                       ("SYNTHETIC", "10 scenarios calibrated on published ranges → SYNTHETIC(scenario)", PRGB(0xD2, 0xA8, 0xFF)),
                                       ("USER-ENTERED", "typed by crew with measurement conditions", PRGB(0x79, 0xC0, 0xFF))]):
        card(s, 0.5 + i * 4.15, 1.6, 4.0, 2.0, t_, b_, col, 14)
    pic(s, "chart.png", 0.5, 3.8, h=3.0)
    tb(s, 7.0, 4.0, 5.8, 2.8, ["Every point coloured by provenance", "Baseline band + gravity-transition markers", "Scenario tests assert SYNTHETIC tag on every value"], 15)

    s = slide("Explainable assessment", "Show the WHY panel: what rule fired, against which baseline, which hazard, what to do, whom to call, sources.", "Validity")
    pic(s, "dashboard.png", 0.5, 1.4, h=5.4)
    tb(s, 6.4, 1.6, 6.4, 5, ["Baseline first (rule 1)", "RED is never softened", "Confidence lowered if conditions incomplete",
                             "Every threshold: citation + 'review needed'", "Body figure: colour + icon + label (never colour alone)"], 17)

    s = slide("Alerts & Earth–Mars delay", "IEC 60601-1-8 style priorities. Mars delay 4–24 min one way; ground acks travel back with delay.", "Relevance · Impact")
    for i, (pr, tr, sig, rep, esc_, gr) in enumerate(C.ALARMS):
        card(s, 0.5 + i * 4.15, 1.5, 4.0, 2.2, pr, [tr, sig, f"repeat: {rep}", f"escalate: {esc_}"], [P_RED, P_AMBER, P_CYAN][i], 12)
    pic(s, "surgeon.png", 0.5, 3.9, h=2.9)
    tb(s, 5.4, 4.0, 7.4, 2.8, ["Moon ≈ 1.3 s · Mars 4–24 min (one way)", "Store-and-forward queue in both directions", "Crew → CMO → flight surgeon",
                               "Onboard protocols keep working with no link (EIMO)"], 16)

    s = slide("Privacy & ethics of voice and webcam", "Raw audio/video never stored or sent; consent per category; consent-off tests prove no collection; neutral wording.", "Impact · Validity")
    for i, (t_, b_) in enumerate([("🎙️ Voice (EXPERIMENTAL)", "7 prosodic numbers only; raw audio discarded in the browser; never alerts alone; no labels"),
                                  ("📷 Webcam (EXPERIMENTAL)", "blink numbers only; separate consent, default OFF"),
                                  ("🤝 Crew", "who/minutes only – never content; isolation signal visible to self + BHS"),
                                  ("📦 Research", "consented, pseudonymised, dates generalised, OAIS package")]):
        card(s, 0.5 + (i % 2) * 6.2, 1.5 + (i // 2) * 2.6, 6.0, 2.4, t_, b_, size=15)

    s = slide("Standards (designed in alignment with – not certified)", f"{len(STD)} standards mapped to code, tests and gaps – see ISO_STANDARDS_ALIGNMENT.docx.", "Validity")
    groups = {}
    for st_ in STD:
        groups.setdefault(st_["area"], []).append(st_["id"])
    for i, (area, ids) in enumerate(groups.items()):
        card(s, 0.5 + (i % 4) * 3.1, 1.5 + (i // 4) * 2.7, 2.95, 2.5, area, " · ".join(ids), size=11)

    s = slide("Impact beyond the ISS", "Same software model fits any remote, delayed-care setting.", "Impact")
    for i, (t_, b_) in enumerate([("🌕 Artemis lunar base", "1.3 s delay, partial gravity, SPE shelter"), ("🔴 Mars", "Earth-independent care, 4–24 min delay"),
                                  ("🧊 Antarctica", "winter-over isolation, sleep and mood"), ("🏥 Remote clinics", "offline, Arabic/English, low-cost laptop")]):
        card(s, 0.5 + i * 3.1, 1.7, 2.95, 3.2, t_, b_, size=15)

    s = slide("Done / partial / next", "Be honest about limits – this is a hackathon prototype.", "Presentation")
    stt = config.load("project_status")
    for i, (k, col) in enumerate((("done", P_GREEN), ("partial", P_AMBER), ("next", P_CYAN))):
        card(s, 0.5 + i * 4.15, 1.5, 4.0, 5.3, k.upper(), ["• " + x for x in stt[k]], col, 11)

    s = slide("References (APA 7) – selection", "Full list in SOURCES.md and the Science & Sources page.", "Validity")
    sel = ["hrp_hazards", "nasa_std_3001_v1", "hrp_oi_2015", "lee_2020", "barger_2014", "smith_2012", "george_2024", "exmc_cdss_2022", "mishra_2026", "lsda_2024"]
    tb(s, 0.5, 1.4, 12.3, 5.5, [REFS[k]["apa"] + " " + REFS[k]["url"] for k in sel], 10)

    n[0] += 1
    s = prs.slides.add_slide(blank)
    bg(s)
    tb(s, 0.8, 2.4, 11.5, 1.2, "Thank you", 54, P_WHITE, True, PP_ALIGN.CENTER)
    tb(s, 0.8, 3.7, 11.5, 1, "BÖVD – status · why · next step · who to contact", 22, P_CYAN, align=PP_ALIGN.CENTER)
    tb(s, 0.8, 4.6, 11.5, 1, "Double-click start.bat · http://127.0.0.1:8765 · demo password astra2026", 16, P_WHITE, align=PP_ALIGN.CENTER)
    s.notes_slide.notes_text_frame.text = "Invite questions; offer the live demo."
    prs.save(str(OUT / "BOVD_Presentation.pptx"))


# ====================================================================== D. Markdown + SBOM
def md_table(h: list[str], rows) -> str:
    out = "| " + " | ".join(h) + " |\n|" + "---|" * len(h) + "\n"
    for r in rows:
        out += "| " + " | ".join(str(x).replace("|", "/") for x in r) + " |\n"
    return out


def build_md() -> None:
    (ROOT / "README.md").write_text(f"""# 🛰️ BÖVD

**NASA Space Apps Challenge 2026 – Create Health Monitoring Software for Astronauts on Space Missions**

> {C.HONESTY}

Offline-first, explainable health decision support for astronauts in 0 g, on the Moon (1/6 g), in Mars transit and on Mars (3/8 g).
Interface: **HTML/JavaScript** · Logic: **Python (standard library only)** · Start: **`start.bat`** · Data stays on `127.0.0.1`.

## Quick start (Windows)
1. Install Python 3.10 or newer from python.org and tick **Add python.exe to PATH**.
2. Unzip the folder and double-click **`start.bat`**.
3. The browser opens `http://127.0.0.1:8765`. Log in with a demo account (password `astra2026`).
4. To stop, close the command window. Reset the demo data with `reset_data.bat`; run the tests with `run_tests.bat`.

macOS/Linux: `./start.sh` · Docker: `docker compose up`

| User | Role |
|---|---|
| astro1 / astro3 | astronaut |
| cmo1 | crew medical officer |
| bhs1 | behavioral health specialist |
| surgeon1 | ground flight surgeon |
| research1 | researcher (pseudonymised export only) |

## 2-minute judge demo
""" + "\n".join(f"{i + 1}. {x}" for i, x in enumerate(C.DEMO_SCRIPT)) + """

## What is inside
- Core: validation → personal baseline (gravity-aware) → thresholds → trends → composite 0–20 → WHY → alerts (3 priorities, escalation, Moon/Mars delay).
- F1 Voice (EXPERIMENTAL) · F2 Eye of Truth · F3 Crew Harmony · F4 Smart Doctor · F5 Radiation Map · F6 Urine analytics · F7 Coach · F8 Smart Nostalgia · F9 Black Box · F10 camera posture check · F11 NASA-grounded AI research assistant (EXPERIMENTAL, online, opt-in: a free OpenRouter model answers only from the bundled NASA/CSA sources and cites them).
- Encryption at rest (AES-256-GCM), FHIR R4 + LOINC + UCUM, provenance badges, Arabic/English RTL, glove & high-contrast modes.
- Version 2 (November 2026): new visual identity, animated intro, 3D body with how-to animations for each check, camera posture check (OpenCV + MediaPipe, with a manual mode), 29-entry evidence register, environment simulation, 11-step guided tour, responsive layout. The camera checks posture only; it never measures vital signs.

## NASA data
- **REAL:** NASA Open Science Data Repository study **OSD-575** (SpaceX Inspiration4): serum glucose for 4 crew members at 7 time points before and after flight, loaded on first start with a REAL badge. See `data/real/OSD-575/README.md`.
- The built-in OSDR loader imports any other OSDR study (`astra/ingest/README.md`).
- Everything else in the demo crew is clearly labelled SYNTHETIC.

## Documents (English)
- Submission: `deliverables/English/BOVD_Demo_7_slides.pdf` and `.pptx` (7-slide demo) · `deliverables/English/BOVD_Full_Presentation.pdf` (full 16-slide presentation) · `deliverables/English/SUBMISSION_FORM.md` (draft text for every form field) · `deliverables/English/SUBMISSION_REFERENCES.md` (text for the References field)
- Full deck and reports: `deliverables/English/BOVD_Presentation.pptx` · `deliverables/English/CODE_EXPLAINED.docx` · `deliverables/English/ISO_STANDARDS_ALIGNMENT.docx`
- `deliverables/English/`: `SOURCES.md` · `RISK_REGISTER.md` · `TRACEABILITY.md` · `PROJECT_STATUS.md` · `PRIVACY.md` · `CODE_EXPLAINED.md` · `sbom.spdx.json`
- Arabic versions: `README_AR.md` and the files in `deliverables/` and the project root.

## Use of AI tools
AI assistants (large language models such as Claude) helped write parts of the code, the documents, the translations and the 7-slide demo deck. The idea, the design decisions, the choice of data and the review of all output were the team's own work. No AI-generated images, audio or video are used; all screenshots are of the running app. Git commits made with an AI assistant carry a `Co-Authored-By` line naming it.

## Quality
140 pytest tests · coverage (stdlib tracer) engine+validation+features ≈ 97 % · ruff clean · mypy --strict clean.
""", encoding="utf-8")
    src = "# SOURCES (APA 7)\n\nVerify each link opens before submission. No reference has been invented; unknown items would be marked [CITATION NEEDED].\n\n"
    src += "\n".join(f"- {r}" for r in ref_list())
    src += "\n\n## Datasets\n" + md_table(["Source", "ID", "URL", "License", "Fields", "Transformation"], [
        ('NASA OSDR – SpaceX Inspiration4 serum metabolic panel (bundled)', 'OSD-575', 'https://osdr.nasa.gov/bio/repo/data/studies/OSD-575', 'NASA open data – “Data are courtesy of the NASA Open Science Data Repository”; study: Overbey, E. G., et al. (2024). The Space Omics and Medical Atlas (SOMA) and international astronaut biobank. Nature. https://doi.org/10.1038/s41586-024-07639-y', 'glucose_value_milligram_per_deciliter from LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv; 4 crew × 7 time points = 28 values', 'scripts/build_osd575.py: day labels L-n / R+n → dates from launch 2021-09-16 and return 2021-09-18 (12:00 UTC, sampling time not in source); L- samples → earth_preflight, R+ samples → earth_postflight; CSV → FHIR Observation (LOINC 2339-0, mg/dL), REAL(OSD-575)'),
        ('NASA OSDR (any other study)', 'chosen OSD-n', 'https://osdr.nasa.gov', 'NASA open data + study citation', 'per mapping.json', 'CSV → FHIR Observation, REAL(OSD-n)'),
        ("NASA Life Sciences Portal", "after data request", "https://nlsp.nasa.gov", "per agreement", "per mapping.json", "same"),
        ("Synthetic generator", "10 scenarios", "astra/synthetic.py", "project", "all indicators", "SYNTHETIC(scenario)")])
    (ROOT / "SOURCES.md").write_text(src, encoding="utf-8")
    (ROOT / "RISK_REGISTER.md").write_text("# RISK REGISTER (ISO 14971 style)\n\nS = severity 1–5, P = probability 1–5 before controls.\n\n"
                                           + md_table(["ID", "Hazardous situation", "Harm", "S", "P", "Control", "Where", "Verification", "Residual"], C.RISKS)
                                           + "\n## AI risks (ISO/IEC 23894)\n" + md_table(["Component", "Risk", "Mitigation", "Further validation"], C.AI_RISKS), encoding="utf-8")
    (ROOT / "TRACEABILITY.md").write_text("# TRACEABILITY\n\n" + md_table(["Requirement", "Source", "Module", "Test / evidence"], C.TRACE), encoding="utf-8")
    stt = config.load("project_status")
    (ROOT / "PROJECT_STATUS.md").write_text("# PROJECT STATUS\n\n" + "".join(f"## {k.title()}\n" + "\n".join(f"- {x}" for x in stt[k]) + "\n\n" for k in ("done", "partial", "next")), encoding="utf-8")
    (ROOT / "PRIVACY.md").write_text(f"""# PRIVACY

{C.HONESTY}

- **Local only.** The server binds to 127.0.0.1; health data is never sent to any cloud service. Network calls happen only on explicit action: the optional OSDR download, and the optional F11 AI research assistant.
- **F11 AI research assistant (EXPERIMENTAL, opt-in).** Off until a flight surgeon adds an OpenRouter API key and, for astronauts, until the 'ai_assistant' consent is granted. It sends only the typed question and excerpts of the bundled NASA/CSA sources to OpenRouter (https://openrouter.ai) – never readings, names or astronaut IDs. The key is stored encrypted and never sent to the browser or the black box; the black box records only which sources were used, not the question.
- **Encryption at rest.** All health payloads are AES-256-GCM encrypted in SQLite; the key is in `data/db/astra.key` (an HSM in a real system).
- **Consent per category** (voice features, vision, webcam blink, crew interaction, radiation, urine, connection, research export). Withdrawing consent or disabling a feature stops collection – proven by automated consent-off tests.
- **Minimisation.** Voice: raw audio never stored or sent (7 numbers only). Webcam: blink numbers only, default OFF. Crew: who/minutes only, never content. Nostalgia: only "helped / didn't help".
- **Visibility.** Isolation signal: the individual and the behavioral health specialist only. Researchers: pseudonymised export only.
- **Integrity.** Every write is in an append-only SHA-256 hash chain (black box) with a tamper-check tool.
- **Demo accounts** use a shared password (`astra2026`) for the hackathon only; change or remove them before any other use.
- **Rights.** Delete local data with `reset_data.bat`. Research exports are generated only on request by authorised roles.
""", encoding="utf-8")
    md = ["# CODE EXPLAINED (Markdown edition)", "", C.HONESTY, "", "## Folder tree", "```", FOLDER_TREE, "```", "## Modules"]
    for name, desc, std, snip in MODULES:
        md += [f"### {name}", desc, f"*Standards (alignment):* {std}", "```python", snip, "```"]
    md += ["## Microgravity rules", md_table(["Rule", "Where", "Behaviour"], MICRO_RULES), "## Features"]
    for fid, title, mod, text, cites in C.FEATURES:
        md += [f"### {fid} · {title}", f"`{mod}` – {text} ({cites})."]
    md += ["## API", md_table(["Method", "Path", "Permission", "Purpose"], [(m, p.pattern.strip("^$"), perm or "public", doc) for m, p, _, perm, doc in ROUTES]),
           "## Glossary", md_table(["English", "العربية"], C.GLOSSARY), "## References", *[f"- {r}" for r in ref_list()]]
    (OUT / "CODE_EXPLAINED.md").write_text("\n".join(md), encoding="utf-8")
    pk = [{"SPDXID": f"SPDXRef-Package-{i}", "name": n_, "versionInfo": v, "licenseConcluded": lic.split(" (")[0], "licenseDeclared": lic.split(" (")[0],
           "downloadLocation": "NOASSERTION", "supplier": "NOASSERTION", "comment": use} for i, (n_, v, lic, use) in enumerate(C.SBOM)]
    sbom = {"spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT", "name": "BÖVD-SBOM",
            "documentNamespace": f"https://bovd.local/spdx/{uuid.uuid4()}",
            "creationInfo": {"created": TODAY + "T00:00:00Z", "creators": ["Tool: scripts/build_deliverables.py"]},
            "packages": pk, "relationships": [{"spdxElementId": "SPDXRef-Package-0", "relationshipType": "DEPENDS_ON", "relatedSpdxElement": f"SPDXRef-Package-{i}"} for i in range(1, len(pk))]}
    (ROOT / "sbom.spdx.json").write_text(json.dumps(sbom, indent=2), encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    build_md()
    build_code_explained()
    build_iso()
    build_pptx()
    print("deliverables built")
