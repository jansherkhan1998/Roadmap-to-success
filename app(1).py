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
          model="gemini-3.5-flash", contents=prompt, config=config
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
  pdf.cell(0, 10, f"Preparation Roadmap: {exam_name}", ln=1)
  pdf.ln(3)

  # Strategy Overview
  pdf.set_font("Helvetica", "B", 12)
  title_text = (
      data.get("strategy_title", "Granular Mastery Plan")
      .encode("latin-1", "replace")
      .decode("latin-1")
  )
  pdf.cell(0, 8, title_text, ln=1)
  pdf.ln(3)

  # Schedule List (Bullet/Section style to prevent table width overflow crashes)
  schedule = data.get("schedule", [])
  if schedule:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Structured Schedule Overview", ln=1)
    pdf.ln(2)

    for i, row_data in enumerate(schedule, 1):
      time_block = (
          str(row_data.get("time_block", f"Phase {i}"))
          .encode("latin-1", "replace")
          .decode("latin-1")
      )
      subj_focus = (
          str(row_data.get("subject_focus", ""))
          .encode("latin-1", "replace")
          .decode("latin-1")
      )
      chapters = (
          str(row_data.get("chapters_to_cover", ""))
          .encode("latin-1", "replace")
          .decode("latin-1")
      )
      actions = (
          str(row_data.get("action_tasks", ""))
          .encode("latin-1", "replace")
          .decode("latin-1")
      )
      mcq_target = (
          str(row_data.get("practice_target", ""))
          .encode("latin-1", "replace")
          .decode("latin-1")
      )

      # Timeline & Focus Header
      pdf.set_font("Helvetica", "B", 10)
      pdf.cell(0, 6, f"{i}. Timeline: {time_block} | Focus: {subj_focus}", ln=1)

      # Details
      pdf.set_font("Helvetica", "", 9)
      if chapters:
        pdf.multi_cell(0, 5, f"   Chapters: {chapters}")
      if actions:
        pdf.multi_cell(0, 5, f"   Daily Routine: {actions}")
      if mcq_target:
        pdf.multi_cell(0, 5, f"   Practice Target: {mcq_target}")

      pdf.ln(2)

  pdf.ln(3)

  # Subtopic Details Breakdown
  pdf.set_font("Helvetica", "B", 12)
  pdf.cell(0, 8, "Detailed Subtopic Breakdown", ln=1)
  pdf.ln(2)

  pdf.set_font("Helvetica", "", 9)
  for block in schedule:
    time_block = (
        str(block.get("time_block", "Phase"))
        .encode("latin-1", "replace")
        .decode("latin-1")
    )
    subtopics_group = block.get("detailed_subtopics", [])

    if subtopics_group:
      pdf.set_font("Helvetica", "B", 10)
      pdf.cell(0, 6, f"[{time_block}] Subtopics:", ln=1)
      pdf.set_font("Helvetica", "", 9)

      for item in subtopics_group:
        if isinstance(item, dict):
          ch = (
              str(item.get("chapter", "Chapter"))
              .encode("latin-1", "replace")
              .decode("latin-1")
          )
          pdf.cell(0, 5, f"  * Chapter: {ch}", ln=1)
          for sub in item.get("subtopics", []):
            sub_clean = (
                str(sub).encode("latin-1", "replace").decode("latin-1")
            )
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

  # Filter out nested subtopic array from main dataframe display
  table_cols = [
      c
      for c in df.columns
      if c
      in [
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

  st.data_editor(
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
      "Expand any time block below to see exact subtopics, mechanisms, and core concept requirements."
  )

  for block in schedule:
    time_label = (
        block.get("time_block") or block.get("phase") or "Study Phase"
    )
    chapters_label = (
        block.get("chapters_to_cover") or block.get("subject_focus") or ""
    )
    subtopic_data = block.get("detailed_subtopics", [])

    with st.expander(f"📌 **{time_label}**: {chapters_label}"):
      if isinstance(subtopic_data, list) and len(subtopic_data) > 0:
        for item in subtopic_data:
          if isinstance(item, dict):
            ch_name = item.get("chapter", "Chapter Focus")
            st.markdown(f"#### 📘 {ch_name}")
            for sub in item.get("subtopics", []):
              st.write(f"  • {sub}")
            st.markdown("---")
          elif isinstance(item, str):
            st.write(f"• {item}")
      else:
        st.markdown("#### 📘 Core Chapters")
        for ch in block.get("chapters_to_cover", "").split("|"):
          if ch.strip():
            st.write(f"  • **{ch.strip()}**")

        st.markdown("#### 📝 Key Tasks")
        tasks = block.get("action_tasks", "")
        if tasks:
          st.write(f"  • {tasks}")

  st.divider()

  # Download PDF Button
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
    st.error(f"Could not prepare PDF download: {e}")


# ============================================================
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
        st.write(f"❌ Q{i + 1}: Correct answer = **{correct_answer}**")
        st.caption(question["explanation"])


# ============================================================
# HEADER & SIDEBAR
# ============================================================

st.title("📚 Roadmap to Success")
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
    with st.spinner("Building your personalized high-yield roadmap..."):
      try:
        raw_response = ask_gemini(
            roadmap_prompt(exam_name, exam_date, level, hours, focus),
            json_mode=True,
        )
        data = parse_ai_json(raw_response)
        if data:
          st.session_state.roadmap = data
          st.success("Roadmap generated successfully!")
        else:
          st.error(
              "Failed to structure roadmap data. Please click 'Generate'"
              " again."
          )
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
        raw_response = ask_gemini(
            mcq_prompt(exam_name, subject, difficulty, count, quiz_level),
            json_mode=True,
        )
        data = parse_ai_json(raw_response)
        questions = data.get("questions", [])
        st.session_state.questions = questions
        st.session_state.quiz_answers = [None for _ in questions]
      except Exception as error:
        st.error(f"Could not generate test: {error}")

  if "questions" in st.session_state and st.session_state.questions:
    run_quiz(st.session_state.questions)

with tab3:
  st.markdown("""
### 🚀 Roadmap to Success Features
1. **Interactive High-Level Schedule**: Overview of timelines, subjects, target chapters, and study tasks.
2. **Granular Subtopic Breakdown**: Expandable dropdowns detailing specific organelle functions, chemical laws, and physics formulas.
3. **Safe JSON Parsing**: Automated system recovery prevents crashes from API limit cut-offs.
4. **Downloadable PDF Export**: Download and save your customized schedule with complete subtopic breakdowns offline.
5. **Interactive MCQ Practice Engine**: Generate custom entrance test practice MCQs complete with options and explanation keys.
""")
