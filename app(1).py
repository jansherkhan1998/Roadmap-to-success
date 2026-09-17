from datetime import date
import json
import os
import time
from fpdf import FPDF
from google import genai
from google.genai import types
from google.genai.errors import APIError
from json_repair import repair_json
import pandas as pd
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Roadmap to Success", page_icon="📚", layout="wide"
)


# ============================================================
# AVAILABLE TESTS
# ============================================================

EXAMS = [
    "MDCAT",
    "ECAT",
    "NUST NET",
    "NTS NAT",
    "NTS GAT",
    "ISSB Initial Test",
    "FAST-NU Admission Test",
    "COMSATS Admission Test",
    "ETEA Engineering",
    "ETEA Medical",
    "UET Entrance Test",
    "Other / Custom Test",
]

LEVELS = ["Beginner", "Intermediate", "Advanced"]

SUBJECTS = [
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "English",
    "IQ / Analytical Reasoning",
    "General Knowledge",
    "Mixed",
]


# ============================================================
# GEMINI API
# ============================================================


def get_api_key():
  """Read the Gemini API key from Streamlit secrets or an environment variable."""
  try:
    key = st.secrets.get("GEMINI_API_KEY")
  except Exception:
    key = None

  return key or os.getenv("GEMINI_API_KEY")


@st.cache_resource
def get_client(api_key):
  return genai.Client(api_key=api_key)


def ask_gemini(prompt, json_mode=False, max_retries=5):
  api_key = get_api_key()

  if not api_key:
    raise RuntimeError(
        "Gemini API key is missing. Add GEMINI_API_KEY to Streamlit Secrets."
    )

  client = get_client(api_key)

  config = types.GenerateContentConfig(
      temperature=0.2,
      max_output_tokens=8192,  # Ensures detailed responses fit without truncation
      response_mime_type="application/json",
  )

  # Automatic retry logic for server spikes (503/429 errors)
  for attempt in range(max_retries):
    try:
      response = client.models.generate_content(
          model="gemini-2.5-flash", contents=prompt, config=config
      )
      return response.text

    except APIError as e:
      if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
        wait_time = (2**attempt) + 1  # Exponential backoff (2s, 3s, 5s...)
        time.sleep(wait_time)
      else:
        raise e


# ============================================================
# SAFE JSON PARSER (FIXES UNTERMINATED STRINGS)
# ============================================================


def parse_ai_json(response_text):
  """Safely parses LLM response text into JSON.

  Uses repair_json to handle truncated or cut-off strings smoothly.
  """
  if not response_text:
    return {}

  text = response_text.strip()

  # Clean markdown code blocks if present
  if text.startswith("```"):
    lines = text.splitlines()
    if lines[0].startswith("```"):
      lines = lines[1:]
    if lines and lines[-1].startswith("```"):
      lines = lines[:-1]
    text = "\n".join(lines).strip()

  try:
    # Attempt native load first
    return json.loads(text)
  except Exception:
    # If the JSON is truncated or has syntax flaws, auto-repair it
    try:
      repaired_str = repair_json(text)
      return json.loads(repaired_str)
    except Exception as e:
      st.error(f"Could not parse AI output: {e}")
      return {}


# ============================================================
# PDF GENERATOR
# ============================================================


def generate_roadmap_pdf(data, exam_name):
  pdf = FPDF()
  pdf.add_page()
  pdf.set_auto_page_break(auto=True, margin=15)

  # Title
  pdf.set_font("Helvetica", "B", 16)
  pdf.cell(
      0, 10, f"Preparation Roadmap: {exam_name}", new_x="LMARGIN", new_y="NEXT"
  )
  pdf.ln(5)

  # Strategy Overview
  pdf.set_font("Helvetica", "B", 12)
  title_text = (
      data.get("strategy_title", "Granular Mastery Plan")
      .encode("latin-1", "replace")
      .decode("latin-1")
  )
  pdf.cell(0, 8, title_text, new_x="LMARGIN", new_y="NEXT")
  pdf.ln(3)

  # Schedule Table
  schedule = data.get("schedule", [])
  if schedule:
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Structured Schedule", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    with pdf.table(
        col_widths=(25, 30, 45, 60, 20), text_align="LEFT"
    ) as table:
      header = table.row()
      header.cell("Timeline")
      header.cell("Subject")
      header.cell("Chapters Covered")
      header.cell("Action Plan")
      header.cell("MCQ Target")

      for row_data in schedule:
        row = table.row()
        row.cell(str(row_data.get("time_block", "")))
        row.cell(
            str(row_data.get("subject_focus", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(
            str(row_data.get("chapters_to_cover", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(
            str(row_data.get("action_tasks", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(str(row_data.get("practice_target", "")))

  pdf.ln(5)

  # Subtopic Details Breakdown
  pdf.set_font("Helvetica", "B", 12)
  pdf.cell(0, 8, "Detailed Subtopic Breakdown", new_x="LMARGIN", new_y="NEXT")
  pdf.ln(2)

  pdf.set_font("Helvetica", "", 10)
  for block in schedule:
    time_block = block.get("time_block", "Phase")
    subtopics_group = block.get("detailed_subtopics", [])

    if subtopics_group:
      pdf.set_font("Helvetica", "B", 10)
      pdf.cell(0, 6, f"[{time_block}] Subtopics:", new_x="LMARGIN", new_y="NEXT")
      pdf.set_font("Helvetica", "", 9)

      for item in subtopics_group:
        if isinstance(item, dict):
          ch = (
              item.get("chapter", "Chapter")
              .encode("latin-1", "replace")
              .decode("latin-1")
          )
          pdf.cell(0, 5, f"  * Chapter: {ch}", new_x="LMARGIN", new_y="NEXT")
          for sub in item.get("subtopics", []):
            sub_clean = sub.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, f"    - {sub_clean}")
        elif isinstance(item, str):
          sub_clean = item.encode("latin-1", "replace").decode("latin-1")
          pdf.multi_cell(0, 5, f"  - {sub_clean}")

      pdf.ln(2)

  return bytes(pdf.output())


# ============================================================
# ROADMAP PROMPT
# ============================================================


def roadmap_prompt(exam, exam_date, level, hours, focus):
  days = max(1, (exam_date - date.today()).days)
  weeks = max(1, days // 7)

  return f"""
You are the Chief Academic Strategist for Pakistani Entrance Exams ({exam}).

Target Exam: {exam}
Timeframe: {days} Days ({weeks} Weeks)
Level: {level} | Hours/Day: {hours} | Focus: {focus or "Full Syllabus High-Yield"}

IMPORTANT INSTRUCTION FOR CONCISE HIGH-DETAIL:
Provide a structured syllabus roadmap. For every phase or time block, break down the core chapters into 3-4 bullet-point subtopics. Focus strictly on official syllabus terms and micro-concepts to remain concise and stay within length boundaries.

Return ONLY valid JSON matching this exact structure:
{{
    "strategy_title": "Granular Syllabus Roadmap for {exam}",
    "schedule": [
        {{
            "time_block": "Weeks 1-6",
            "subject_focus": "Biology & Chemistry Foundations",
            "chapters_to_cover": "Bio: Cell Biology, Enzymes | Chem: Basic Concepts",
            "recommended_books": "Punjab/KPK Textbook Board & KIPS Series",
            "action_tasks": "Read textbook lines, annotate organelle functions, solve 80 MCQs daily",
            "practice_target": "500 MCQs",
            "detailed_subtopics": [
                {{
                    "chapter": "Cell Biology",
                    "subtopics": [
                        "Fluid Mosaic Model: Phospholipid bilayer fluidity and transport mechanisms",
                        "Organelles: ER, Golgi apparatus sorting, Lysosomes acidic pH and storage diseases",
                        "Energy Transducers: Mitochondria cristae and chloroplast thylakoids",
                        "Nucleus and Chromosomes: Histone octamers, nucleosome folding, 70S vs 80S ribosomes"
                    ]
                }},
                {{
                    "chapter": "Basic Concepts and Stoichiometry",
                    "subtopics": [
                        "Mole concept, Avogadros number, and gas molar volume at STP",
                        "Empirical vs Molecular formula derivations",
                        "Limiting Reactants identification and percentage yield calculations"
                    ]
                }}
            ]
        }}
    ],
    "error_log_protocol": ["Rule 1", "Rule 2"],
    "test_day_strategy": ["Tip 1", "Tip 2"]
}}
"""


# ============================================================
# MCQ PROMPT
# ============================================================


def mcq_prompt(exam, subject, difficulty, count, level):
  return f"""
Create {count} original practice MCQs for Pakistani entrance test preparation.

Exam: {exam}
Subject: {subject}
Difficulty: {difficulty}
Student Level: {level}

Return ONLY valid JSON
