"""PawPal+ AI Streamlit UI — connects to pawpal_system.py backend + RAG layer."""

import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+ AI", page_icon="🐾", layout="centered")

st.title("PawPal+ AI")
st.caption("Smart pet care scheduling assistant — now with RAG-powered recommendations")

# ── Session state ─────────────────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None
if "show_schedule" not in st.session_state:
    st.session_state.show_schedule = False

# ── Owner setup ───────────────────────────────────────────────────────────────
_existing = st.session_state.owner

def _busy_times_to_text(busy_times):
    """[(\"09:00\", \"17:00\")] -> \"09:00-17:00\"."""
    return ", ".join(f"{s}-{e}" for s, e in busy_times) if busy_times else ""

def _parse_busy_times(text):
    """\"09:00-17:00, 19:00-20:00\" -> [(\"09:00\",\"17:00\"), (\"19:00\",\"20:00\")]."""
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

with st.expander("Owner Setup", expanded=_existing is None):
    with st.form("owner_form"):
        owner_name = st.text_input("Owner name", value=_existing.name if _existing else "Jordan")
        contact    = st.text_input("Contact info (optional)", value=_existing.contact_info if _existing else "")
        busy_text  = st.text_input(
            "Busy times — used by the AI recommender (HH:MM-HH:MM, comma-separated)",
            value=_busy_times_to_text(_existing.busy_times) if _existing else "09:00-17:00",
            help="Example: 09:00-17:00, 19:00-20:00",
        )
        if st.form_submit_button("Save owner") and owner_name:
            parsed_busy = _parse_busy_times(busy_text)
            if _existing:
                # Edit in-place — keeps all pets and tasks
                _existing.name = owner_name
                _existing.contact_info = contact
                _existing.busy_times = parsed_busy
            else:
                st.session_state.owner = Owner(
                    name=owner_name, contact_info=contact, busy_times=parsed_busy
                )
                st.session_state.show_schedule = False
            st.success(f"Owner '{owner_name}' saved!")

if st.session_state.owner is None:
    st.info("Enter owner info above to get started.")
    st.stop()

owner: Owner = st.session_state.owner
st.divider()

# ── Add a pet ─────────────────────────────────────────────────────────────────
st.subheader("Pets")
with st.form("pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
    col4, col5 = st.columns(2)
    with col4:
        energy = st.selectbox("Energy level", ["low", "medium", "high"], index=1)
    with col5:
        health_notes = st.text_input("Health notes (optional)", value="", help="e.g. 'senior, mild arthritis'")
    if st.form_submit_button("Add pet") and pet_name:
        owner.add_pet(Pet(
            name=pet_name, species=species, age=int(age),
            energy=energy, health_notes=health_notes,
        ))
        st.success(f"Added {pet_name} the {species}!")

if owner.pets:
    st.write("Pets: " + ", ".join(p.name for p in owner.pets))

    with st.expander("Edit or delete a pet"):
        pet_to_manage = st.selectbox(
            "Select pet", [p.name for p in owner.pets], key="manage_pet_sel"
        )
        pet_obj = next(p for p in owner.pets if p.name == pet_to_manage)

        # Edit
        with st.form("edit_pet_form"):
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                new_name    = st.text_input("Name",    value=pet_obj.name)
            with ec2:
                new_species = st.selectbox("Species", ["dog", "cat", "other"],
                                           index=["dog", "cat", "other"].index(pet_obj.species))
            with ec3:
                new_age     = st.number_input("Age", min_value=0, max_value=30, value=pet_obj.age)
            ec4, ec5 = st.columns(2)
            with ec4:
                new_energy = st.selectbox(
                    "Energy", ["low", "medium", "high"],
                    index=["low", "medium", "high"].index(getattr(pet_obj, "energy", "medium")),
                )
            with ec5:
                new_health = st.text_input("Health notes", value=getattr(pet_obj, "health_notes", ""))
            if st.form_submit_button("Save changes"):
                pet_obj.name         = new_name
                pet_obj.species      = new_species
                pet_obj.age          = int(new_age)
                pet_obj.energy       = new_energy
                pet_obj.health_notes = new_health
                st.success(f"Updated pet to {new_name}!")

        # Delete
        st.markdown("---")
        if st.button(f"Delete {pet_to_manage} (and all their tasks)", type="secondary"):
            owner.remove_pet(pet_obj)
            st.session_state.show_schedule = False
            st.warning(f"{pet_to_manage} removed.")
            st.rerun()
else:
    st.info("No pets yet. Add one above.")

st.divider()

# ── Add a task ────────────────────────────────────────────────────────────────
st.subheader("Schedule a Task")
if not owner.pets:
    st.warning("Add at least one pet before scheduling tasks.")
else:
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
            task_time  = st.text_input("Time (HH:MM)", value="08:00")
            duration   = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col2:
            priority   = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            frequency  = st.selectbox("Frequency", ["once", "daily", "weekly"])
            target_pet = st.selectbox("Assign to pet", [p.name for p in owner.pets])

        if st.form_submit_button("Add task") and task_title:
            task = Task(
                title=task_title,
                time=task_time,
                duration_minutes=int(duration),
                priority=priority,
                frequency=frequency,
            )
            next(p for p in owner.pets if p.name == target_pet).add_task(task)
            st.session_state.show_schedule = False   # reset so schedule refreshes
            st.success(f"Task '{task_title}' added to {target_pet}!")

st.divider()

# ── Schedule ──────────────────────────────────────────────────────────────────
st.subheader("Today's Schedule")

col_btn, col_hide = st.columns([2, 1])
with col_btn:
    if st.button("Show / Refresh Schedule"):
        st.session_state.show_schedule = True
with col_hide:
    if st.button("Hide Schedule"):
        st.session_state.show_schedule = False

if st.session_state.show_schedule and owner.pets:
    scheduler = Scheduler(owner)
    pairs = scheduler.get_tasks_with_pets()   # [(task, pet_name), ...]

    if not pairs:
        st.info("No tasks yet. Add some above.")
    else:
        # ── Filters ───────────────────────────────────────────────────────────
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            pet_filter = st.selectbox(
                "Filter by pet", ["All"] + [p.name for p in owner.pets], key="pet_filter"
            )
        with fcol2:
            status_filter = st.selectbox(
                "Filter by status", ["All", "Pending", "Completed"], key="status_filter"
            )

        # Apply filters
        filtered = pairs
        if pet_filter != "All":
            filtered = [(t, pn) for t, pn in filtered if pn == pet_filter]
        if status_filter == "Pending":
            filtered = [(t, pn) for t, pn in filtered if not t.completed]
        elif status_filter == "Completed":
            filtered = [(t, pn) for t, pn in filtered if t.completed]

        # ── Progress bar ──────────────────────────────────────────────────────
        done, total = scheduler.completion_progress()
        st.progress(done / total if total else 0, text=f"{done} / {total} tasks completed")

        # ── Conflict warnings ─────────────────────────────────────────────────
        for c in scheduler.detect_conflicts():
            st.warning(c)

        # ── Schedule table ────────────────────────────────────────────────────
        if filtered:
            rows = [
                {
                    "Time":     t.time,
                    "Pet":      pn,
                    "Task":     t.title,
                    "Duration": f"{t.duration_minutes} min",
                    "Priority": t.priority,
                    "Freq":     t.frequency,
                    "Status":   "Done" if t.completed else "Pending",
                }
                for t, pn in filtered
            ]
            st.table(rows)
        else:
            st.info("No tasks match the current filters.")

        st.divider()

        # ── Actions ───────────────────────────────────────────────────────────
        all_task_pairs = scheduler.get_tasks_with_pets()

        # Label helper: "08:00 — Morning walk (Mochi)"
        def label(task, pet_name):
            return f"{task.time} — {task.title} ({pet_name})"

        acol1, acol2 = st.columns(2)

        with acol1:
            st.markdown("**Mark complete**")
            incomplete = [(t, pn) for t, pn in all_task_pairs if not t.completed]
            if incomplete:
                chosen_complete = st.selectbox(
                    "Task to complete",
                    [label(t, pn) for t, pn in incomplete],
                    key="complete_sel",
                )
                if st.button("Mark complete"):
                    for t, pn in incomplete:
                        if label(t, pn) == chosen_complete:
                            t.mark_complete()
                            break
            else:
                st.success("All tasks done!")

        with acol2:
            st.markdown("**Delete task**")
            if all_task_pairs:
                chosen_delete = st.selectbox(
                    "Task to delete",
                    [label(t, pn) for t, pn in all_task_pairs],
                    key="delete_sel",
                )
                if st.button("Delete task"):
                    for t, pn in all_task_pairs:
                        if label(t, pn) == chosen_delete:
                            scheduler.delete_task(t)
                            break
            else:
                st.info("No tasks to delete.")


# ── AI Recommendations (RAG layer) ────────────────────────────────────────────
st.divider()
st.subheader("AI Recommendations")
st.caption("Powered by ChromaDB (local) + sentence-transformers + Claude (optional). Advisory only.")

if not owner.pets:
    st.info("Add at least one pet to get AI-powered recommendations.")
else:
    target_pet_name = st.selectbox(
        "Generate AI schedule for",
        [p.name for p in owner.pets],
        key="ai_target_pet",
    )

    if st.button("Generate AI schedule", type="primary"):
        with st.spinner("Building local index, retrieving context, generating..."):
            try:
                from rag.rag_engine import RAGEngine
                from rag.vector_store import ChromaStore
                from recommender.ranker import apply_recommendation

                store = ChromaStore()
                store.ingest_knowledge_base()  # idempotent — only builds once
                engine = RAGEngine(store=store)
                pet_obj = next(p for p in owner.pets if p.name == target_pet_name)
                rec = engine.generate(owner, pet_obj, k=5)
                result = apply_recommendation(
                    rec,
                    busy_times=owner.busy_times,
                    existing_tasks=pet_obj.tasks,
                )
                st.session_state["last_ai_result"] = result
                st.session_state["last_ai_rec"]    = rec
            except Exception as e:
                st.error(f"AI generation failed: {e}")
                st.info("Make sure `pip install -r requirements.txt` has run.")

    result = st.session_state.get("last_ai_result")
    rec    = st.session_state.get("last_ai_rec")

    if result and rec:
        # Confidence gauge
        conf = result["confidence"]
        label = result["confidence_label"]
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.metric("Confidence", f"{conf:.2f}", label.upper())
        with cc2:
            st.metric("Mode", "LLM" if result["used_llm"] else "Template")
        with cc3:
            st.metric("Slots kept", f"{len(result['kept'])} / {len(result['kept']) + len(result['dropped'])}")

        # Explanation + scrub warning
        if result["explanation"]:
            st.info(result["explanation"])

        # Recommended schedule table
        if result["ranked"]:
            rows = [
                {
                    "Time":     s.get("time", "—"),
                    "Task":     s.get("title", "—"),
                    "Duration": f"{s.get('duration_minutes', 15)} min",
                    "Priority": s.get("priority", "medium"),
                    "Score":    f"{s.get('score', 0.0):.2f}",
                    "Shifted":  "yes" if s.get("shifted") else "",
                    "Rationale": s.get("rationale", "")[:80],
                }
                for s in result["ranked"]
            ]
            st.markdown("**Recommended schedule (constraint-validated)**")
            st.table(rows)

            # One-click "add all to my pet"
            if st.button("Add all kept tasks to " + target_pet_name):
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

        # Dropped (constraint violations)
        if result["dropped"]:
            with st.expander(f"Dropped slots ({len(result['dropped'])})"):
                for d in result["dropped"]:
                    reason = d.get("drop_reason", "unknown")
                    st.warning(f"{d.get('time', '?')} — {d.get('title', '?')} — dropped ({reason})")

        # Citations
        if result["citations"]:
            with st.expander("Sources used"):
                for c in result["citations"]:
                    st.write(f"- `{c}`")

        # Confidence-based guidance
        if label == "low":
            st.warning("Low confidence — consider adding more pets or richer health notes for better matches.")
