import streamlit as st
from google import genai
from datetime import date

st.set_page_config(
    page_title="Pakistani Entrance Test Preparation Roadmap",
    page_icon="📚",
    layout="wide"
)

st.title("📚 AI Entrance Test Preparation Roadmap")
st.write(
    "Generate a personalized preparation roadmap for Pakistani "
    "university, medical, engineering, defence and aptitude entrance tests."
)

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
            "Custom / Other Entrance Test"
        ]
    )

    custom_test = ""
    if target_test == "Custom / Other Entrance Test":
        custom_test = st.text_input(
            "Enter Test Name",
            placeholder="e.g., GIKI, PIEAS, UET Taxila"
        )

    target_date = st.date_input(
        "Target Exam Date",
        min_value=date.today()
    )

    preparation_level = st.selectbox(
        "Current Preparation Level",
        ["Beginner", "Intermediate", "Advanced"]
    )

    study_hours = st.slider(
        "Daily Available Study Hours",
        min_value=1,
        max_value=16,
        value=6
    )

    st.divider()
    st.header("🔑 Gemini API")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Enter your Gemini API key"
    )

    generate_button = st.button(
        "🚀 Generate Roadmap",
        type="primary",
        use_container_width=True
    )

today = date.today()
remaining_days = (target_date - today).days

if target_test == "Custom / Other Entrance Test":
    selected_test = custom_test.strip()
else:
    selected_test = target_test

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Days Remaining", max(remaining_days, 0))

with col2:
    st.metric("Study Hours / Day", study_hours)

with col3:
    st.metric("Preparation Level", preparation_level)

def build_prompt(test_name, exam_date, days_remaining, level, hours_per_day):
    return f"""
You are an expert Pakistani entrance-test preparation strategist,
academic planner, and curriculum specialist.

Create a practical personalized preparation roadmap for:

Target Test: {test_name}
Target Exam Date: {exam_date}
Days Remaining: {days_remaining}
Current Preparation Level: {level}
Daily Available Study Hours: {hours_per_day}

The student is preparing in Pakistan. Tailor the roadmap to commonly
relevant Pakistani education and entrance-test patterns, including
PMDC/medical tests, NUMS where applicable, HEC-related aptitude
patterns, provincial boards, FSc/A-Level preparation, engineering
entrance tests, and computer-based testing.

Do not invent an official syllabus. If the exact pattern can vary by
institution or year, clearly state that.

Include:

1. Executive summary
2. Exam structure and common sections
3. High-yield subjects and topics in a table
4. Phase-wise plan:
   - Syllabus Coverage / Concept Building
   - Revision / Weak Area Improvement
   - Mock Practice / Exam Simulation
5. Day-by-day roadmap. For very long periods, organize it into
   weekly blocks while providing a detailed repeatable daily template.
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
Advanced = more testing, speed, revision and weak-area correction.

Use clear Markdown, headings, tables and bullet points.
Avoid vague advice. Give measurable targets.
Today's date is {today}.
"""

if generate_button:
    if not api_key.strip():
        st.error("❌ Please enter your Gemini API key.")
        st.stop()

    if target_date <= today:
        st.error("❌ Please select a future exam date.")
        st.stop()

    if target_test == "Custom / Other Entrance Test" and not custom_test.strip():
        st.error("❌ Please enter your custom test name.")
        st.stop()

    try:
        with st.spinner("🤖 Generating your personalized roadmap..."):
            client = genai.Client(api_key=api_key.strip())

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=build_prompt(
                    selected_test,
                    target_date.strftime("%d %B %Y"),
                    remaining_days,
                    preparation_level,
                    study_hours
                )
            )

            roadmap = response.text

        if not roadmap:
            st.error("❌ Gemini returned an empty response.")
            st.stop()

        st.session_state["roadmap"] = roadmap
        st.session_state["test"] = selected_test
        st.session_state["exam_date"] = target_date.strftime("%d %B %Y")

    except Exception as error:
        st.error("❌ Unable to generate the roadmap.")
        st.warning(
            "Check your Gemini API key, internet connection, "
            "model availability, and try again."
        )
        with st.expander("Technical error"):
            st.code(str(error))

if "roadmap" in st.session_state:
    st.success(
        f"Roadmap generated for {st.session_state['test']} — "
        f"Exam Date: {st.session_state['exam_date']}"
    )

    st.subheader("🗺️ Your Personalized Roadmap")
    st.markdown(st.session_state["roadmap"])

    st.divider()
    st.subheader("📥 Download Roadmap")

    markdown_data = (
        "# AI Entrance Test Preparation Roadmap\n\n"
        f"**Test:** {st.session_state['test']}\n\n"
        f"**Exam Date:** {st.session_state['exam_date']}\n\n"
        "---\n\n"
        + st.session_state["roadmap"]
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
            use_container_width=True
        )

    with col2:
        st.download_button(
            "📝 Download Text",
            text_data,
            "entrance_test_roadmap.txt",
            "text/plain",
            use_container_width=True
        )
else:
    st.info(
        "👈 Configure the settings in the sidebar and click "
        "**Generate Roadmap**."
    )
