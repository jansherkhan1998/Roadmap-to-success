from datetime import date
import json
import os
from fpdf import FPDF
from google import genai
from google.genai import types
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Roadmap to success", page_icon="📚", layout="wide"
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

import time
from google.genai.errors import APIError


def ask_gemini(prompt, json_mode=False, max_retries=5):
  api_key = get_api_key()

  if not api_key:
    raise RuntimeError(
        "Gemini API key is missing. Add GEMINI_API_KEY to Streamlit Secrets."
    )

  client = get_client(api_key)

  config = types.GenerateContentConfig(
      temperature=0.3,
      max_output_tokens=8192,  # Ensures long structured outputs fit
      response_mime_type="application/json" if json_mode else "text/plain",
  )

  # Automatic retry logic for temporary server-side spikes (503/429 errors)
  for attempt in range(max_retries):
    try:
      response = client.models.generate_content(
          model="gemini-3.5-flash", contents=prompt, config=config
      )
      return response.text

    except APIError as e:
      # If it's a 503 (Overloaded) or 429 (Rate Limit) error, retry automatically
      if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
        wait_time = (2**attempt) + 1  # Waits 2s, 3s, 5s, 9s...
        time.sleep(wait_time)
      else:
        raise e  # If retries run out or it's a different error, raise it


# ============================================================
# JSON CLEANER
# ============================================================


def clean_json(text):
  text = text.strip()

  if text.startswith("```"):
    lines = text.splitlines()
    if lines[-1].strip().startswith("```"):
      lines = lines[1:-1]
    else:
      lines = lines[1:]
    text = "\n".join(lines).strip()

  try:
    return json.loads(text)
  except json.JSONDecodeError as e:
    st.error(
        f"Failed to parse AI output into JSON: {e}. Please click 'Generate' again."
    )
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

  # Summary
  pdf.set_font("Helvetica", "B", 12)
  pdf.cell(0, 8, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
  pdf.set_font("Helvetica", "", 10)
  summary_text = data.get("summary", "").encode("latin-1", "replace").decode("latin-1")
  pdf.multi_cell(0, 5, summary_text)
  pdf.ln(5)

  # Schedule Table
  schedule = data.get("day_by_day_schedule", [])
  if schedule:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Day-by-Day Schedule", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Render Table
    with pdf.table(
        col_widths=(15, 25, 45, 80, 20), text_align="LEFT"
    ) as table:
      header = table.row()
      header.cell("Day #")
      header.cell("Subject")
      header.cell("Topic")
      header.cell("Action Items")
      header.cell("Hours")

      for row_data in schedule:
        row = table.row()
        row.cell(str(row_data.get("day_number", "")))
        row.cell(
            str(row_data.get("subject", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(
            str(row_data.get("topic", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(
            str(row_data.get("action_items", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(str(row_data.get("hours", "")))

  # PDF Output
  return bytes(pdf.output())


# ============================================================
# ROADMAP PROMPT
# ============================================================


def roadmap_prompt(exam, exam_date, level, hours, focus):
  days = max(1, (exam_date - date.today()).days)
  weeks = max(1, days // 7)

  # 1. Dynamic Granularity Rule to prevent Token Errors
  if weeks > 16:
    structure_type = "Macro-Phases (Block of Weeks)"
    granularity_instruction = f"""
        Given the long preparation window ({days} days / {weeks} weeks), group the output into 4-6 MACRO PHASES.
        Do NOT write individual days. Write structured blocks (e.g. Phase 1: Weeks 1-6, Phase 2: Weeks 7-12...).
        """
  elif weeks > 4:
    structure_type = "Weekly Schedule"
    granularity_instruction = f"""
        Group the schedule into WEEKLY blocks ({weeks} Weeks total).
        For each week, specify exact chapter targets and MCQ quotas.
        """
  else:
    structure_type = "Daily Schedule"
    granularity_instruction = (
        f"Provide a granular DAY-BY-DAY schedule covering all {days} days."
    )

  return f"""
#def roadmap_prompt(exam, exam_date, level, hours, focus):
  days = max(1, (exam_date - date.today()).days)
  weeks = max(1, days // 7)

  return f"""
You are an Experienced Chief Academic Strategist for Pakistani  Competitive & University Entrance test Exams ({exam}).

STUDENT & EXAM SPECIFICATIONS:
- Target Test: {exam}
- Target Date: {exam_date.isoformat()} ({days} days / {weeks} weeks remaining)
- Starting Level: {level}
- Commitment: {hours} hours/day
- Focus Area: {focus or "Full Syllabus High-Yield Coverage"}

TEST-SPECIFIC SYLLABUS DIRECTIVES:
- If MDCAT: Prioritize Biology (81 MCQs), Chemistry (45 MCQs), Physics (36 MCQs), English & Logical Reasoning.
- If ECAT/UET: Prioritize Math (30 MCQs), Physics (30 MCQs), Chemistry/CS (30 MCQs), English (10 MCQs).
- If NUST NET: Focus on Math (50%), Physics (30%), English (20%) time-management (~50s per MCQ).
- If NTS NAT/GAT/FAST: Heavy focus on Analytical Reasoning, Quantitative, Verbal, and IQ.

INSTRUCTION FOR HIGH DETAIL:
For EVERY chapter listed, you MUST break it down into explicit SUBTOPICS and core CONCEPTS required by the official syllabus (PMDC / UET / NUST). 

Example for "Cell Biology":
- Subtopics: Fluid Mosaic Model, Endomembrane System (Rough/Smooth ER, Golgi, Lysosomes), Organelle Autophagy, Mitochondria Cristae & mtDNA, Chromosome Nucleosome packing (Histones H1-H4), Prokaryote (70S) vs Eukaryote (80S) Ribosomes.

Return ONLY valid JSON with this schema:
{{
    "strategy_title": "Granular Syllabus Roadmap for {exam}",
    "schedule": [
        {{
            "time_block": "Week 1 (Days 1-7)",
            "subject_focus": "Biology & Chemistry",
            "chapters_to_cover": "Bio: Cell Biology | Chem: Basic Concepts & Stoichiometry",
            "recommended_books": "Punjab/KPK Textbook Board & KIPS Series",
            "action_tasks": "Read textbook lines, annotate organelle functions, solve 80 MCQs/day",
            "practice_target": "500 MCQs",
            "detailed_subtopics": [
                {{
                    "chapter": "Cell Biology",
                    "subtopics": [
                        "Plasma Membrane: Fluid Mosaic Model, Phospholipid bilayer fluidity & transport mechanisms",
                        "Organelles: Endoplasmic Reticulum, Golgi apparatus sorting, Lysosomal acidic pH (~5) & storage diseases",
                        "Energy Transducers: Mitochondria cristae & chloroplast thylakoid structures",
                        "Nucleus & Chromosomes: Histone octamers, nucleosome folding, and 70S vs 80S ribosome comparison"
                    ]
                }},
                {{
                    "chapter": "Basic Concepts & Stoichiometry",
                    "subtopics": [
                        "Mole concept, Avogadro's number calculations, and molar volume of gases at STP",
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

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "question": "Question text",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "answer": "A",
            "explanation": "Short explanation",
            "topic": "Topic"
        }}
    ]
}}
"""


# ============================================================
# DISPLAY ROADMAP
# ============================================================


import pandas as pd
import streamlit as st


def show_roadmap(data, exam_name):
  if not data:
    st.warning("⚠️ No roadmap data available. Please regenerate.")
    return

  st.subheader(f"🔥 {data.get('strategy_title', 'Granular Mastery Plan')}")

  schedule = data.get("schedule", [])
  if not schedule:
    st.warning("⚠️ Schedule items could not be loaded. Please regenerate.")
    return

  # ---------------------------------------------------------
  # LAYER 1: Interactive High-Level Checklist Table
  # ---------------------------------------------------------
  st.markdown("### 📅 Step 1: High-Level Study Schedule")
  df = pd.DataFrame(schedule)

  # Filter out nested detailed_subtopics from the main table view to keep it clean
  table_cols = [
      c
      for c in df.columns
      if c in [
          "time_block",
          "subject_focus",
          "chapters_to_cover",
          "action_tasks",
          "practice_target",
          "recommended_books",
      ]
  ]
  table_df = df[table_cols].copy()

  if "completed" not in table_df.columns:
    table_df.insert(0, "completed", False)

  edited_df = st.data_editor(
      table_df,
      column_config={
          "completed": st.column_config.CheckboxColumn(
              "Status", default=False
          ),
          "time_block": "Timeline",
          "subject_focus": "Subject Focus",
          "chapters_to_cover": "Exact Chapters",
          "action_tasks": "Daily Study Routine",
          "practice_target": "MCQ Target",
          "recommended_books": "Reference Material",
      },
      use_container_width=True,
      hide_index=True,
      key=f"roadmap_table_{exam_name}",
  )

  st.divider()

  # ---------------------------------------------------------
  # LAYER 2: Granular Subtopic & Micro-Concept Deep Dive
  # ---------------------------------------------------------
  st.markdown("### 🔍 Step 2: Detailed Subtopic & Concept Breakdown")
  st.caption(
      "Expand any time block below to see the exact subtopics, organelle/reaction mechanisms, and numerical formulas required by the official syllabus."
  )

  for block in schedule:
    time_label = block.get("time_block", "Study Block")
    chapters_label = block.get("chapters_to_cover", "")
    subtopic_data = block.get("detailed_subtopics", [])

    with st.expander(f"📌 **{time_label}**: {chapters_label}"):
      if subtopic_data:
        for item in subtopic_data:
          ch_name = item.get("chapter", "Chapter Focus")
          st.markdown(f"#### 📘 {ch_name}")

          subtopics_list = item.get("subtopics", [])
          for sub in subtopics_list:
            st.write(f"  • {sub}")
          st.markdown("---")
      else:
        st.info("No detailed subtopic breakdowns available for this block.")

  st.divider()

  # Download Button
  try:
    pdf_bytes = generate_roadmap_pdf(data, exam_name)
    st.download_button(
        label="📄 Download Complete Detailed PDF Plan",
        data=pdf_bytes,
        file_name=f"{exam_name}_Granular_Plan.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
  except Exception as e:
    st.error(f"PDF error: {e}")# ============================================================
# QUIZ ENGINE
# ============================================================


def run_quiz(questions):
  if (
      "quiz_answers" not in st.session_state
      or len(st.session_state.quiz_answers) != len(questions)
  ):
    st.session_state.quiz_answers = [None for _ in questions]

  for i, question in enumerate(questions):
    st.markdown(f"### Q{i + 1}. {question['question']}")

    answer = st.radio(
        "Select an answer",
        options=["A", "B", "C", "D"],
        format_func=lambda x, options=question["options"]: f"{x}. {options[x]}",
        key=f"question_{i}",
        index=None,
    )

    st.session_state.quiz_answers[i] = answer

  if st.button("Submit Test", type="primary"):
    score = sum(
        answer == question["answer"]
        for answer, question in zip(
            st.session_state.quiz_answers, questions
        )
    )

    percentage = (score / len(questions)) * 100

    st.success(f"Score: {score}/{len(questions)} ({percentage:.1f}%)")

    st.subheader("📊 Answer Review")

    for i, question in enumerate(questions):
      user_answer = st.session_state.quiz_answers[i]
      correct_answer = question["answer"]

      if user_answer == correct_answer:
        st.write(f"✅ Q{i + 1}: Correct")
      else:
        st.write(
            f"❌ Q{i + 1}: Correct answer = **{correct_answer}**"
        )
        st.caption(question["explanation"])


# ============================================================
# HEADER & SIDEBAR
# ============================================================

st.title("📚 Roadmap to success")
st.caption(
    "AI-powered preparation roadmaps and practice MCQs for Pakistani entrance"
    " tests."
)

with st.sidebar:
  st.header("👨‍🎓 Student Profile")
  exam = st.selectbox("Select Test", EXAMS)
  custom_exam = st.text_input(
      "Custom Test Name", disabled=(exam != "Other / Custom Test")
  )

  exam_name = (
      custom_exam.strip()
      if (exam == "Other / Custom Test" and custom_exam.strip())
      else exam
  )
  exam_date = st.date_input("Target Test Date", min_value=date.today())
  level = st.selectbox("Preparation Level", LEVELS)
  hours = st.slider("Study Hours Per Day", 1, 12, 4)
  focus = st.text_input("Special Focus", placeholder="e.g. Physics numericals")


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    ["🗺️ Preparation Roadmap", "📝 Practice MCQs", "ℹ️ How It Works"]
)

with tab1:
  days = max(0, (exam_date - date.today()).days)
  col1, col2, col3 = st.columns(3)
  col1.metric("Test", exam_name)
  col2.metric("Days Remaining", days)
  col3.metric("Level", level)

  if st.button(
      "🚀 Generate My Complete Roadmap",
      type="primary",
      use_container_width=True,
  ):
    with st.spinner("Building your personalized day-by-day roadmap..."):
      try:
        response = ask_gemini(
            roadmap_prompt(exam_name, exam_date, level, hours, focus),
            json_mode=True,
        )
        data = clean_json(response)
        st.session_state.roadmap = data
      except Exception as error:
        st.error(f"Could not generate roadmap: {error}")

  if "roadmap" in st.session_state:
    show_roadmap(st.session_state.roadmap, exam_name)

with tab2:
  st.subheader("📝 AI Practice Test Generator")
  col1, col2, col3, col4 = st.columns(4)
  subject = col1.selectbox("Subject", SUBJECTS)
  difficulty = col2.selectbox("Difficulty", ["Easy", "Medium", "Hard", "Mixed"])
  count = col3.selectbox("Number of Questions", [5, 10, 15, 20], index=1)
  quiz_level = col4.selectbox("Student Level", LEVELS, key="quiz_level")

  if st.button(
      "🎯 Generate New MCQ Test", type="primary", use_container_width=True
  ):
    with st.spinner("Generating practice questions..."):
      try:
        response = ask_gemini(
            mcq_prompt(exam_name, subject, difficulty, count, quiz_level),
            json_mode=True,
        )
        data = clean_json(response)
        questions = data.get("questions", [])
        st.session_state.questions = questions
        st.session_state.quiz_answers = [None for _ in questions]
      except Exception as error:
        st.error(f"Could not generate test: {error}")

  if "questions" in st.session_state and st.session_state.questions:
    run_quiz(st.session_state.questions)

with tab3:
  st.markdown("""
### 🚀 PakPrep AI Features
1. **Day-by-Day Table Schedule**: Generates explicit topics, chapters, and hours per day.
2. **Downloadable PDF**: Export your personalized roadmap to a clean PDF file to read later.
3. **Interactive MCQ Engine**: Generate original practice MCQs with explanations and answer keys.
""")
