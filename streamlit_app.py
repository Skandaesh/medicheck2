"""
Streamlit front-end for the Medication Safety Checker (with dosage meter).

Setup:
    pip install streamlit
Run (from the folder containing BOTH files):
    streamlit run streamlit_app.py

Requires med_safety_checker.py in the same folder (database + logic).
"""

import streamlit as st

from med_safety_checker import (
    check, format_report, assess_dose, find_condition_tags, DISCLAIMER,
)

st.set_page_config(page_title="Medication Safety Checker", page_icon="💊")

st.title("💊 Medication Safety Checker")
st.caption("Educational tool only - not medical advice.")

with st.form("check_form"):
    conditions = st.text_input(
        "Current condition(s)",
        placeholder="e.g. asthma, high blood pressure, pregnant",
    )
    medication = st.text_input(
        "Prescribed medication",
        placeholder="e.g. ibuprofen, metformin, amoxicillin",
    )

    st.markdown("**Prescribed dosage**")
    dose_mg = st.slider(
        "Dose per intake (mg)  - leave at 0 to skip the dose check",
        min_value=0, max_value=1000, value=0, step=5,
    )
    times = st.slider("Times per day", min_value=1, max_value=6, value=1)
    st.caption(f"Total per day: **{dose_mg * times} mg**")

    col1, col2 = st.columns(2)
    with col1:
        age_val = st.number_input("Age (0 = skip)", min_value=0, max_value=120, value=0, step=1)
    with col2:
        allergies = st.text_input("Known allergies (optional)", placeholder="e.g. penicillin")
    other_meds = st.text_input(
        "Other medicines you take (optional)", placeholder="e.g. warfarin, sertraline"
    )
    submitted = st.form_submit_button("Check safety")

if submitted:
    if not medication.strip():
        st.warning("Please enter a medication.")
    else:
        age = int(age_val) if age_val > 0 else None
        dose = dose_mg if dose_mg > 0 else None
        verdict, findings, notes = check(
            conditions, medication, age, allergies, other_meds, dose, times
        )

        if verdict == "AVOID":
            st.error("NOT SAFE - a serious conflict was found. Do not start this medicine "
                     "until you've spoken to your doctor or pharmacist.")
        elif verdict == "CAUTION":
            st.warning("USE WITH CAUTION - may be OK, but only under medical supervision. "
                       "Confirm with your doctor or pharmacist first.")
        elif verdict == "NO_CONFLICT":
            st.success("No conflict found in this app's limited database. "
                       "That does NOT guarantee it is safe - please still confirm with a professional.")
        else:
            st.info("UNKNOWN - this medicine isn't in the database, so no check was possible.")

        # ---- Dosage meter ----
        d = assess_dose(medication, dose, times, age, find_condition_tags(conditions))
        if d:
            st.subheader("Dosage meter")
            if d["daily_max"]:
                ratio = d["daily_total"] / d["daily_max"]
                st.progress(min(ratio, 1.0))
                st.caption(f"{d['daily_total']:g} mg/day of a usual adult maximum of "
                           f"{d['daily_max']} mg/day  ({ratio:.0%})")
                if d["status"] == "WITHIN":
                    st.success(d["message"])
                elif d["status"] == "OVER_SINGLE":
                    st.warning(d["message"])
                else:
                    st.error(d["message"])
            else:
                st.info(d["message"])

        if findings:
            st.subheader("Reasons")
            for sev, reason in sorted(findings, key=lambda f: f[0] != "AVOID"):
                icon = "🔴" if sev == "AVOID" else "🟠"
                st.markdown(f"{icon} **{sev}** - {reason}")

        for n in notes:
            st.caption(f"Note: {n}")

        with st.expander("Plain-text report"):
            st.code(format_report(verdict, findings, notes, medication.strip()))

st.divider()
st.caption(DISCLAIMER)
