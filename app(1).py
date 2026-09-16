import os
import json
from datetime import date

import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Roadmap to success",
    page_icon="📚",
    layout="wide"
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
    "Other / Custom Test"
]

LEVELS = [
    "Beginner",
    "Intermediate",
    "Advanced"
]

SUBJECTS = [
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "English",
    "IQ / Analytical Reasoning",
    "General Knowledge",
    "Mixed"
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

    return genai.Client(
        api_key=api_key
    )


def ask_gemini(prompt, json_mode=False):

    api_key = get_api_key()

    if not api_key:
        raise RuntimeError(
            "Gemini API key is missing. "
            "Add GEMINI_API_KEY to Streamlit Secrets."
        )

    client = get_client(api_key)

    config = types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json"
        if json_mode
        else "text/plain"
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=config
    )

    return response.text


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

    return json.loads(text)


# ============================================================
# ROADMAP PROMPT
# ============================================================

def roadmap_prompt(
    exam,
    exam_date,
    level,
    hours,
    focus
):

    days = max(
        1,
        (exam_date - date.today()).days
    )

    return f"""
You are an expert Pakistan entrance-test preparation planner.

Create a realistic, student-friendly preparation roadmap.

Exam:
{exam}

Exam Date:
{exam_date.isoformat()}

Days Remaining:
{days}

Student Level:
{level}

Available Study Hours Per Day:
{hours}

Priority / Focus:
{focus or "No special focus"}

IMPORTANT:

Do not invent official syllabus, dates,
eligibility rules, marks, or test patterns.

If an exam detail can vary by year or institution,
tell the student to verify it from the current
official authority.

Make the roadmap useful even if the exact
official syllabus is not supplied.

Adapt the plan according to the student's level.

The roadmap should include:

1. Foundation building
2. Concept development
3. Topic-wise practice
4. MCQ practice
5. Timed practice
6. Mock tests
7. Error-log review
8. Spaced revision
9. Weak-area improvement
10. Final revision
11. Exam-day strategy

Return ONLY valid JSON.

Use exactly this structure:

{{
    "summary": "string",

    "assumptions": [
        "string"
    ],

    "phases": [
        {{
            "phase": "string",
            "duration": "string",
            "objectives": "string",
            "daily_plan": "string",
            "topics": "string",
            "practice": "string",
            "revision": "string",
            "checkpoint": "string"
        }}
    ],

    "weekly_template": [
        "string"
    ],

    "final_week": [
        "string"
    ],

    "exam_day": [
        "string"
    ],

    "resources": [
        "string"
    ],

    "common_mistakes": [
        "string"
    ]
}}

Make the plan practical and progressively harder.
"""


# ============================================================
# MCQ PROMPT
# ============================================================

def mcq_prompt(
    exam,
    subject,
    difficulty,
    count,
    level
):

    return f"""
Create {count} original multiple-choice practice
questions for a Pakistani entrance-test preparation app.

Exam:
{exam}

Subject:
{subject}

Difficulty:
{difficulty}

Student Level:
{level}

These are practice questions.

Do NOT claim that these are official past-paper
questions.

Do not copy known copyrighted questions.

Avoid ambiguous wording.

Each question must have:

A
B
C
D

Exactly ONE correct answer.

Include a short educational explanation.

Return ONLY valid JSON.

Use exactly this structure:

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

The answer must be exactly one of:

A
B
C
D
"""


# ============================================================
# DISPLAY ROADMAP
# ============================================================

def show_roadmap(data):

    st.subheader("🗺️ Your AI Preparation Roadmap")

    st.info(
        data.get(
            "summary",
            ""
        )
    )

    if data.get("assumptions"):

        with st.expander(
            "Assumptions & Verification Notes"
        ):

            for item in data["assumptions"]:

                st.write(
                    "• " + item
                )

    for phase in data.get(
        "phases",
        []
    ):

        with st.expander(
            f"{phase.get('phase', 'Phase')} "
            f"— {phase.get('duration', '')}"
        ):

            st.markdown(
                f"**Objectives:** "
                f"{phase.get('objectives', '')}"
            )

            st.markdown(
                f"**Daily Plan:** "
                f"{phase.get('daily_plan', '')}"
            )

            st.markdown(
                f"**Topics:** "
                f"{phase.get('topics', '')}"
            )

            st.markdown(
                f"**Practice:** "
                f"{phase.get('practice', '')}"
            )

            st.markdown(
                f"**Revision:** "
                f"{phase.get('revision', '')}"
            )

            st.markdown(
                f"**Checkpoint:** "
                f"{phase.get('checkpoint', '')}"
            )

    if data.get("weekly_template"):

        st.subheader("📅 Weekly Template")

        for i, item in enumerate(
            data["weekly_template"],
            1
        ):

            st.write(
                f"**Day {i}:** {item}"
            )

    if data.get("final_week"):

        st.subheader("🔥 Final Week")

        for item in data["final_week"]:

            st.write(
                "• " + item
            )

    if data.get("exam_day"):

        st.subheader("🎯 Exam-Day Plan")

        for item in data["exam_day"]:

            st.write(
                "• " + item
            )

    if data.get("resources"):

        st.subheader("📚 Resource Guidance")

        for item in data["resources"]:

            st.write(
                "• " + item
            )

    if data.get("common_mistakes"):

        st.subheader("⚠️ Common Mistakes")

        for item in data["common_mistakes"]:

            st.write(
                "• " + item
            )


# ============================================================
# QUIZ ENGINE
# ============================================================

def run_quiz(questions):

    if (
        "quiz_answers" not in st.session_state
        or len(st.session_state.quiz_answers)
        != len(questions)
    ):

        st.session_state.quiz_answers = [
            None
            for _ in questions
        ]

    for i, question in enumerate(
        questions
    ):

        st.markdown(
            f"### Q{i + 1}. "
            f"{question['question']}"
        )

        answer = st.radio(
            "Select an answer",

            options=[
                "A",
                "B",
                "C",
                "D"
            ],

            format_func=lambda x,
            options=question["options"]:
                f"{x}. {options[x]}",

            key=f"question_{i}",

            index=None
        )

        st.session_state.quiz_answers[i] = answer

    if st.button(
        "Submit Test",
        type="primary"
    ):

        score = sum(
            answer == question["answer"]
            for answer, question
            in zip(
                st.session_state.quiz_answers,
                questions
            )
        )

        percentage = (
            score / len(questions)
        ) * 100

        st.success(
            f"Score: {score}/{len(questions)} "
            f"({percentage:.1f}%)"
        )

        st.subheader(
            "📊 Answer Review"
        )

        for i, question in enumerate(
            questions
        ):

            user_answer = (
                st.session_state.quiz_answers[i]
            )

            correct_answer = (
                question["answer"]
            )

            if user_answer == correct_answer:

                st.write(
                    f"✅ Q{i + 1}: Correct"
                )

            else:

                st.write(
                    f"❌ Q{i + 1}: "
                    f"Correct answer = "
                    f"**{correct_answer}**"
                )

                st.caption(
                    question["explanation"]
                )


# ============================================================
# HEADER
# ============================================================

st.title(
    "📚 PakPrep AI"
)

st.caption(
    "AI-powered preparation roadmaps "
    "and original practice MCQs for "
    "Pakistani entrance and aptitude tests."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "👨‍🎓 Student Profile"
    )

    exam = st.selectbox(
        "Select Test",
        EXAMS
    )

    custom_exam = st.text_input(
        "Custom Test Name",
        disabled=(
            exam != "Other / Custom Test"
        )
    )

    if (
        exam == "Other / Custom Test"
        and custom_exam.strip()
    ):

        exam_name = custom_exam.strip()

    else:

        exam_name = exam

    exam_date = st.date_input(
        "Target Test Date",
        min_value=date.today()
    )

    level = st.selectbox(
        "Preparation Level",
        LEVELS
    )

    hours = st.slider(
        "Study Hours Per Day",
        1,
        12,
        4
    )

    focus = st.text_input(
        "Special Focus",
        placeholder="e.g. Physics numericals"
    )

    st.divider()

    st.caption(
        "Always verify current syllabus, "
        "registration dates and official "
        "test rules from the relevant authority."
    )


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    [
        "🗺️ Preparation Roadmap",
        "📝 Practice MCQs",
        "ℹ️ How It Works"
    ]
)


# ============================================================
# ROADMAP TAB
# ============================================================

with tab1:

    days = max(
        0,
        (exam_date - date.today()).days
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Test",
        exam_name
    )

    col2.metric(
        "Days Remaining",
        days
    )

    col3.metric(
        "Level",
        level
    )

    if st.button(
        "🚀 Generate My Complete Roadmap",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "Building your personalized roadmap..."
        ):

            try:

                response = ask_gemini(
                    roadmap_prompt(
                        exam_name,
                        exam_date,
                        level,
                        hours,
                        focus
                    ),
                    json_mode=True
                )

                data = clean_json(
                    response
                )

                st.session_state.roadmap = data

            except Exception as error:

                st.error(
                    f"Could not generate roadmap: "
                    f"{error}"
                )

    if "roadmap" in st.session_state:

        show_roadmap(
            st.session_state.roadmap
        )


# ============================================================
# MCQ TAB
# ============================================================

with tab2:

    st.subheader(
        "📝 AI Practice Test Generator"
    )

    col1, col2, col3, col4 = st.columns(4)

    subject = col1.selectbox(
        "Subject",
        SUBJECTS
    )

    difficulty = col2.selectbox(
        "Difficulty",
        [
            "Easy",
            "Medium",
            "Hard",
            "Mixed"
        ]
    )

    count = col3.selectbox(
        "Number of Questions",
        [
            5,
            10,
            15,
            20
        ],
        index=1
    )

    quiz_level = col4.selectbox(
        "Student Level",
        LEVELS,
        key="quiz_level"
    )

    if st.button(
        "🎯 Generate New MCQ Test",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "Generating original practice questions..."
        ):

            try:

                response = ask_gemini(
                    mcq_prompt(
                        exam_name,
                        subject,
                        difficulty,
                        count,
                        quiz_level
                    ),
                    json_mode=True
                )

                data = clean_json(
                    response
                )

                questions = data.get(
                    "questions",
                    []
                )

                st.session_state.questions = (
                    questions
                )

                st.session_state.quiz_answers = [
                    None
                    for _ in questions
                ]

            except Exception as error:

                st.error(
                    f"Could not generate test: "
                    f"{error}"
                )

    if (
        "questions" in st.session_state
        and st.session_state.questions
    ):

        run_quiz(
            st.session_state.questions
        )


# ============================================================
# HOW IT WORKS
# ============================================================

with tab3:

    st.markdown(
        """
### 🚀 PakPrep AI Features

**1. Personalized Roadmap**

The student provides:

- Entrance test
- Target date
- Preparation level
- Daily study hours
- Weak area / focus

The AI then creates a customized preparation strategy.

---

**2. Progressive Preparation**

The roadmap can contain:

- Foundation
- Concept building
- Topic practice
- MCQs
- Timed practice
- Mock exams
- Error-log review
- Revision
- Final-week preparation
- Exam-day strategy

---

**3. AI Practice Tests**

Students can generate different tests based on:

- Subject
- Difficulty
- Number of questions
- Student level
- Selected entrance test

Each question contains:

- Four options
- Correct answer
- Explanation
- Topic

---

### ⚠️ Important

This application is an AI study assistant.

It should NOT be treated as an official source
for examination dates, syllabus, admission rules,
eligibility requirements, or official past papers.

Students should verify current information
from the relevant official testing or
admission authority.
"""
    )
