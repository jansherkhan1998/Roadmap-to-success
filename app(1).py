from datetime import date
import json
import os
from google import genai
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Pakistani Entrance Test Preparation Roadmap",
    page_icon="📚",
    layout="wide",
)

st.title("📚 AI Entrance Test Preparation Roadmap")
st.write(
    "Generate a personalized preparation roadmap for Pakistani university,"
    " medical, engineering, defence, and aptitude entrance tests."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def get_gemini_api_key():
  """Retrieve API key from Streamlit secrets, environment variables, or session state."""
  if "api_key" in st.session_state and st.session_state["api_key"]:
    return st.session_state["api_key"]

  try:
    if "GEMINI_API_KEY" in st.secrets:
      return st.secrets["GEMINI_API_KEY"]
  except Exception:
    pass

  return os.getenv("GEMINI_API_KEY", "")


def build_roadmap_prompt(
    test_name, exam_date, days_remaining, level, hours_per_day
):
  return f"""
You are an expert Pakistani entrance-test preparation strategist, academic planner, and curriculum specialist.

Create a practical personalized preparation roadmap for:

Target Test: {test_name}
Target Exam Date: {exam_date}
Days Remaining: {days_remaining}
Current Preparation Level: {level}
Daily Available Study Hours: {hours_per_day}

The student is preparing in Pakistan. Tailor the roadmap to commonly relevant Pakistani education and entrance-test patterns, including PMDC/medical tests, NUMS where applicable, HEC-related aptitude patterns, provincial boards, FSc/A-Level preparation, engineering entrance tests, and computer-based testing.

Do not invent an official syllabus. If the exact pattern can vary by institution or year, clearly state that.

Include:
1. Executive summary
2. Exam structure and common sections
3. High-yield subjects and topics in a table
4. Phase-wise plan:
   - Phase 1: Syllabus Coverage / Concept Building
   - Phase 2: Revision / Weak Area Improvement
   - Phase 3: Mock Practice / Exam Simulation
5. Day-by-day roadmap. For long periods, organize it into weekly blocks while providing a detailed repeatable daily template.
6. Daily study schedule based on {hours_per_day} hours
7. MCQ and mock-test strategy
8. Time-management strategy
9. Negative-marking strategy only if applicable
10. Computer-based-test strategy where relevant
11. Weekly performance tracking table
12. Final 7-day strategy
13. Exam-day strategy
14. Top 10 personalized priorities
15. Five common mistakes to avoid
16. Five measurable preparation targets

Make the workload realistic. Adapt the balance according to level:
Beginner = more concepts,
Intermediate = balanced concepts/revision/practice,
Advanced = more testing, speed, revision, and weak-area correction.

Use clear Markdown, headings, tables, and bullet points. Avoid vague advice. Give measurable targets.
Today's date is {date.today()}.
"""


def build_mcq_prompt(test_name, phase_name, subject, count=5):
  return f"""
Generate {count} high-yield multiple choice questions (MCQs) for Pakistani entrance test preparation.

Target Exam: {test_name}
Study Phase: {phase_name}
Subject: {subject}

Return ONLY valid JSON with this exact structure:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text here?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "answer": "A) Option 1",
      "explanation": "Brief explanation of why this answer is correct."
    }}
  ]
}}
"""


# ============================================================
# SIDEBAR CONFIGURATION
# ============================================================

with st.sidebar:
  st.header("⚙️ Preparation Settings")

  target_test = st.selectbox(
      "Target Test",
      [
          "MDCAT",
          "ECAT / Engineering Tests",
          "ISSB Initial Computer Test",
          "Army Medical College (AMC) Test",
          "NUST NET",
          "FAST",
          "NTS NAT",
          "Custom / Other Entrance Test",
      ],
  )

  custom_test = ""
  if target_test == "Custom / Other Entrance Test":
    custom_test = st.text_input(
        "Enter Test Name", placeholder="e.g., GIKI, PIEAS, UET Taxila"
    )

  target_date = st.date_input("Target Exam Date", min_value=date.today())

  preparation_level = st.selectbox(
      "Current Preparation Level", ["Beginner", "Intermediate", "Advanced"]
  )

  study_hours = st.slider(
      "Daily Available Study Hours", min_value=1, max_value=16, value=6
  )

  st.divider()
  st.header("🔑 Gemini API Settings")

  auto_key = get_gemini_api_key()
  if auto_key:
    st.success("✅ API Key automatically loaded from system.")
    api_key_input = auto_key
  else:
    api_key_input = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Enter your Gemini API key",
    )
    if api_key_input:
      st.session_state["api_key"] = api_key_input.strip()

  generate_button = st.button(
      "🚀 Generate Roadmap", type="primary", use_container_width=True
  )

# ============================================================
# METRICS & CALCULATIONS
# ============================================================

today = date.today()
remaining_days = (target_date - today).days

selected_test = (
    custom_test.strip()
    if target_test == "Custom / Other Entrance Test"
    else target_test
)

col1, col2, col3 = st.columns(3)
with col1:
  st.metric("Days Remaining", max(remaining_days, 0))
with col2:
  st.metric("Study Hours / Day", study_hours)
with col3:
  st.metric("Preparation Level", preparation_level)

# ============================================================
# GENERATION LOGIC
# ============================================================

if generate_button:
  current_key = get_gemini_api_key()

  if not current_key:
    st.error(
        "❌ No Gemini API key found. Please enter it in the sidebar or add it"
        " to Streamlit secrets."
    )
    st.stop()

  if target_date <= today:
    st.error("❌ Please select a future exam date.")
    st.stop()

  if target_test == "Custom / Other Entrance Test" and not custom_test.strip():
    st.error("❌ Please enter your custom test name.")
    st.stop()

  try:
    with st.spinner("🤖 Generating your personalized roadmap..."):
      client = genai.Client(api_key=current_key)

      response = client.models.generate_content(
          model="gemini-3.5-flash",
          contents=build_roadmap_prompt(
              selected_test,
              target_date.strftime("%d %B %Y"),
              remaining_days,
              preparation_level,
              study_hours,
          ),
      )

      roadmap = response.text

    if not roadmap:
      st.error("❌ Gemini returned an empty response.")
      st.stop()

    st.session_state["roadmap"] = roadmap
    st.session_state["test"] = selected_test
    st.session_state["exam_date"] = target_date.strftime("%d %B %Y")
    st.session_state.pop("phase_mcqs", None)  # Reset MCQs on new roadmap

  except Exception as error:
    st.error("❌ Unable to generate the roadmap.")
    st.warning(
        "Check your Gemini API key, internet connection, model availability,"
        " and try again."
    )
    with st.expander("Technical error"):
      st.code(str(error))

# ============================================================
# MAIN CONTENT TABS
# ============================================================

if "roadmap" in st.session_state:
  st.success(
      f"Roadmap ready for {st.session_state['test']} — Exam Date:"
      f" {st.session_state['exam_date']}"
  )

  tab1, tab2 = st.tabs(["🗺️ Preparation Roadmap", "📝 Phase Practice MCQs"])

  with tab1:
    st.markdown(st.session_state["roadmap"])

    st.divider()
    st.subheader("📥 Download Roadmap")

    markdown_data = (
        "# AI Entrance Test Preparation Roadmap\n\n"
        f"**Test:** {st.session_state['test']}\n\n"
        f"**Exam Date:** {st.session_state['exam_date']}\n\n"
        "---\n\n" + st.session_state["roadmap"]
    )

    text_data = (
        "AI Entrance Test Preparation Roadmap\n"
        "=====================================\n\n"
        f"Test: {st.session_state['test']}\n"
        f"Exam Date: {st.session_state['exam_date']}\n\n"
        + st.session_state["roadmap"]
    )

    col1, col2 = st.columns(2)
    with col1:
      st.download_button(
          "📄 Download Markdown",
          markdown_data,
          "entrance_test_roadmap.md",
          "text/markdown",
          use_container_width=True,
      )
    with col2:
      st.download_button(
          "📝 Download Text",
          text_data,
          "entrance_test_roadmap.txt",
          "text/plain",
          use_container_width=True,
      )

  with tab2:
    st.subheader("🎯 Phase-Based Practice Quiz")
    st.write(
        "Test your knowledge for specific phases and subjects in your roadmap."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
      selected_phase = st.selectbox(
          "Select Preparation Phase",
          [
              "Phase 1: Syllabus Coverage & Concepts",
              "Phase 2: Revision & Weak Areas",
              "Phase 3: Mock Exams & Speed",
          ],
      )
    with col2:
      quiz_subject = st.text_input(
          "Subject / Topic", placeholder="e.g. Physics - Vectors"
      )
    with col3:
      mcq_count = st.select_slider("Number of Questions", options=[3, 5, 10])

    if st.button(
        "⚡ Generate Phase MCQs", type="primary", use_container_width=True
    ):
      if not quiz_subject.strip():
        st.error("Please specify a subject or topic for the quiz.")
      else:
        current_key = get_gemini_api_key()
        try:
          with st.spinner("Generating quiz questions..."):
            client = genai.Client(api_key=current_key)
            mcq_res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=build_mcq_prompt(
                    st.session_state["test"],
                    selected_phase,
                    quiz_subject,
                    mcq_count,
                ),
            )
            # Standard cleanup for potential code blocks
            clean_json = mcq_res.text.strip()
            if clean_json.startswith("```"):
              clean_json = clean_json.split("\n", 1)[1].rsplit("\n", 1)[0]
            st.session_state["phase_mcqs"] = json.loads(clean_json).get(
                "questions", []
            )
        except Exception as e:
          st.error(f"Failed to generate quiz: {e}")

    # Interactive Quiz Engine
    if "phase_mcqs" in st.session_state and st.session_state["phase_mcqs"]:
      st.divider()
      questions = st.session_state["phase_mcqs"]

      with st.form("quiz_form"):
        user_answers = {}
        for idx, q in enumerate(questions):
          st.markdown(f"**Q{idx+1}: {q['question']}**")
          user_answers[idx] = st.radio(
              "Options:",
              q["options"],
              key=f"q_{idx}",
              index=None,
              label_visibility="collapsed",
          )
          st.write("")

        submitted = st.form_submit_button("Submit Quiz")

      if submitted:
        score = 0
        st.divider()
        st.subheader("📊 Quiz Results")

        for idx, q in enumerate(questions):
          selected = user_answers.get(idx)
          correct = q["answer"]

          if selected == correct:
            score += 1
            st.success(f"**Q{idx+1}**: Correct! ({correct})")
          else:
            st.error(
                f"**Q{idx+1}**: Incorrect. You chose '{selected or 'None'}'. "
                f"Correct Answer: **{correct}**"
            )

          st.caption(f"💡 Explanation: {q['explanation']}")
          st.write("---")

        st.info(f"**Final Score:** {score} / {len(questions)}")

else:
  st.info(
      "👈 Configure your settings in the sidebar and click **Generate"
      " Roadmap**."
  )
