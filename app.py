"""PawPal+ AI — premium Streamlit UI.

Design language inspired by 21st.dev / awwwards.com:
    - Fraunces variable serif for display, Inter for body
    - Warm earth palette: sage primary, terracotta accent, cream surface
    - Card-based layout with soft shadows, generous whitespace
    - Hero + stat row + tabbed organization
    - Mobile-friendly via Streamlit's responsive columns
"""

import os
import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

# ── Streamlit Cloud secrets bridge ────────────────────────────────────────────
# st.secrets (TOML on Streamlit Cloud) doesn't auto-populate os.environ. Bridge
# them at startup so rag_engine.py (which reads os.environ) just works.
try:
    for _key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
        if _key in st.secrets and not os.environ.get(_key):
            os.environ[_key] = st.secrets[_key]
except Exception:
    # Local dev with no secrets file — fine, .env covers us via python-dotenv.
    pass


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PawPal+ AI",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Custom CSS (premium typography + cards + spacing) ────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg: #FAF7F2;
  --surface: #FFFFFF;
  --primary: #2D5F3F;
  --primary-deep: #1F4A30;
  --primary-soft: #E8F0EA;
  --accent: #D97757;
  --accent-soft: #FCEEE6;
  --text: #1F2937;
  --muted: #6B7280;
  --border: #E5E7EB;
  --shadow-sm: 0 1px 3px rgba(31,41,55,0.04), 0 1px 2px rgba(31,41,55,0.06);
  --shadow-md: 0 4px 16px rgba(31,41,55,0.06), 0 2px 4px rgba(31,41,55,0.04);
  --shadow-lg: 0 16px 40px rgba(31,41,55,0.08), 0 4px 12px rgba(31,41,55,0.06);
  --radius: 18px;
  --radius-sm: 10px;
}

/* Body & app shell */
.stApp { background: var(--bg); }
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  color: var(--text);
}

/* Hide Streamlit chrome */
#MainMenu, header[data-testid="stHeader"], footer { visibility: hidden; height: 0; }
.stDeployButton { display: none; }
[data-testid="stToolbar"] { display: none; }

/* Block container — center, max-width, generous padding */
.block-container {
  max-width: 1100px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}

/* ── Hero ────────────────────────────────────────────────────────────────── */
.hero {
  text-align: center;
  padding: 56px 24px 40px;
  background: radial-gradient(ellipse at top, var(--primary-soft) 0%, transparent 65%);
  border-radius: 24px;
  margin-bottom: 32px;
}
.hero .eyebrow {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 6px 14px;
  border-radius: 100px;
  margin-bottom: 20px;
}
.hero h1 {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 500;
  font-size: clamp(2.4rem, 5.5vw, 4.2rem);
  letter-spacing: -0.025em;
  line-height: 1.05;
  color: var(--text);
  margin: 0 0 18px;
}
.hero h1 em {
  font-style: italic;
  font-weight: 400;
  color: var(--primary);
  font-family: 'Fraunces', Georgia, serif;
}
.hero .tagline {
  font-size: 1.13rem;
  color: var(--muted);
  max-width: 580px;
  margin: 0 auto;
  line-height: 1.6;
}
.hero .meta {
  margin-top: 28px;
  display: inline-flex;
  gap: 24px;
  flex-wrap: wrap;
  justify-content: center;
  font-size: 0.85rem;
  color: var(--muted);
}
.hero .meta span { display: inline-flex; align-items: center; gap: 6px; }
.hero .meta .dot { width: 6px; height: 6px; background: var(--primary); border-radius: 50%; }

/* ── Section headings ────────────────────────────────────────────────────── */
h2, h3, h4 {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 500;
  letter-spacing: -0.015em;
  color: var(--text);
}
.section-eyebrow {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--primary);
  margin-bottom: 6px;
}
.section-title {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.85rem;
  font-weight: 500;
  letter-spacing: -0.02em;
  color: var(--text);
  margin: 0 0 8px;
}
.section-sub {
  color: var(--muted);
  font-size: 0.98rem;
  margin: 0 0 24px;
}

/* ── Cards (st.container(border=True) targets) ───────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 28px !important;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  box-shadow: var(--shadow-md);
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button, .stFormSubmitButton > button {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 11px 22px;
  font-weight: 500;
  font-size: 0.95rem;
  font-family: 'Inter', sans-serif;
  transition: all 0.18s ease;
  box-shadow: var(--shadow-sm);
  letter-spacing: 0.01em;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  background: var(--primary-deep);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
  color: white;
}
.stButton > button:active, .stFormSubmitButton > button:active {
  transform: translateY(0);
}

/* Secondary buttons (those marked type="secondary") */
.stButton > button[kind="secondary"] {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  box-shadow: none;
}
.stButton > button[kind="secondary"]:hover {
  background: var(--bg);
  border-color: var(--primary);
  color: var(--primary);
}

/* Primary CTA */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-deep) 100%);
  font-weight: 600;
  padding: 13px 28px;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea textarea {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border) !important;
  padding: 10px 14px !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.95rem !important;
  transition: border 0.18s, box-shadow 0.18s;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--primary-soft) !important;
}

/* Selectbox */
.stSelectbox > div > div {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border) !important;
}

/* Labels */
.stTextInput label, .stNumberInput label, .stSelectbox label, .stTextArea label {
  font-weight: 500 !important;
  font-size: 0.88rem !important;
  color: var(--text) !important;
}

/* ── Metrics (stat cards) ────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--surface);
  padding: 22px 26px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] {
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Fraunces', Georgia, serif !important;
  font-size: 2.2rem !important;
  font-weight: 500 !important;
  color: var(--primary) !important;
  letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] {
  font-size: 0.78rem !important;
  font-weight: 500 !important;
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  background: var(--surface);
  padding: 6px;
  border-radius: 14px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  font-size: 0.95rem;
  border-radius: 10px;
  padding: 10px 22px;
  color: var(--muted);
  background: transparent;
  transition: all 0.18s;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text); }
.stTabs [aria-selected="true"] {
  background: var(--primary) !important;
  color: white !important;
  box-shadow: var(--shadow-sm);
}

/* ── Tables ──────────────────────────────────────────────────────────────── */
[data-testid="stTable"] table, .stTable table {
  border-collapse: separate;
  border-spacing: 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  font-size: 0.92rem;
}
[data-testid="stTable"] thead th {
  background: var(--primary-soft);
  color: var(--primary) !important;
  font-weight: 600 !important;
  font-size: 0.78rem !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  padding: 12px 16px !important;
  border: none !important;
}
[data-testid="stTable"] tbody td {
  padding: 12px 16px !important;
  border-bottom: 1px solid var(--border) !important;
  background: var(--surface) !important;
}
[data-testid="stTable"] tbody tr:hover td { background: var(--bg) !important; }

/* ── Expanders ───────────────────────────────────────────────────────────── */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {
  background: var(--surface);
  border-radius: 12px;
  font-weight: 500;
  border: 1px solid var(--border);
  padding: 12px 16px !important;
}
[data-testid="stExpander"] {
  border-radius: 12px;
  border: 1px solid var(--border) !important;
  background: var(--surface);
  margin-bottom: 8px;
}

/* ── Alerts (info / success / warning / error) ───────────────────────────── */
.stAlert {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border) !important;
  padding: 14px 18px !important;
  font-size: 0.93rem;
}
.stAlert[data-baseweb="notification"] {
  background: var(--surface) !important;
}

/* ── Progress bar ────────────────────────────────────────────────────────── */
.stProgress > div > div > div > div {
  background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
  border-radius: 100px;
}

/* ── Dividers ────────────────────────────────────────────────────────────── */
hr { border-color: var(--border); margin: 2.5rem 0 !important; }

/* ── Footer brand ────────────────────────────────────────────────────────── */
.footer {
  text-align: center;
  padding: 48px 0 16px;
  color: var(--muted);
  font-size: 0.85rem;
}
.footer .brand {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 500;
  color: var(--text);
  font-size: 1rem;
}

/* ── Mobile ──────────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .hero { padding: 36px 16px 28px; }
  .hero h1 { font-size: 2.2rem; }
  [data-testid="stVerticalBlockBorderWrapper"] { padding: 20px !important; }
  .stTabs [data-baseweb="tab"] { padding: 8px 14px; font-size: 0.88rem; }
}
</style>
""", unsafe_allow_html=True)


# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <span class="eyebrow">PawPal+ AI · Module 5 Final</span>
  <h1>Care that <em>thinks</em> with you,<br/>not for you.</h1>
  <p class="tagline">
    A retrieval-augmented pet care assistant. Schedules grounded in 33 curated guides,
    constraint-validated against your calendar, and ranked with a transparent confidence score.
  </p>
  <div class="meta">
    <span><span class="dot"></span> Local ChromaDB</span>
    <span><span class="dot"></span> MiniLM embeddings</span>
    <span><span class="dot"></span> Gemini · Claude · Template fallback</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None
if "show_schedule" not in st.session_state:
    st.session_state.show_schedule = False


# ── Helpers ──────────────────────────────────────────────────────────────────
def _busy_times_to_text(busy_times):
    return ", ".join(f"{s}-{e}" for s, e in busy_times) if busy_times else ""


def _parse_busy_times(text):
    out = []
    if not text:
        return out
    for chunk in text.split(","):
        chunk = chunk.strip()
        if "-" not in chunk:
            continue
        start, _, end = chunk.partition("-")
        out.append((start.strip(), end.strip()))
    return out


def _section_header(eyebrow: str, title: str, sub: str = ""):
    st.markdown(
        f'<div class="section-eyebrow">{eyebrow}</div>'
        f'<div class="section-title">{title}</div>'
        + (f'<div class="section-sub">{sub}</div>' if sub else ""),
        unsafe_allow_html=True,
    )


# ── Owner setup (always visible until owner is created) ──────────────────────
_existing = st.session_state.owner

if _existing is None:
    _section_header("01 · Get started", "Tell us about you", "We'll use your busy hours when the AI plans your day.")
    with st.container(border=True):
        with st.form("owner_form_init"):
            c1, c2 = st.columns(2)
            with c1:
                owner_name = st.text_input("Your name", value="Jordan")
                contact = st.text_input("Contact (optional)", value="")
            with c2:
                busy_text = st.text_input(
                    "Busy hours",
                    value="09:00-17:00",
                    help="Format: HH:MM-HH:MM, comma-separated. Example: 09:00-17:00, 19:00-20:00",
                )
            if st.form_submit_button("Save and continue") and owner_name:
                st.session_state.owner = Owner(
                    name=owner_name,
                    contact_info=contact,
                    busy_times=_parse_busy_times(busy_text),
                )
                st.session_state.show_schedule = False
                st.rerun()
    st.stop()


owner: Owner = st.session_state.owner


# ── Stat row ─────────────────────────────────────────────────────────────────
sched = Scheduler(owner)
done, total = sched.completion_progress()
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Pets in your care", len(owner.pets))
with m2:
    st.metric("Tasks today", total, f"{done} done" if total else None)
with m3:
    st.metric("Owner", owner.name)


st.write("")  # spacer


# ── Tabbed sections ──────────────────────────────────────────────────────────
tab_setup, tab_schedule, tab_ai = st.tabs(["Setup", "Today's schedule", "AI recommendations"])


# ─── TAB 1: SETUP ────────────────────────────────────────────────────────────
with tab_setup:
    # Owner edit
    _section_header("Profile", "Owner")
    with st.container(border=True):
        with st.form("owner_form_edit"):
            c1, c2, c3 = st.columns(3)
            with c1:
                owner_name = st.text_input("Name", value=owner.name)
            with c2:
                contact = st.text_input("Contact", value=owner.contact_info)
            with c3:
                busy_text = st.text_input(
                    "Busy hours",
                    value=_busy_times_to_text(owner.busy_times),
                    help="HH:MM-HH:MM, comma-separated",
                )
            if st.form_submit_button("Save changes"):
                owner.name = owner_name
                owner.contact_info = contact
                owner.busy_times = _parse_busy_times(busy_text)
                st.success("Saved.")

    # Pets
    _section_header("Roster", "Your pets", "Add and manage the animals in your care.")

    with st.container(border=True):
        with st.form("pet_form"):
            c1, c2, c3 = st.columns([1.5, 1, 1])
            with c1:
                pet_name = st.text_input("Pet name", value="Mochi")
            with c2:
                species = st.selectbox("Species", ["dog", "cat", "other"])
            with c3:
                age = st.number_input("Age", min_value=0, max_value=30, value=2)
            c4, c5 = st.columns([1, 2])
            with c4:
                energy = st.selectbox("Energy", ["low", "medium", "high"], index=1)
            with c5:
                health_notes = st.text_input("Health notes (optional)", value="",
                                             help="e.g. 'senior, mild arthritis'")
            if st.form_submit_button("Add pet") and pet_name:
                owner.add_pet(Pet(
                    name=pet_name, species=species, age=int(age),
                    energy=energy, health_notes=health_notes,
                ))
                st.success(f"Added {pet_name} the {species}.")

    if owner.pets:
        with st.expander(f"Manage existing pets ({len(owner.pets)})"):
            pet_to_manage = st.selectbox(
                "Select a pet", [p.name for p in owner.pets], key="manage_pet_sel",
            )
            pet_obj = next(p for p in owner.pets if p.name == pet_to_manage)

            with st.form("edit_pet_form"):
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    new_name = st.text_input("Name", value=pet_obj.name)
                with ec2:
                    new_species = st.selectbox(
                        "Species", ["dog", "cat", "other"],
                        index=["dog", "cat", "other"].index(pet_obj.species),
                    )
                with ec3:
                    new_age = st.number_input("Age", min_value=0, max_value=30, value=pet_obj.age)
                ec4, ec5 = st.columns([1, 2])
                with ec4:
                    new_energy = st.selectbox(
                        "Energy", ["low", "medium", "high"],
                        index=["low", "medium", "high"].index(getattr(pet_obj, "energy", "medium")),
                    )
                with ec5:
                    new_health = st.text_input("Health notes",
                                               value=getattr(pet_obj, "health_notes", ""))
                if st.form_submit_button("Save changes"):
                    pet_obj.name = new_name
                    pet_obj.species = new_species
                    pet_obj.age = int(new_age)
                    pet_obj.energy = new_energy
                    pet_obj.health_notes = new_health
                    st.success(f"Updated {new_name}.")

            if st.button(f"Delete {pet_to_manage}", type="secondary", key="del_pet_btn"):
                owner.remove_pet(pet_obj)
                st.session_state.show_schedule = False
                st.warning(f"{pet_to_manage} removed.")
                st.rerun()
    else:
        st.info("No pets yet — add one above.")

    # Add task
    _section_header("Plan", "Schedule a task")
    with st.container(border=True):
        if not owner.pets:
            st.info("Add a pet before scheduling tasks.")
        else:
            with st.form("task_form"):
                c1, c2 = st.columns(2)
                with c1:
                    task_title = st.text_input("Task title", value="Morning walk")
                    task_time = st.text_input("Time (HH:MM)", value="08:00")
                    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
                with c2:
                    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
                    frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
                    target_pet = st.selectbox("Assign to", [p.name for p in owner.pets])
                if st.form_submit_button("Add task") and task_title:
                    task = Task(
                        title=task_title, time=task_time,
                        duration_minutes=int(duration), priority=priority, frequency=frequency,
                    )
                    next(p for p in owner.pets if p.name == target_pet).add_task(task)
                    st.session_state.show_schedule = False
                    st.success(f"'{task_title}' added to {target_pet}.")


# ─── TAB 2: TODAY'S SCHEDULE ─────────────────────────────────────────────────
with tab_schedule:
    _section_header("Today", "Your schedule",
                    "Sorted by time across all pets, with conflict detection.")

    if not owner.pets:
        st.info("Add a pet on the Setup tab to see your schedule.")
    else:
        scheduler = Scheduler(owner)
        pairs = scheduler.get_tasks_with_pets()

        if not pairs:
            with st.container(border=True):
                st.info("No tasks yet. Add some on the Setup tab — or generate them with the AI tab.")
        else:
            with st.container(border=True):
                # Filters
                fcol1, fcol2 = st.columns(2)
                with fcol1:
                    pet_filter = st.selectbox(
                        "Filter by pet", ["All"] + [p.name for p in owner.pets], key="pet_filter",
                    )
                with fcol2:
                    status_filter = st.selectbox(
                        "Status", ["All", "Pending", "Completed"], key="status_filter",
                    )

                filtered = pairs
                if pet_filter != "All":
                    filtered = [(t, pn) for t, pn in filtered if pn == pet_filter]
                if status_filter == "Pending":
                    filtered = [(t, pn) for t, pn in filtered if not t.completed]
                elif status_filter == "Completed":
                    filtered = [(t, pn) for t, pn in filtered if t.completed]

                # Progress
                done, total = scheduler.completion_progress()
                st.progress(done / total if total else 0,
                            text=f"{done} / {total} tasks completed today")

                # Conflict warnings
                for c in scheduler.detect_conflicts():
                    st.warning(c)

                # Schedule table
                if filtered:
                    rows = [
                        {
                            "Time":     t.time,
                            "Pet":      pn,
                            "Task":     t.title,
                            "Duration": f"{t.duration_minutes} min",
                            "Priority": t.priority,
                            "Frequency": t.frequency,
                            "Status":   "Done" if t.completed else "Pending",
                        }
                        for t, pn in filtered
                    ]
                    st.table(rows)
                else:
                    st.info("No tasks match the current filters.")

            # Actions
            with st.container(border=True):
                _section_header("Actions", "Manage tasks")
                all_task_pairs = scheduler.get_tasks_with_pets()

                def _label(task, pet_name):
                    return f"{task.time} — {task.title} ({pet_name})"

                acol1, acol2 = st.columns(2)
                with acol1:
                    st.markdown("**Mark complete**")
                    incomplete = [(t, pn) for t, pn in all_task_pairs if not t.completed]
                    if incomplete:
                        chosen_complete = st.selectbox(
                            "Task", [_label(t, pn) for t, pn in incomplete],
                            key="complete_sel", label_visibility="collapsed",
                        )
                        if st.button("Complete", key="btn_complete"):
                            for t, pn in incomplete:
                                if _label(t, pn) == chosen_complete:
                                    t.mark_complete()
                                    break
                            st.rerun()
                    else:
                        st.success("All tasks done.")

                with acol2:
                    st.markdown("**Delete a task**")
                    if all_task_pairs:
                        chosen_delete = st.selectbox(
                            "Task", [_label(t, pn) for t, pn in all_task_pairs],
                            key="delete_sel", label_visibility="collapsed",
                        )
                        if st.button("Delete", type="secondary", key="btn_delete"):
                            for t, pn in all_task_pairs:
                                if _label(t, pn) == chosen_delete:
                                    scheduler.delete_task(t)
                                    break
                            st.rerun()
                    else:
                        st.info("No tasks to delete.")


# ─── TAB 3: AI RECOMMENDATIONS ───────────────────────────────────────────────
with tab_ai:
    _section_header(
        "RAG · grounded",
        "AI-powered schedule",
        "ChromaDB retrieves the most relevant care guides, then an LLM "
        "generates a constraint-aware plan. Advisory only.",
    )

    if not owner.pets:
        with st.container(border=True):
            st.info("Add a pet on the Setup tab to enable AI recommendations.")
    else:
        with st.container(border=True):
            target_pet_name = st.selectbox(
                "Generate AI schedule for",
                [p.name for p in owner.pets],
                key="ai_target_pet",
            )

            if st.button("Generate AI schedule", type="primary"):
                with st.spinner("Indexing knowledge base, retrieving context, generating..."):
                    try:
                        from rag.rag_engine import RAGEngine
                        from rag.vector_store import ChromaStore
                        from recommender.ranker import apply_recommendation

                        store = ChromaStore()
                        store.ingest_knowledge_base()
                        engine = RAGEngine(store=store)
                        pet_obj = next(p for p in owner.pets if p.name == target_pet_name)
                        rec = engine.generate(owner, pet_obj, k=5)
                        result = apply_recommendation(
                            rec,
                            busy_times=owner.busy_times,
                            existing_tasks=pet_obj.tasks,
                        )
                        st.session_state["last_ai_result"] = result
                        st.session_state["last_ai_rec"] = rec
                    except Exception as e:
                        st.error(f"AI generation failed: {e}")
                        st.info("Run `pip install -r requirements.txt` and restart.")

        result = st.session_state.get("last_ai_result")
        rec = st.session_state.get("last_ai_rec")

        if result and rec:
            # Top-line metrics
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.metric("Confidence",
                          f"{result['confidence']:.2f}",
                          result["confidence_label"].upper())
            with cc2:
                provider = (rec.provider or "template").capitalize()
                st.metric("Provider", provider if result["used_llm"] else "Template")
            with cc3:
                kept = len(result["kept"])
                total_proposed = kept + len(result["dropped"])
                st.metric("Slots kept", f"{kept} / {total_proposed}")

            # Explanation
            if result["explanation"]:
                with st.container(border=True):
                    st.markdown(f"**AI's reasoning** — {result['explanation']}")

            # Schedule table
            if result["ranked"]:
                with st.container(border=True):
                    st.markdown("**Recommended schedule** · constraint-validated, score-ranked")
                    rows = [
                        {
                            "Time":     s.get("time", "—"),
                            "Task":     s.get("title", "—"),
                            "Duration": f"{s.get('duration_minutes', 15)} min",
                            "Priority": s.get("priority", "medium"),
                            "Score":    f"{s.get('score', 0.0):.2f}",
                            "Shifted":  "yes" if s.get("shifted") else "",
                            "Rationale": (s.get("rationale", "") or "")[:80],
                        }
                        for s in result["ranked"]
                    ]
                    st.table(rows)

                    if st.button(f"Add all kept tasks to {target_pet_name}",
                                 type="primary", key="btn_add_all"):
                        pet_obj = next(p for p in owner.pets if p.name == target_pet_name)
                        for s in result["kept"]:
                            pet_obj.add_task(Task(
                                title=s.get("title", "AI task"),
                                time=s.get("time", "12:00"),
                                duration_minutes=int(s.get("duration_minutes", 15)),
                                priority=s.get("priority", "medium"),
                                description=s.get("rationale", ""),
                                frequency="daily",
                            ))
                        st.success(f"Added {len(result['kept'])} tasks to {target_pet_name}.")
                        st.rerun()

            # Dropped
            if result["dropped"]:
                with st.expander(f"Dropped slots ({len(result['dropped'])})"):
                    for d in result["dropped"]:
                        reason = d.get("drop_reason", "unknown")
                        st.warning(f"{d.get('time', '?')} — {d.get('title', '?')} ({reason})")

            # Citations
            if result["citations"]:
                with st.expander(f"Sources used ({len(result['citations'])})"):
                    for c in result["citations"]:
                        st.markdown(f"- `{c}`")

            # Confidence guidance
            if result["confidence_label"] == "low":
                st.warning(
                    "Low confidence — the retrieval signal was weak. "
                    "Add richer health notes or check your busy hours.",
                )


# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
  <div class="brand">PawPal+ AI</div>
  <div>Module 5 final · Applied AI System · Advisory only — not a substitute for veterinary care.</div>
</div>
""", unsafe_allow_html=True)
