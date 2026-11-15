"""
Build the FULL English presentation for the local event (every part of BÖVD, following the team script).

The official Space Apps demo stays the 7-slide deck (scripts/build_demo_deck.py) because longer demos are
not eligible for global judging. This deck is for presenting live and for judges who want the whole story.

Run: python scripts/build_full_deck.py
Output: deliverables/English/BOVD_Full_Presentation.pptx  (export to PDF with PowerPoint: File → Save As → PDF)
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "deliverables" / "img" / "v2"
OUT = ROOT / "deliverables" / "English" / "BOVD_Full_Presentation.pptx"
TEAM = json.loads((ROOT / "config" / "team.json").read_text(encoding="utf-8"))

NAVY, CYAN, WHITE = RGBColor(0x0B, 0x1F, 0x3A), RGBColor(0x00, 0xB4, 0xD8), RGBColor(0xFF, 0xFF, 0xFF)
GREEN, AMBER, RED, MUTED = RGBColor(0x2E, 0xCC, 0x71), RGBColor(0xF5, 0xA6, 0x23), RGBColor(0xFF, 0x4D, 0x4F), RGBColor(0x9D, 0xB3, 0xCC)
PURPLE, CARD, ICE = RGBColor(0xB3, 0x8B, 0xFF), RGBColor(0x13, 0x2A, 0x4B), RGBColor(0xE6, 0xF4, 0xFA)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
SLIDES: list[str] = []


def tb(s, x, y, w, h, text, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT, space=6):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, ln in enumerate(text if isinstance(text, list) else [text]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size, r.font.color.rgb, r.font.bold = Pt(size), color, bold
        p.space_after = Pt(space)
    return box


def card(s, x, y, w, h, title, body, accent=CYAN, size=13, tsize=15):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = CARD
    sh.line.color.rgb = accent
    sh.adjustments[0] = 0.07
    tb(s, x + 0.15, y + 0.08, w - 0.3, 0.5, title, tsize, accent, True)
    tb(s, x + 0.15, y + 0.55, w - 0.3, h - 0.6, body, size, WHITE, space=3)


def pic(s, name, x, y, maxw, maxh):
    """Place an image inside a box, keeping its aspect ratio, centred."""
    f = IMG / name
    w, h = Image.open(f).size
    scale = min(maxw / w, maxh / h)
    pw, ph = w * scale, h * scale
    p = s.shapes.add_picture(str(f), Inches(x + (maxw - pw) / 2), Inches(y + (maxh - ph) / 2), Inches(pw), Inches(ph))
    p.line.color.rgb = MUTED
    return p


def slide(title, notes, kicker=""):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    if kicker:
        tb(s, 0.5, 0.22, 12.3, 0.4, kicker.upper(), 12, AMBER, True)
    if title:
        tb(s, 0.5, 0.45, 12.3, 0.8, title, 28, WHITE, True)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.17), Inches(1.2), Emu(45000))
        bar.fill.solid()
        bar.fill.fore_color.rgb = CYAN
        bar.line.fill.background()
    SLIDES.append(title or "title")
    tb(s, 0.5, 7.05, 12.3, 0.35, f"BÖVD · NASA Space Apps 2026 · Create Health Monitoring Software for Astronauts on Space Missions · {len(SLIDES)}", 10, MUTED)
    s.notes_slide.notes_text_frame.text = notes
    return s


def chevrons(s, steps, y, x0=0.4, w=1.8, h=0.75, size=10):
    for i, st in enumerate(steps):
        sh = s.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(x0 + i * w), Inches(y), Inches(w - 0.05), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = CYAN if i % 2 == 0 else RGBColor(0x00, 0x7A, 0x99)
        sh.line.fill.background()
        sh.text_frame.text = st
        sh.text_frame.word_wrap = True
        r = sh.text_frame.paragraphs[0].runs[0]
        r.font.size, r.font.bold = Pt(size), True


# 1 ─ title
s = slide("", "Introduce the team and the one-line pitch.")
tb(s, 0.8, 0.9, 11.5, 1.3, "BÖVD", 66, WHITE, True)
tb(s, 0.8, 2.25, 11.7, 1.0, "Explainable, offline health monitoring for astronauts – on the ISS, the Moon, in Mars transit and on Mars", 24, CYAN)
tb(s, 0.8, 3.45, 11.7, 0.9, [f"Team: {TEAM['team_name']}", "Members: " + ", ".join(TEAM["members"])], 18, AMBER, True)
tb(s, 0.8, 4.55, 11.7, 2.2, [
    "NASA Space Apps Challenge 2026",
    "Challenge: Create Health Monitoring Software for Astronauts on Space Missions",
    "Every reading gets four answers: status · why · next step · who to contact"], 17, WHITE)

# 2 ─ hook
s = slide("200 million kilometres from the nearest hospital", "Start calmly; pause before the question.", "The hook")
tb(s, 0.8, 1.8, 7.0, 3.6, [
    "You are on Mars. You wake up with a racing heart and you feel dizzy.",
    "Your message to the doctor on Earth takes up to 20 minutes to arrive…",
    "…and up to 20 more minutes for the answer to come back."], 22, WHITE, space=14)
card(s, 8.3, 1.8, 4.5, 3.2, "In those 40 minutes", ["Who decides what you do?"], AMBER, 26, 20)
tb(s, 0.8, 5.7, 12, 0.8, "Mars is 4–24 light-minutes from Earth, one way. The Moon is about 1.3 seconds.", 15, MUTED)

# 3 ─ problem
s = slide("The problem: space is hard on the human body", "NASA's Human Research Program groups spaceflight risks into five hazards.", "The problem")
for i, (t_, b_) in enumerate([
        ("Radiation", "Solar storms and cosmic rays beyond low Earth orbit raise lifetime cancer risk."),
        ("Isolation", "About 6 hours of sleep in flight, lower mood and stress in a small closed crew."),
        ("Distance", "Up to 24 minutes one-way delay with Mars: no quick help from a doctor."),
        ("Gravity", "Fluid shifts to the head; bones, muscles and eyes change; dizziness after landing."),
        ("Environment", "Closed cabin: CO₂ build-up, pressure changes, noise and microbes.")]):
    card(s, 0.5 + i * 2.5, 1.5, 2.35, 2.9, t_, b_, size=13)
tb(s, 0.5, 4.7, 12.3, 1.6, [
    "• The astronaut is not a doctor and needs clear, simple guidance.",
    "• Earth 'normal' ranges are misleading in space: the body's normal changes with gravity.",
    "• NASA lists 17 health risks of spaceflight, among them cardiovascular changes, SANS (eyes), bone loss, sleep and behaviour."], 16, WHITE)
tb(s, 0.5, 6.45, 12.3, 0.5, "Sources: NASA HRP – Five hazards of human spaceflight; Risks of human spaceflight (2026). CSA – Why do we conduct science experiments in space? (2025).", 11, MUTED)

# 4 ─ meet BÖVD
s = slide("Meet BÖVD", "What it is in one breath, then the four answers.", "Introducing the app")
tb(s, 0.5, 1.45, 12.3, 1.0, "A health monitoring app that astronauts use themselves. It runs on a laptop with no internet, in English and Arabic.", 20, WHITE)
for i, (t_, b_, col) in enumerate([("1 · Status", "Green, yellow or red, plus a 0–20 score", GREEN),
                                   ("2 · Why", "The hazard, the rule and the NASA source", CYAN),
                                   ("3 · Next step", "Clear actions and how to prevent a problem", AMBER),
                                   ("4 · Who to contact", "Crew Medical Officer or flight surgeon", RED)]):
    card(s, 0.5 + i * 3.1, 2.55, 2.95, 1.6, t_, [b_], col, 14)
tb(s, 0.5, 4.45, 6.0, 2.4, [
    "• 5 roles: astronaut, Crew Medical Officer, behavioural health specialist, flight surgeon, researcher",
    "• 17 health indicators with Earth and space guidance",
    "• Inputs: keyboard, clicks, file import, camera (posture only)"], 15, WHITE)
tb(s, 6.8, 4.45, 6.0, 2.4, [
    "• Designed for gloves and floating: large buttons, glove mode, high contrast",
    "• Never diagnoses – it supports decisions",
    "• Starts with one double-click: start.bat"], 15, WHITE)

# 5 ─ how it works
s = slide("How it works", "Walk through the pipeline using the dashboard screenshot.", "Explaining the app")
chevrons(s, ["Measure", "Validate", "Personal baseline", "Thresholds + trends", "Status 0–20", "Why + action", "Escalate"], 1.45)
pic(s, "en_dash.png", 0.5, 2.45, 7.6, 4.4)
tb(s, 8.4, 2.45, 4.5, 4.5, [
    "• Readings: heart rate, blood pressure, SpO₂, temperature, blood glucose (mg/dL), sleep, mood, stress, CO₂, radiation, body mass, exercise, urine",
    "• Compared first with the astronaut's own baseline (mean ± 2 SD, for the current gravity), then with NASA and clinical ranges",
    "• Trend rules: e.g. 3 short nights in a row → red; mood falling 3 days → yellow",
    "• Every value shows where it came from: REAL, SYNTHETIC or USER-ENTERED"], 14, WHITE, space=8)

# 6 ─ 3D body + guidance
s = slide("Clickable 3D body and health guidance", "Show that every organ and every reading explains itself.", "Explaining the app")
pic(s, "en_body3d_crop.png", 0.5, 1.45, 3.7, 5.4)
pic(s, "en_guide.png", 4.4, 1.45, 3.9, 5.4)
tb(s, 8.6, 1.5, 4.3, 5.4, [
    "3D body",
    "• 8 body regions: tap one to see its function, how space affects it and its health status",
    "• 3D animations show how to do each exam correctly in 0 g",
    "",
    "Guidance for every reading",
    "• Why this check matters in space",
    "• How to stay healthy and prevent a critical condition",
    "• English and Arabic, with NASA, CSA and study sources"], 14, WHITE, space=5)

# 7 ─ Smart Doctor + AI
s = slide("Smart Doctor and the NASA-grounded AI assistant", "Protocols are fixed and reviewed; the AI only explains sources.", "Explaining the app")
pic(s, "en_cdss.png", 0.5, 1.45, 6.0, 4.6)
tb(s, 6.8, 1.45, 6.1, 5.4, [
    "Smart Doctor – works offline",
    "• 7 protocols: chest pain, headache + vision change, fever, low blood glucose, insomnia, radiation exposure, post-landing dizziness",
    "• One question per screen, clear “stop and call the CMO” steps; the session is sent to the flight surgeon",
    "",
    "AI research assistant (experimental, optional)",
    "• A free OpenRouter model answers only from 116 NASA and CSA excerpts and cites each one [S1], [S2]…",
    "• Never diagnoses or names medicines; points to the right protocol",
    "• Only the typed question leaves the laptop, with consent; the API key is stored encrypted"], 14, WHITE, space=5)

# 8 ─ solution per hazard
s = slide("The solution: a tool for every hazard", "Map each hazard back to a feature.", "Solving the problem")
rows = [("Radiation", "Personal dose vs the 600 mSv NASA career limit; solar-storm mode with countdown and the safest shelter zone", PURPLE),
        ("Gravity", "Gravity-aware baseline (ISS, Moon, Mars transit, Mars); landing protocol and stand test; eye (SANS) and bone checks", GREEN),
        ("Isolation", "Sleep, mood and stress trends; crew-harmony index; home-connection prompts", AMBER),
        ("Distance", "Offline Smart Doctor; alerts queued with the real Moon/Mars delay", CYAN),
        ("Environment", "Cabin CO₂ judged at the actual cabin pressure; SpO₂ and temperature", RED)]
for i, (t_, b_, col) in enumerate(rows):
    card(s, 0.5, 1.45 + i * 1.08, 6.4, 1.0, t_, [b_], col, 12, 14)
pic(s, "en_radiation.png", 7.2, 1.45, 5.7, 5.3)

# 9 ─ alerts and delay
s = slide("Alerts that respect the distance to Earth", "Show how the ground sees only what has arrived.", "Solving the problem")
chevrons(s, ["Astronaut", "Crew Medical Officer", "Flight surgeon (Earth)"], 1.45, x0=0.5, w=3.0, size=13)
pic(s, "en_surgeon.png", 0.5, 2.45, 7.0, 4.4)
tb(s, 7.8, 2.45, 5.1, 4.4, [
    "• 3 alert priorities: high, medium, low",
    "• Store-and-forward queue in both directions",
    "• Moon ≈ 1.3 s, Mars 4–24 min one way – the delay is simulated",
    "• The flight surgeon sees only alerts that have arrived; acknowledgements travel back with the same delay",
    "• Onboard protocols keep working with no link (Earth-independent medical operations)"], 15, WHITE, space=8)

# 10 ─ NASA data
s = slide("NASA data and resources", "Real NASA data plus the challenge's own resources.", "Trusted science")
pic(s, "en_real_glucose.png", 0.5, 1.45, 6.6, 3.9)
tb(s, 7.4, 1.45, 5.5, 4.0, [
    "• REAL data: NASA OSDR study OSD-575 (SpaceX Inspiration4) – serum glucose, 4 crew × 7 time points",
    "• Built-in OSDR loader turns any study's CSV into health records with a REAL badge",
    "• Thresholds tied to NASA-STD-3001 and HRP evidence reports",
    "• 29-entry evidence register and 33 references"], 14, WHITE, space=8)
tb(s, 0.5, 5.55, 12.3, 1.4, [
    "Challenge resources used: NASA HRP Five hazards · Risks of human spaceflight · Ongoing HRP research · "
    "CSA Monitoring radiation for astronaut health (CANS) · CSA Why do we conduct science experiments in space?"], 13, MUTED)

# 11 ─ trust
s = slide("Built to be trusted", "Security, standards and honest limits.", "Trusted science")
card(s, 0.5, 1.45, 4.0, 2.6, "Private and secure", [
    "• Data stays on the laptop", "• AES-256-GCM encryption", "• Consent for every feature", "• 5 roles, least privilege",
    "• Tamper-proof black box log"], GREEN, 13)
card(s, 4.65, 1.45, 4.0, 2.6, "Standards (designed in line with)", [
    "• 32 international standards", "• ISO 14971 risk management", "• IEC 62304 health software", "• ISO/IEC 27001 security",
    "• HL7 FHIR R4 + LOINC records"], CYAN, 13)
card(s, 8.8, 1.45, 4.0, 2.6, "Tested", [
    "• 151 automated tests pass", "• Browser and accessibility checks", "• Every threshold linked to evidence",
    "• Synthetic data always labelled"], AMBER, 13)
card(s, 0.5, 4.3, 12.3, 2.5, "Honest limits", [
    "• Hackathon prototype for decision support and training – not a certified medical device; not ISO-certified, only designed in line with standards",
    "• Some thresholds (heart rate, SpO₂, temperature, glucose) are clinical defaults that need flight-surgeon review",
    "• Real data so far is one NASA study; voice and webcam-blink features are experimental",
    "• The AI assistant needs internet; everything else works offline"], RED, 13)

# 12 ─ features + comparison
s = slide("Everything BÖVD does – and why it's different", "Use as a summary or during questions.", "Why BÖVD")
tb(s, 0.5, 1.4, 5.9, 5.5, [
    "• 0–20 status score and clickable 3D body",
    "• Personal baseline adjusted for gravity",
    "• “Why” panel with NASA sources",
    "• Guidance for 17 indicators",
    "• Smart Doctor: 7 offline protocols",
    "• NASA-grounded AI assistant",
    "• Alerts with real Moon/Mars delay",
    "• Radiation map and solar-storm mode",
    "• Landing protocol and stand test",
    "• Sleep, mood, stress and crew harmony",
    "• Eye (SANS), urine and exercise coach",
    "• Camera posture check",
    "• Tamper-proof black box",
    "• English/Arabic, glove and high-contrast modes"], 14, WHITE, space=3)
cmp_rows = [("Need internet and the cloud", "Works fully offline"),
            ("Compare you with Earth “normal” ranges", "Your own baseline, for your gravity"),
            ("Show numbers only", "Explain why, next step and who to contact"),
            ("General advice", "Answers only from NASA and CSA sources"),
            ("Data on company servers", "Encrypted on the device, consent per feature"),
            ("Not built for space", "Moon/Mars delay, radiation storms, landing")]
tb(s, 6.7, 1.4, 2.9, 0.4, "Typical health apps", 15, MUTED, True)
tb(s, 9.8, 1.4, 3.1, 0.4, "BÖVD", 16, CYAN, True)
for i, (a, b) in enumerate(cmp_rows):
    y = 1.95 + i * 0.82
    tb(s, 6.7, y, 2.9, 0.8, a, 13, MUTED)
    card(s, 9.7, y - 0.05, 3.2, 0.74, "", [], CYAN)
    tb(s, 9.85, y, 3.0, 0.7, b, 13, WHITE, True)
tb(s, 6.7, 6.9 - 0.05, 6.2, 0.3, "Compared with typical consumer health apps.", 10, MUTED)

# 13 ─ ambition
s = slide("Our ambition: beyond space", "Paint the future, then the Earth uses.", "Ambition and future")
card(s, 0.5, 1.45, 6.0, 2.4, "What we want to achieve", [
    "• Crews at the Artemis Moon base and on Mars missions use BÖVD for Earth-independent care",
    "• Every result stays explainable and traceable to science"], CYAN, 14)
card(s, 6.8, 1.45, 6.0, 2.4, "Next steps", [
    "• Flight-surgeon review of every threshold and protocol", "• More NASA data (OSDR, Life Sciences Portal)",
    "• Neutron dose input like CSA's CANS spectrometer", "• Glove and floating usability tests in an analog mission"], AMBER, 13)
for i, (t_, b_) in enumerate([("Deserts", "Expeditions and remote work sites"), ("War zones", "Field medicine and first aid"),
                              ("Antarctica", "Isolated research stations"), ("Remote clinics", "Offline, low-cost laptop"),
                              ("Personal care", "Anyone tracking their own health")]):
    card(s, 0.5 + i * 2.5, 4.15, 2.35, 1.8, t_, [b_], GREEN, 13)
tb(s, 0.5, 6.15, 12.3, 0.6, "Not limited to space: anywhere help is far away.", 18, CYAN, True)

# 14 ─ live demo
s = slide("Live demo", "Run start.bat before presenting.", "See it in action")
for i, (t_, b_) in enumerate([
        ("1 · Astronaut dashboard", "Log in as astro1: status ring, 3D body, latest readings with sources"),
        ("2 · A worrying reading", "Heart rate 128, sleep 4.5 h, mood 2 → RED with why, next step and who to contact"),
        ("3 · Flight surgeon on Earth", "Log in as surgeon1: alerts arrive with the communication delay"),
        ("4 · Landing on Mars", "Gravity transition protocol and the stand test"),
        ("5 · Solar storm", "Radiation page: storm mode, countdown and shelter zone"),
        ("6 · Smart Doctor + AI", "Open a protocol; ask the assistant a question with NASA sources")]):
    card(s, 0.5 + (i % 3) * 4.15, 1.5 + (i // 3) * 2.55, 4.0, 2.35, t_, [b_], CYAN, 14)

# 15 ─ references
s = slide("Key references", "Full list: deliverables/English/SOURCES.md (33 references).", "Trusted science")
tb(s, 0.5, 1.45, 12.3, 5.4, [
    "NASA Human Research Program. (n.d.). Five hazards of human spaceflight. nasa.gov/hrp/hazards",
    "NASA Human Research Program. (2026). Risks of human spaceflight. nasa.gov/hrp/risks",
    "NASA Human Research Program. (2026). Ongoing HRP research in space. nasa.gov/hrp/ongoing-hrp-research",
    "Canadian Space Agency. (2026). Monitoring radiation for astronaut health.",
    "Canadian Space Agency. (2025). Why do we conduct science experiments in space?",
    "NASA OSDR. OSD-575: SpaceX Inspiration4 blood serum metabolic panel. osdr.nasa.gov",
    "Overbey, E. G., et al. (2024). The Space Omics and Medical Atlas (SOMA). Nature.",
    "NASA. (2023). NASA-STD-3001 Vol. 1 (crew health) and Vol. 2 (environmental health).",
    "NASA HRP evidence reports: orthostatic intolerance (2015), behavioural conditions (2015), team risk (2022).",
    "Barger et al. (2014), Lancet Neurology – sleep in spaceflight. George et al. (2024), Nature – Artemis I radiation.",
    "Lee et al. (2020), npj Microgravity – SANS. Smith et al. (2012), Nutrients – calcium and bone."], 13, WHITE, space=5)

# 16 ─ thank you
s = slide("", "Invite questions.")
tb(s, 0.8, 1.6, 11.7, 1.3, "Thank you", 60, WHITE, True, PP_ALIGN.CENTER)
tb(s, 0.8, 3.0, 11.7, 0.8, "BÖVD – status · why · next step · who to contact", 24, CYAN, align=PP_ALIGN.CENTER)
tb(s, 0.8, 3.9, 11.7, 0.6, "Your questions are welcome", 20, AMBER, True, PP_ALIGN.CENTER)
tb(s, 0.8, 4.7, 11.7, 0.6, "github.com/al8a7aa/bovd5 · double-click start.bat → http://127.0.0.1:8765", 16, WHITE, align=PP_ALIGN.CENTER)
tb(s, 1.3, 5.9, 10.7, 0.9, "AI disclosure: " + TEAM["ai_use"], 10, MUTED, align=PP_ALIGN.CENTER)

cp = prs.core_properties
cp.title = "BÖVD – full presentation (NASA Space Apps 2026)"
cp.author = TEAM["team_name"]
cp.keywords = "NASA Space Apps 2026; astronaut health; OSDR OSD-575; AI-assisted"
cp.comments = ("AI disclosure: AI assistants (LLMs such as Claude) helped write code, documents and this deck. "
               "Idea, design, data choice and review by the team. No AI-generated images, audio or video.")
prs.save(str(OUT))
print(f"saved {OUT} ({len(prs.slides)} slides)")
