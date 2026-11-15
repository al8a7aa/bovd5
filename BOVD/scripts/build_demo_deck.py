"""
Build the 7-slide English demo deck for the NASA Space Apps project submission.

The submission rules allow a slide demo of at most 7 slides, title and intro slides included.
The long deck (BOVD_Presentation.pptx) stays as the full walkthrough. This one is for the submission form.

Run: python scripts/build_demo_deck.py
Output: deliverables/English/BOVD_Demo_7_slides.pptx
After building, export it to BOVD_Demo_7_slides.pdf (PowerPoint: File → Save As → PDF) so the GitHub link opens in a browser.
"""
from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "deliverables" / "img" / "v2"
OUT = ROOT / "deliverables" / "English" / "BOVD_Demo_7_slides.pptx"
MAX_SLIDES = 7
TEAM = json.loads((ROOT / "config" / "team.json").read_text(encoding="utf-8"))
PLACEHOLDERS = "[" in TEAM["team_name"] or any("[" in m for m in TEAM["members"])

NAVY, CYAN, WHITE = RGBColor(0x0B, 0x1F, 0x3A), RGBColor(0x00, 0xB4, 0xD8), RGBColor(0xFF, 0xFF, 0xFF)
GREEN, AMBER, RED, MUTED = RGBColor(0x2E, 0xCC, 0x71), RGBColor(0xF5, 0xA6, 0x23), RGBColor(0xFF, 0x4D, 0x4F), RGBColor(0x9D, 0xB3, 0xCC)
PURPLE, CARD = RGBColor(0xB3, 0x8B, 0xFF), RGBColor(0x13, 0x2A, 0x4B)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def tb(s, x, y, w, h, text, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, ln in enumerate(text if isinstance(text, list) else [text]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size, r.font.color.rgb, r.font.bold = Pt(size), color, bold
        p.space_after = Pt(6)
    return box


def card(s, x, y, w, h, title, body, accent=CYAN, size=13):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = CARD
    sh.line.color.rgb = accent
    sh.adjustments[0] = 0.08
    tb(s, x + 0.15, y + 0.08, w - 0.3, 0.5, title, 15, accent, True)
    tb(s, x + 0.15, y + 0.55, w - 0.3, h - 0.6, body, size, WHITE)


def pic(s, name, x, y, w=None, h=None):
    f = IMG / name
    if not f.exists():
        raise FileNotFoundError(f)
    p = s.shapes.add_picture(str(f), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    p.line.color.rgb = MUTED
    return p


def slide(title, notes, n):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    if title:
        tb(s, 0.5, 0.3, 12.3, 0.8, title, 28, WHITE, True)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.05), Inches(1.2), Emu(45000))
        bar.fill.solid()
        bar.fill.fore_color.rgb = CYAN
        bar.line.fill.background()
    tb(s, 0.5, 7.0, 12.3, 0.4, f"BÖVD · NASA Space Apps 2026 · prototype for decision support and training, not a medical device · {n}/{MAX_SLIDES}", 10, MUTED)
    s.notes_slide.notes_text_frame.text = notes
    return s


# 1 ─ title and pitch
s = slide("", "One sentence: BÖVD tells an astronaut their health status, why, what to do next and who to contact, with no Earth link needed.", 1)
tb(s, 0.8, 0.9, 11.5, 1.2, "BÖVD", 60, WHITE, True)
tb(s, 0.8, 2.15, 11.7, 1.0, "Explainable, offline health monitoring for astronauts – on the ISS, the Moon, in Mars transit and on Mars", 24, CYAN)
tb(s, 0.8, 3.3, 11.7, 0.9, [f"Team: {TEAM['team_name']}", "Members: " + ", ".join(TEAM["members"])], 17, AMBER, True)
tb(s, 0.8, 4.35, 11.7, 2.0, [
    "Challenge: Create Health Monitoring Software for Astronauts on Space Missions",
    "Every reading gets four answers: status · why · next step · who to contact",
    "Uses real NASA data (OSDR OSD-575, Inspiration4) and NASA health standards",
    "Runs on a laptop with no internet: double-click start.bat"], 17, WHITE)

# 2 ─ the problem
s = slide("The problem: far from Earth, astronauts must check their own health",
          "The NASA Human Research Program groups spaceflight risks into five hazards. On Mars a message to Earth takes 4–24 minutes one way, so the crew can't wait for a doctor. The challenge asks for software that lets astronauts assess their own health.", 2)
for i, (t_, b_) in enumerate([("Radiation", "solar storms and cosmic rays beyond low Earth orbit"),
                              ("Isolation", "sleep, mood and team problems in a small closed crew"),
                              ("Distance", "Mars: 4–24 min one-way delay, no quick help from Earth"),
                              ("Gravity", "0 g → 1/6 g → 3/8 g → 1 g changes heart, bones, eyes"),
                              ("Environment", "closed cabin: CO₂, pressure, noise, microbes")]):
    card(s, 0.5 + i * 2.5, 1.5, 2.35, 2.6, t_, b_, size=14)
tb(s, 0.5, 4.4, 12.3, 1.6, [
    "Earth reference ranges alone are misleading in space: in 0 g fluid shifts toward the head, so an astronaut's 'normal' changes.",
    "Astronauts are not doctors. They need a clear status and a simple next step, not raw numbers."], 17, WHITE)
tb(s, 0.5, 6.25, 12.3, 0.6, "Sources: NASA HRP – Five hazards of human spaceflight; Risks of human spaceflight (2026). CSA – Why do we conduct science experiments in space? (2025).", 11, MUTED)

# 3 ─ the solution
s = slide("Our solution: status, why, next step, who to contact",
          "Walk through the pipeline. A personal baseline comes first, Earth ranges second. The app never diagnoses; it tells the astronaut what to do and whom to call.", 3)
for i, st_ in enumerate(["Measure", "Validate", "Personal baseline", "Thresholds + trends", "Status 0–20", "Why + action", "Escalate"]):
    sh = s.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(0.4 + i * 1.8), Inches(1.4), Inches(1.75), Inches(0.75))
    sh.fill.solid()
    sh.fill.fore_color.rgb = CYAN if i % 2 == 0 else RGBColor(0x00, 0x7A, 0x99)
    sh.line.fill.background()
    sh.text_frame.text = st_
    sh.text_frame.word_wrap = True
    r = sh.text_frame.paragraphs[0].runs[0]
    r.font.size, r.font.bold = Pt(10), True
pic(s, "en_dash.png", 0.5, 2.45, h=4.4)
tb(s, 8.5, 2.5, 4.4, 4.4, [
    "• Compares each value with the astronaut's OWN baseline, adjusted for gravity",
    "• Then NASA and clinical reference ranges, then trends (e.g. 3 short nights → red)",
    "• Green / yellow / red with icons, a 0–20 score and a clickable 3D body",
    "• 'Why' panel: hazard, explanation, actions, who to contact, sources",
    "• Alerts go crew → medical officer → flight surgeon over a delayed link"], 15)

# 4 ─ NASA data
s = slide("NASA data drives the app",
          "OSD-575 from the NASA Open Science Data Repository is loaded on first start as REAL data: serum glucose for the 4 Inspiration4 crew members at 7 time points before and after flight. The loader can import any other OSDR study. Thresholds are tied to NASA-STD-3001 and HRP evidence reports.", 4)
pic(s, "en_real_glucose.png", 0.5, 1.4, h=4.3)
tb(s, 8.4, 1.4, 4.5, 4.6, [
    "REAL: NASA OSDR study OSD-575 (SpaceX Inspiration4) – 28 glucose values, 4 crew, before and after flight",
    "Built-in OSDR loader turns any study's CSV into health records with a REAL badge",
    "Limits from NASA-STD-3001 (600 mSv career radiation, cabin CO₂) and HRP evidence reports",
    "29-entry evidence register; 33 APA references, every value shows its source"], 15)
for i, (t_, b_, col) in enumerate([("REAL", "NASA OSDR data", GREEN), ("SYNTHETIC", "10 labelled test scenarios", PURPLE),
                                   ("USER-ENTERED", "typed by the crew", RGBColor(0x79, 0xC0, 0xFF))]):
    card(s, 0.5 + i * 2.6, 5.9, 2.45, 0.95, t_, b_, col, 12)

# 5 ─ every hazard covered
s = slide("Every hazard has a tool",
          "Show how each of the five hazards maps to a feature. Demo the radiation storm mode and the flight surgeon view if time allows.", 5)
for i, (t_, b_, col) in enumerate([
        ("Radiation", "personal dose vs 600 mSv limit; solar storm alarm, countdown, best shelter zone", PURPLE),
        ("Isolation", "sleep, mood and stress trends; crew harmony; home-connection prompts", AMBER),
        ("Distance", "7 offline Smart Doctor protocols; store-and-forward link with Moon/Mars delay", CYAN),
        ("Gravity", "gravity-aware baseline; landing stand test; eye (SANS) and bone/urine checks", GREEN),
        ("Environment", "cabin CO₂ judged at the real cabin pressure; SpO₂ and temperature checks", RED)]):
    card(s, 0.5 + i * 2.5, 1.4, 2.35, 2.45, t_, b_, col, 12)
pic(s, "en_radiation.png", 0.5, 4.05, h=2.85)
pic(s, "en_surgeon.png", 6.0, 4.05, h=2.85)

# 6 ─ validity and trust
s = slide("Built to be trusted",
          "Be honest about limits: this is a hackathon prototype. Every threshold needs flight-surgeon review, and the voice and blink features are experimental.", 6)
card(s, 0.5, 1.4, 6.0, 2.6, "Works and is tested", [
    "• 140 automated tests pass",
    "• Runs offline on 127.0.0.1; nothing goes to the cloud",
    "• Health data encrypted at rest (AES-256-GCM)",
    "• FHIR R4 records with LOINC codes, as in hospitals"], GREEN, 14)
card(s, 6.8, 1.4, 6.0, 2.6, "Safe by design", [
    "• Never diagnoses: status + next step + who to call",
    "• Consent per feature; raw audio and video never stored",
    "• Five roles; the flight surgeon sees only what arrived",
    "• Tamper-evident black box log"], CYAN, 14)
card(s, 0.5, 4.2, 12.3, 2.5, "Honest limits", [
    "• Some thresholds (heart rate, SpO₂, temperature, glucose) are clinical defaults marked [CITATION NEEDED] for flight-surgeon review",
    "• Real data so far is one NASA study (glucose, a 3-day mission); the other indicators use labelled synthetic data",
    "• Voice and webcam-blink features are experimental research concepts"], AMBER, 14)

# 7 ─ impact and next steps
s = slide("Impact and next steps",
          "Close with impact: the same offline, explainable approach fits Artemis, Mars, Antarctic stations and remote clinics on Earth.", 7)
for i, (t_, b_) in enumerate([("Artemis Moon base", "1.3 s delay, 1/6 g, solar storm shelter"),
                              ("Mars missions", "Earth-independent care with 4–24 min delay"),
                              ("Antarctic stations", "winter isolation, sleep and mood"),
                              ("Remote clinics", "offline, Arabic/English, a low-cost laptop")]):
    card(s, 0.5 + i * 3.1, 1.4, 2.95, 2.0, t_, b_, size=14)
tb(s, 0.5, 3.7, 12.3, 2.0, [
    "Next: flight-surgeon review of every threshold · more OSDR and NASA Life Sciences Portal data · neutron dose input like CSA's CANS spectrometer · usability tests with gloves in an analog mission"], 16)
tb(s, 0.5, 4.9, 12.3, 0.8, ["Try it: double-click start.bat → http://127.0.0.1:8765 · demo users astro1 / cmo1 / surgeon1 · password astra2026"], 16, CYAN, True)
tb(s, 0.5, 5.9, 12.3, 0.9, "AI disclosure: " + TEAM["ai_use"], 11, MUTED)

assert len(prs.slides) <= MAX_SLIDES, f"{len(prs.slides)} slides; the submission limit is {MAX_SLIDES}"
cp = prs.core_properties  # the guide asks for AI use to be stated in metadata too
cp.title = "BÖVD – NASA Space Apps 2026 demo"
cp.author = TEAM["team_name"]
cp.subject = "Create Health Monitoring Software for Astronauts on Space Missions"
cp.keywords = "NASA Space Apps 2026; astronaut health; OSDR OSD-575; AI-assisted"
cp.comments = ("AI disclosure: AI assistants (LLMs such as Claude) helped write code, documents and this deck. "
               "Idea, design, data choice and review by the team. No AI-generated images, audio or video.")  # 255-char limit
prs.save(str(OUT))
print(f"saved {OUT} ({len(prs.slides)} slides)")
if PLACEHOLDERS:
    print("WARNING: config/team.json still has placeholders – fill in the team name and members before uploading.")
