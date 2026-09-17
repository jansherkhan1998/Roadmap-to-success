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
# GEMINI API & SAFE PARSER
# ============================================================


def get_api_key():
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
        "Gemini API key missing. Add GEMINI_API_KEY to Streamlit Secrets."
    )

  client = get_client(api_key)
  config = types.GenerateContentConfig(
      temperature=0.2,
      max_output_tokens=8192,
      response_mime_type="application/json",
  )

  for attempt in range(max_retries):
    try:
      response = client.models.generate_content(
          model="gemini-2.5-flash", contents=prompt, config=config
      )
      return response.text
    except APIError as e:
      if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
        time.sleep((2**attempt) + 1)
      else:
        raise e


def parse_ai_json(response_text):
  if not response_text:
    return {}
  text = response_text.strip()
  if text.startswith("```"):
    lines = text.splitlines()
    if lines[0].startswith("```"):
      lines = lines[1:]
    if lines and lines[-1].startswith("```"):
      lines = lines[:-1]
    text = "\n".join(lines).strip()

  try:
    return json.loads(text)
  except Exception:
    try:
      repaired_str = repair_json(text)
      return json.loads(repaired_str)
    except Exception as e:
      st.error(f"Could not parse AI output: {e}")
      return {}


# ============================================================
# FIXED PDF GENERATOR (Backward compatible with all FPDF versions)
# ============================================================


def generate_roadmap_pdf(data, exam_name):
  pdf = FPDF()
  pdf.add_page()
  pdf.set_auto_page_break(auto=True, margin=15)

  # Title
  pdf.set_font("Helvetica", "B", 16)
  pdf.cell(0, 10, f"Preparation Roadmap: {exam_name}", ln=1)
  pdf.ln(3)

  pdf.set_font("Helvetica", "B", 11)
  title_text = (
      data.get("strategy_title", "Syllabus Mastery Plan")
      .encode("latin-1", "replace")
      .decode("latin-1")
  )
  pdf.cell(0, 8, title_text, ln=1)
  pdf.ln(3)

  schedule = data.get("schedule", [])
  for block in schedule:
    time_block = (
        block.get("time_block", "Phase")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )
    subj_focus = (
        block.get("subject_focus", "")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Timeline: {time_block} | Focus: {subj_focus}", ln=1)

    pdf.set_font("Helvetica", "", 9)
    act = (
        f"Routine: {block.get('action_tasks', '')} | Target:"
        f" {block.get('practice_target', '')}"
    )
    pdf.multi_cell(0, 5, act.encode("latin-1", "replace").decode("latin-1"))
    pdf.ln(2)

    subtopics_group = block.get("detailed_subtopics", [])
    if subtopics_group:
      for item in subtopics_group:
        if isinstance(item, dict):
          subject = (
              item.get("subject", "")
              .encode("latin-1", "replace")
              .decode("latin-1")
          )
          ch = (
              item.get("chapter", "")
              .encode("latin-1", "replace")
              .decode("latin-1")
          )
          pdf.set_font("Helvetica", "B", 10)
          pdf.cell(0, 5, f"  [{subject}] Chapter: {ch}", ln=1)

          pdf.set_font("Helvetica", "", 9)
          for sub in item.get("subtopics", []):
            sub_clean = sub.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, f"    - {sub_clean}")
        pdf.ln(1)
    pdf.ln(4)

  return bytes(pdf.output())


# ============================================================
# SYLLABUS-STRICT PROMPTS
# ============================================================


def roadmap_prompt(exam, exam_date, level, hours, focus):
  days = max(1, (exam_date - date.today()).days)
  weeks = max(1, days // 7)

  return f"""
You are the Chief Academic Strategist for Pakistani Competitive Entrance Exams ({exam}).

Target Exam: {exam}
Timeframe: {days} Days ({weeks} Weeks)
Student Level: {level} | Hours/Day: {hours} | Focus: {focus or "Complete Syllabus High-Yield"}

STRICT SYLLABUS RULES:
1. Base ALL chapters and subtopics strictly on official syllabus guidelines (e.g., PMDC for MDCAT, ECAT/UET syllabus, NUST NET syllabus, Federal/Punjab/KPK/Sindh textbook boards).
2. DO NOT omit any subject required by the exam. If MDCAT: include Bio, Chem, Physics, English, Logical Reasoning. If ECAT/NET: include Math, Physics, Chem/CS, English.
3. Every `detailed_subtopics` element MUST explicitly list the Subject, the exact Textbook Chapter name, and 3-4 granular high-yield micro-topics/mechanisms/formulas.

Return ONLY valid JSON matching this exact structure:
{{
    "strategy_title": "Official Syllabus-Mapped Roadmap for {exam}",
    "schedule": [
        {{
            "time_block": "Weeks 1-2",
            "subject_focus": "Core Fundamentals Across All Subjects",
            "chapters_to_cover": "Bio: Cell Structure, Enzymes | Chem: Stoichiometry, Atomic Structure | Phys: Vectors, Force & Motion | Eng: Tenses & Subject-Verb Agreement",
            "recommended_books": "Punjab/KPK/Federal Textbooks & KIPS/STEP Series",
            "action_tasks": "Textbook line-by-line reading, note-taking, solve 100 MCQs daily",
            "practice_target": "700 MCQs",
            "detailed_subtopics": [
                {{
                    "subject": "Biology",
                    "chapter": "Cell Structure and Function",
                    "subtopics": [
                        "Fluid Mosaic Model: Phospholipid bilayer transport mechanisms (Active vs Passive)",
                        "Organelles: Endoplasmic Reticulum, Golgi apparatus sorting, Lysosome pH & storage diseases",
                        "Mitochondria Cristae & Chloroplast Thylakoid ATP Synthesis",
                        "Prokaryote (70S) vs Eukaryote (80S) Ribosomes & Nucleosome folding"
                    ]
                }},
                {{
                    "subject": "Chemistry",
                    "chapter": "Fundamental Concepts of Chemistry",
                    "subtopics": [
                        "Mole concept, Avogadros Number, Molar Volume at STP",
                        "Stoichiometric calculations with balanced chemical equations",
                        "Limiting Reactant determination & Percentage Yield formula calculations"
                    ]
                }},
                {{
                    "subject": "Physics",
                    "chapter": "Force and Motion",
                    "subtopics": [
                        "Displacement-time & Velocity-time graph interpretations",
                        "Newtons Laws of Motion & Momentum Conservation in 1D/2D collisions",
                        "Projectile Motion: Maximum height, time of flight, horizontal range formulas"
                    ]
                }},
                {{
                    "subject": "English & Logic",
                    "chapter": "Grammar & Logical Reasoning",
                    "subtopics": [
                        "Subject-Verb Agreement rules and pronoun-antecedent agreement",
                        "Logical Deduction, Cause and Effect, Symbol series patterns"
                    ]
                }}
            ]
        }}
    ]
}}
"""


def mcq_prompt(exam, subject, difficulty, count, level):
  return f"""
Create {count} high-yield MCQs for Pakistani entrance test preparation adhering strictly to official textbook concepts.

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
            "explanation": "Short textbook-aligned explanation",
            "topic": "Topic Name"
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

  # LAYER 1: Table
  st.markdown("### 📅 Step 1: Syllabus Phase Schedule")
  df = pd.DataFrame(schedule)

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
          "subject_focus": "Subjects",
          "chapters_to_cover": "Target Chapters Across Syllabus",
          "action_tasks": "Daily Action Routine",
          "practice_target": "MCQ Target",
          "recommended_books": "Textbooks & Guides",
      },
      use_container_width=True,
      hide_index=True,
      key=f"roadmap_table_{exam_name}",
  )

  st.divider()

  # LAYER 2: Detailed Subtopic Breakdown
  st.markdown("### 🔍 Step 2: Book & Syllabus Subtopic Breakdown")
  st.caption(
      "Expand any timeline below to inspect the complete chapter and"
      " micro-topic breakdown."
  )

  for block in schedule:
    time_label = block.get("time_block", "Phase")
    subj_label = block.get("subject_focus", "Focus")
    subtopic_data = block.get("detailed_subtopics", [])

    with st.expander(f"📌 **{time_label}**: {subj_label}"):
      if isinstance(subtopic_data, list) and len(subtopic_data) > 0:
        for item in subtopic_data:
          if isinstance(item, dict):
            subj = item.get("subject", "Subject")
            ch_name = item.get("chapter", "Chapter")
            st.markdown(f"#### 📘 [{subj}] {ch_name}")
            for sub in item.get("subtopics", []):
              st.write(f"  • {sub}")
            st.markdown("---")
      else:
        st.info("No explicit subtopics listed for this section.")

  st.divider()

  # PDF Download
  try:
    pdf_bytes = generate_roadmap_pdf(data, exam_name)
    st.download_button(
        label="📄 Download Complete Syllabus PDF Plan",
        data=pdf_bytes,
        file_name=f"{exam_name}_Official_Syllabus_Plan.pdf",
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
    "AI-powered preparation roadmaps and practice MCQs aligned with official"
    " textbooks."
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
    with st.spinner("Building your textbook-aligned roadmap..."):
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
### 🚀 Roadmap Features
1. **Syllabus Coverage**: Formatted specifically around official curriculum specs (PMDC, UET, NUST, etc.).
2. **Subtopic Deep Dive**: Expand each phase to inspect exact chapter mechanisms, concepts, and formulas.
3. **Universal PDF Export**: Fixed `fpdf` calls ensure smooth PDF generation across environments.
4. **Resilient AI Parsing**: Integrated `repair_json` prevents app crashes even if token limits cut text short.
""")
