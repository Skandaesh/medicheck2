#!/usr/bin/env python3
"""
Medication Safety Checker (educational tool)
--------------------------------------------
Enter your condition(s) and a prescribed medication, and the app checks them
against a small built-in rule database of well-known contraindications and
cautions.

IMPORTANT: This is NOT medical advice. The database is small and incomplete.
"No conflict found" does NOT mean "safe". Always confirm with the prescribing
doctor or a pharmacist before starting, stopping, or changing any medicine.

Run:  python med_safety_checker.py
Uses only the Python standard library.
"""

import re

# ----------------------------------------------------------------------------
# 1. DATABASE
# ----------------------------------------------------------------------------

# medication class -> list of names/brands people might type
MED_CLASSES = {
    "nsaid": ["ibuprofen", "naproxen", "diclofenac", "ketorolac", "celecoxib",
              "indomethacin", "mefenamic acid", "brufen", "advil", "motrin",
              "voltaren", "nsaid"],
    "aspirin": ["aspirin", "acetylsalicylic acid", "ecosprin", "disprin"],
    "paracetamol": ["paracetamol", "acetaminophen", "tylenol", "crocin",
                    "dolo", "panadol"],
    "metformin": ["metformin", "glucophage"],
    "penicillin": ["amoxicillin", "penicillin", "ampicillin", "augmentin",
                   "amoxyclav", "co-amoxiclav", "flucloxacillin"],
    "beta_blocker": ["propranolol", "atenolol", "metoprolol", "bisoprolol",
                     "carvedilol", "nebivolol", "labetalol"],
    "ace_inhibitor": ["lisinopril", "enalapril", "ramipril", "captopril",
                      "perindopril", "losartan", "telmisartan", "valsartan"],
    "statin": ["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin",
               "lovastatin"],
    "decongestant": ["pseudoephedrine", "phenylephrine", "sudafed"],
    "antihistamine_1": ["diphenhydramine", "chlorpheniramine", "promethazine",
                        "hydroxyzine", "benadryl", "avil"],
    "warfarin": ["warfarin", "coumadin"],
    "ssri": ["sertraline", "fluoxetine", "escitalopram", "citalopram",
             "paroxetine", "zoloft", "prozac"],
    "opioid": ["tramadol", "codeine", "morphine", "oxycodone", "hydrocodone"],
    "fluoroquinolone": ["ciprofloxacin", "levofloxacin", "ofloxacin",
                        "moxifloxacin", "norfloxacin"],
    "steroid": ["prednisone", "prednisolone", "dexamethasone",
                "methylprednisolone", "hydrocortisone"],
    "pde5": ["sildenafil", "tadalafil", "vardenafil", "viagra"],
    "nitrate": ["nitroglycerin", "glyceryl trinitrate", "isosorbide",
                "nitrate", "gtn"],
    "maoi": ["phenelzine", "tranylcypromine", "selegiline", "moclobemide"],
}

# condition tag -> phrases that indicate it (matched on word boundaries)
CONDITION_TAGS = {
    "ulcer": ["ulcer", "ulcers", "peptic", "gi bleed", "stomach bleeding",
              "gastric bleeding", "gastritis"],
    "kidney": ["kidney", "kidneys", "renal", "ckd", "nephritis"],
    "liver": ["liver", "hepatitis", "cirrhosis", "hepatic", "jaundice"],
    "heart_failure": ["heart failure", "chf", "cardiac failure"],
    "heart_disease": ["heart disease", "angina", "heart attack", "coronary",
                      "arrhythmia", "cardiac", "palpitations", "cad"],
    "hypertension": ["hypertension", "high blood pressure", "high bp"],
    "low_bp": ["low blood pressure", "hypotension", "low bp"],
    "asthma": ["asthma", "wheezing"],
    "copd": ["copd", "emphysema", "chronic bronchitis"],
    "diabetes": ["diabetes", "diabetic", "high sugar", "type 2", "type 1"],
    "pregnancy": ["pregnant", "pregnancy", "expecting"],
    "breastfeeding": ["breastfeeding", "nursing mother", "lactating"],
    "bleeding": ["bleeding disorder", "hemophilia", "haemophilia",
                 "low platelets", "thrombocytopenia", "bleeding"],
    "glaucoma": ["glaucoma"],
    "bph": ["bph", "enlarged prostate", "prostate enlargement",
            "urinary retention"],
    "hyperthyroid": ["hyperthyroid", "hyperthyroidism", "overactive thyroid",
                     "thyrotoxicosis"],
    "epilepsy": ["epilepsy", "seizure", "seizures", "convulsions"],
    "myasthenia": ["myasthenia gravis", "myasthenia"],
    "bradycardia": ["bradycardia", "heart block", "slow heart rate",
                    "slow heartbeat"],
    "alcohol": ["alcoholism", "alcohol dependence", "heavy drinker",
                "alcohol abuse", "drinks heavily"],
    "bipolar": ["bipolar", "mania", "manic"],
    "infection": ["infection", "tb", "tuberculosis", "fungal"],
    "osteoporosis": ["osteoporosis"],
    "mono": ["mononucleosis", "glandular fever", "mono"],
    "tendon": ["tendon", "tendinitis", "tendonitis", "tendon rupture"],
    "dementia": ["dementia", "alzheimer", "alzheimers"],
    "respiratory": ["breathing problem", "breathing problems",
                    "sleep apnea", "sleep apnoea", "respiratory depression"],
    "hyperkalemia": ["hyperkalemia", "high potassium"],
    "angioedema": ["angioedema", "swelling of face", "swelling of lips"],
    "dehydration": ["dehydration", "dehydrated", "vomiting", "diarrhea",
                    "diarrhoea"],
}

# Rules: med class -> list of (condition tag, severity, explanation)
# severity: "AVOID" (contraindicated / usually should not be used)
#           "CAUTION" (may be used only with doctor's supervision)
RULES = {
    "nsaid": [
        ("ulcer", "AVOID", "NSAIDs can cause or worsen stomach ulcers and GI bleeding."),
        ("kidney", "AVOID", "NSAIDs can reduce kidney blood flow and worsen kidney disease."),
        ("heart_failure", "AVOID", "NSAIDs cause fluid retention and can worsen heart failure."),
        ("bleeding", "AVOID", "NSAIDs impair clotting and raise bleeding risk."),
        ("pregnancy", "AVOID", "NSAIDs are generally avoided in pregnancy, especially from ~20 weeks onward."),
        ("asthma", "CAUTION", "NSAIDs can trigger asthma attacks in some people."),
        ("hypertension", "CAUTION", "NSAIDs can raise blood pressure and blunt BP medicines."),
        ("heart_disease", "CAUTION", "NSAIDs are linked to higher heart attack/stroke risk."),
        ("liver", "CAUTION", "Liver disease increases the risk of NSAID side effects."),
        ("dehydration", "CAUTION", "NSAIDs while dehydrated raise the risk of kidney injury."),
    ],
    "aspirin": [
        ("ulcer", "AVOID", "Aspirin can cause or worsen stomach ulcers and bleeding."),
        ("bleeding", "AVOID", "Aspirin impairs clotting and raises bleeding risk."),
        ("kidney", "AVOID", "Aspirin can worsen kidney disease at analgesic doses."),
        ("pregnancy", "AVOID", "Aspirin is avoided in pregnancy unless specifically prescribed (e.g. low-dose)."),
        ("asthma", "CAUTION", "Aspirin can trigger asthma attacks in aspirin-sensitive people."),
        ("liver", "CAUTION", "Liver disease increases the risk of bleeding with aspirin."),
        ("breastfeeding", "CAUTION", "Aspirin passes into breast milk; ask your doctor."),
    ],
    "paracetamol": [
        ("liver", "CAUTION", "Paracetamol is processed by the liver; dose limits are lower in liver disease."),
        ("alcohol", "AVOID", "Heavy alcohol use greatly raises paracetamol liver-damage risk."),
        ("kidney", "CAUTION", "Dose adjustment may be needed in severe kidney disease."),
    ],
    "metformin": [
        ("kidney", "AVOID", "Metformin is unsafe in significant kidney impairment (lactic acidosis risk)."),
        ("liver", "AVOID", "Liver impairment raises the risk of lactic acidosis with metformin."),
        ("heart_failure", "CAUTION", "Unstable heart failure raises lactic acidosis risk."),
        ("alcohol", "CAUTION", "Excess alcohol with metformin raises lactic acidosis risk."),
        ("dehydration", "CAUTION", "Dehydration can lead to kidney problems and lactic acidosis; metformin is often paused."),
    ],
    "penicillin": [
        ("kidney", "CAUTION", "Dose adjustment may be needed in kidney disease."),
        ("mono", "AVOID", "Amoxicillin/ampicillin often cause a severe rash in infectious mononucleosis."),
    ],
    "beta_blocker": [
        ("asthma", "AVOID", "Beta-blockers can trigger severe bronchospasm in asthma."),
        ("copd", "CAUTION", "Beta-blockers may worsen breathing in COPD (cardio-selective ones are sometimes used)."),
        ("bradycardia", "AVOID", "Beta-blockers slow the heart and can worsen bradycardia/heart block."),
        ("low_bp", "CAUTION", "Beta-blockers can lower blood pressure further."),
        ("diabetes", "CAUTION", "Beta-blockers can mask low blood sugar symptoms."),
        ("heart_failure", "CAUTION", "Only certain beta-blockers are used, and only if stable, under specialist care."),
    ],
    "ace_inhibitor": [
        ("pregnancy", "AVOID", "ACE inhibitors/ARBs can seriously harm a developing baby."),
        ("angioedema", "AVOID", "History of angioedema is a contraindication."),
        ("hyperkalemia", "AVOID", "These medicines raise potassium levels."),
        ("kidney", "CAUTION", "Kidney function and potassium need monitoring."),
        ("low_bp", "CAUTION", "May lower blood pressure further."),
        ("dehydration", "CAUTION", "Dehydration raises the risk of kidney injury; these are often paused."),
        ("breastfeeding", "CAUTION", "Some are not recommended while breastfeeding."),
    ],
    "statin": [
        ("liver", "AVOID", "Statins are avoided in active liver disease."),
        ("pregnancy", "AVOID", "Statins are generally avoided in pregnancy."),
        ("breastfeeding", "AVOID", "Statins are generally not recommended while breastfeeding."),
        ("kidney", "CAUTION", "Some statins need dose adjustment in kidney disease."),
        ("alcohol", "CAUTION", "Heavy alcohol use raises the risk of liver problems with statins."),
    ],
    "decongestant": [
        ("hypertension", "AVOID", "Decongestants can raise blood pressure."),
        ("heart_disease", "AVOID", "Decongestants can raise heart rate and strain the heart."),
        ("glaucoma", "CAUTION", "May worsen some types of glaucoma."),
        ("hyperthyroid", "AVOID", "Stimulant effects can worsen an overactive thyroid."),
        ("bph", "CAUTION", "May worsen urinary retention."),
        ("diabetes", "CAUTION", "May raise blood sugar and blood pressure."),
        ("pregnancy", "CAUTION", "Generally avoided in early pregnancy; ask your doctor."),
    ],
    "antihistamine_1": [
        ("glaucoma", "CAUTION", "Can worsen narrow-angle glaucoma."),
        ("bph", "CAUTION", "Can cause urinary retention."),
        ("dementia", "AVOID", "Anticholinergic effects can worsen confusion and memory."),
        ("asthma", "CAUTION", "Thickened secretions may worsen an asthma attack."),
        ("respiratory", "CAUTION", "Drowsiness can worsen breathing problems."),
        ("epilepsy", "CAUTION", "May lower the seizure threshold in some people."),
    ],
    "warfarin": [
        ("bleeding", "AVOID", "Warfarin raises bleeding risk."),
        ("ulcer", "AVOID", "Active GI ulcers/bleeding make warfarin dangerous."),
        ("pregnancy", "AVOID", "Warfarin can cause birth defects."),
        ("liver", "CAUTION", "Liver disease changes clotting and warfarin response."),
        ("alcohol", "CAUTION", "Alcohol affects INR control and bleeding risk."),
    ],
    "ssri": [
        ("bipolar", "CAUTION", "Antidepressants can trigger mania in bipolar disorder."),
        ("bleeding", "CAUTION", "SSRIs increase bleeding risk."),
        ("ulcer", "CAUTION", "SSRIs raise GI bleeding risk."),
        ("epilepsy", "CAUTION", "May lower the seizure threshold."),
        ("pregnancy", "CAUTION", "Risks and benefits must be weighed by your doctor."),
        ("liver", "CAUTION", "May need a lower dose in liver disease."),
        ("glaucoma", "CAUTION", "Can rarely trigger angle-closure glaucoma."),
    ],
    "opioid": [
        ("respiratory", "AVOID", "Opioids suppress breathing."),
        ("copd", "CAUTION", "Opioids can dangerously suppress breathing in COPD."),
        ("asthma", "CAUTION", "Opioids can worsen breathing in an acute asthma attack."),
        ("epilepsy", "CAUTION", "Tramadol in particular can trigger seizures."),
        ("alcohol", "AVOID", "Alcohol plus opioids greatly raises overdose and breathing-failure risk."),
        ("liver", "CAUTION", "Liver disease raises opioid levels in the body."),
        ("kidney", "CAUTION", "Kidney disease can cause opioid build-up."),
        ("pregnancy", "CAUTION", "Opioids carry risks for the baby, including dependence at birth."),
        ("breastfeeding", "AVOID", "Codeine/tramadol can harm a breastfed baby."),
        ("dementia", "CAUTION", "Higher risk of confusion and falls."),
    ],
    "fluoroquinolone": [
        ("myasthenia", "AVOID", "Can severely worsen muscle weakness in myasthenia gravis."),
        ("tendon", "AVOID", "Raises the risk of tendon inflammation and rupture."),
        ("epilepsy", "CAUTION", "May lower the seizure threshold."),
        ("pregnancy", "AVOID", "Generally avoided in pregnancy."),
        ("breastfeeding", "CAUTION", "Generally avoided while breastfeeding."),
        ("kidney", "CAUTION", "Dose adjustment is needed in kidney disease."),
        ("diabetes", "CAUTION", "Can cause blood sugar swings."),
    ],
    "steroid": [
        ("diabetes", "CAUTION", "Steroids raise blood sugar."),
        ("infection", "CAUTION", "Steroids suppress immunity and may worsen infections."),
        ("ulcer", "CAUTION", "Steroids raise the risk of stomach ulcers/bleeding."),
        ("osteoporosis", "CAUTION", "Steroids weaken bones."),
        ("hypertension", "CAUTION", "Steroids can raise blood pressure and cause fluid retention."),
        ("bipolar", "CAUTION", "Steroids can trigger mood episodes."),
        ("glaucoma", "CAUTION", "Steroids can raise eye pressure."),
        ("heart_failure", "CAUTION", "Fluid retention can worsen heart failure."),
    ],
    "pde5": [
        ("heart_disease", "CAUTION", "Sexual activity and BP drops can be risky with severe heart disease."),
        ("low_bp", "AVOID", "Can cause a dangerous drop in blood pressure."),
        ("heart_failure", "CAUTION", "Needs doctor approval."),
    ],
    "nitrate": [
        ("low_bp", "AVOID", "Nitrates lower blood pressure further."),
    ],
    "maoi": [
        ("hypertension", "CAUTION", "MAOIs can cause dangerous blood pressure spikes."),
        ("bipolar", "CAUTION", "Can trigger mania."),
    ],
}

# Drug-drug interactions between classes (checked against "other medicines")
INTERACTIONS = [
    ({"nsaid", "aspirin"}, {"warfarin"}, "AVOID", "Greatly increases bleeding risk."),
    ({"nsaid"}, {"ace_inhibitor"}, "CAUTION", "Can reduce BP control and harm the kidneys."),
    ({"nsaid", "aspirin"}, {"ssri"}, "CAUTION", "Increases the risk of GI bleeding."),
    ({"nsaid"}, {"aspirin"}, "CAUTION", "Taking two NSAIDs together raises stomach and kidney risks."),
    ({"pde5"}, {"nitrate"}, "AVOID", "Can cause a life-threatening drop in blood pressure."),
    ({"ssri"}, {"opioid"}, "CAUTION", "Risk of serotonin syndrome (and seizures with tramadol)."),
    ({"ssri"}, {"maoi"}, "AVOID", "Risk of life-threatening serotonin syndrome."),
    ({"opioid"}, {"maoi"}, "AVOID", "Risk of serotonin syndrome / severe reactions."),
    ({"decongestant"}, {"maoi"}, "AVOID", "Risk of dangerous blood pressure spikes."),
    ({"warfarin"}, {"fluoroquinolone", "penicillin"}, "CAUTION", "Antibiotics can raise INR and bleeding risk."),
    ({"beta_blocker"}, {"beta_blocker"}, "CAUTION", "Two beta-blockers together is unusual; confirm with a doctor."),
    ({"statin"}, {"fluoroquinolone"}, "CAUTION", "Minor, but report any muscle or tendon pain."),
    ({"ace_inhibitor"}, {"steroid"}, "CAUTION", "Steroids can blunt blood-pressure control."),
]

# ----------------------------------------------------------------------------
# 2. LOGIC
# ----------------------------------------------------------------------------


def _contains(text, phrase):
    return re.search(r"\b" + re.escape(phrase) + r"\b", text) is not None


def find_med_class(name):
    """Return the class key for a medication name, or None."""
    name = name.lower().strip()
    if not name:
        return None
    for cls, names in MED_CLASSES.items():
        for n in names:
            if _contains(name, n):
                return cls
    return None


def find_classes_in_text(text):
    """Find all medication classes mentioned in free text."""
    text = text.lower()
    found = set()
    for cls, names in MED_CLASSES.items():
        if any(_contains(text, n) for n in names):
            found.add(cls)
    return found


def find_condition_tags(text):
    text = text.lower()
    return {tag for tag, phrases in CONDITION_TAGS.items()
            if any(_contains(text, p) for p in phrases)}


def check(conditions, medication, age=None, allergies="", other_meds=""):
    """Return (verdict, findings, notes). verdict in AVOID/CAUTION/NO_CONFLICT/UNKNOWN."""
    findings = []   # (severity, reason)
    notes = []

    med_class = find_med_class(medication)
    tags = find_condition_tags(conditions)

    if med_class is None:
        return ("UNKNOWN", [], [
            f"'{medication}' is not in this app's database.",
            "Please ask your pharmacist or doctor, or check an official drug label."])

    # Condition rules
    for tag, severity, reason in RULES.get(med_class, []):
        if tag in tags:
            findings.append((severity, f"[{tag.replace('_', ' ')}] {reason}"))

    # Allergies
    allergies_l = allergies.lower()
    if allergies_l.strip():
        med_l = medication.lower().strip()
        allergy_classes = find_classes_in_text(allergies_l)
        if med_class in allergy_classes or (med_l and _contains(allergies_l, med_l)):
            findings.append(("AVOID", "[allergy] You listed an allergy that matches this medicine."))
        if med_class == "aspirin" and "nsaid" in allergy_classes:
            findings.append(("AVOID", "[allergy] NSAID allergy often cross-reacts with aspirin."))
        if med_class == "nsaid" and "aspirin" in allergy_classes:
            findings.append(("AVOID", "[allergy] Aspirin allergy often cross-reacts with NSAIDs."))

    # Age-based
    if age is not None:
        if age < 16 and med_class == "aspirin":
            findings.append(("AVOID", "[age] Aspirin is avoided in children/teens (risk of Reye's syndrome)."))
        if age < 12 and med_class == "opioid":
            findings.append(("AVOID", "[age] Codeine/tramadol are not recommended for young children."))
        if age < 18 and med_class == "fluoroquinolone":
            findings.append(("CAUTION", "[age] Fluoroquinolones are generally avoided in children unless essential."))
        if age < 6 and med_class in ("decongestant", "antihistamine_1"):
            findings.append(("AVOID", "[age] Not recommended for young children."))
        if age >= 65 and med_class in ("antihistamine_1", "opioid", "nsaid"):
            findings.append(("CAUTION", "[age] Older adults are more sensitive to side effects of this type of medicine."))
        if age >= 65 and med_class in ("ssri", "beta_blocker", "ace_inhibitor"):
            findings.append(("CAUTION", "[age] Older adults may need lower doses and closer monitoring."))

    # Drug interactions
    other_classes = find_classes_in_text(other_meds)
    for a, b, severity, reason in INTERACTIONS:
        for x, y in ((a, b), (b, a)):
            if med_class in x and (other_classes & y):
                # skip duplicate-class false positives unless explicit
                clash = ", ".join(sorted(other_classes & y)).replace("_", " ")
                findings.append((severity, f"[interaction with {clash}] {reason}"))
                break

    # de-duplicate
    seen, unique = set(), []
    for f in findings:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    findings = unique

    if not tags:
        notes.append("No known condition keywords were recognized in your input. "
                     "Try plain terms such as 'asthma', 'kidney disease', 'pregnant', 'high blood pressure'.")

    if any(s == "AVOID" for s, _ in findings):
        verdict = "AVOID"
    elif any(s == "CAUTION" for s, _ in findings):
        verdict = "CAUTION"
    else:
        verdict = "NO_CONFLICT"
    return verdict, findings, notes


VERDICT_TEXT = {
    "AVOID": "NOT SAFE - a serious conflict was found. Do not start this medicine\n"
             "until you've spoken to your doctor or pharmacist.",
    "CAUTION": "USE WITH CAUTION - this may be OK, but only under medical supervision.\n"
               "Confirm with your doctor or pharmacist first.",
    "NO_CONFLICT": "No conflict found in this app's limited database.\n"
                   "That does NOT guarantee it is safe - please still confirm with a professional.",
    "UNKNOWN": "UNKNOWN - this medicine isn't in the database, so no check was possible.",
}

DISCLAIMER = ("This tool is for education only and is not medical advice. If you have "
              "trouble breathing, swelling, severe rash, or any emergency symptoms, "
              "seek urgent medical care.")


def format_report(verdict, findings, notes, medication):
    lines = [f"Medication: {medication}", "", VERDICT_TEXT[verdict], ""]
    if findings:
        lines.append("Reasons:")
        for sev, reason in sorted(findings, key=lambda f: f[0] != "AVOID"):
            lines.append(f"  - {sev}: {reason}")
        lines.append("")
    for n in notes:
        lines.append(f"Note: {n}")
    if notes:
        lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 3. INTERFACES
# ----------------------------------------------------------------------------


def parse_age(s):
    s = s.strip()
    if not s:
        return None
    try:
        a = int(s)
        return a if 0 <= a <= 120 else None
    except ValueError:
        return None


def run_gui():
    import tkinter as tk
    from tkinter import ttk

    colors = {"AVOID": "#c0392b", "CAUTION": "#d68910",
              "NO_CONFLICT": "#1e8449", "UNKNOWN": "#566573"}

    root = tk.Tk()
    root.title("Medication Safety Checker")
    root.geometry("640x700")
    frm = ttk.Frame(root, padding=14)
    frm.pack(fill="both", expand=True)

    def add(label, hint=""):
        ttk.Label(frm, text=label, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
        if hint:
            ttk.Label(frm, text=hint, foreground="#666").pack(anchor="w")
        e = ttk.Entry(frm)
        e.pack(fill="x")
        return e

    cond = add("Current condition(s)", "e.g. asthma, high blood pressure, pregnant")
    med = add("Prescribed medication", "e.g. ibuprofen, metformin, amoxicillin")
    age = add("Age (optional)")
    allergy = add("Known allergies (optional)", "e.g. penicillin")
    other = add("Other medicines you take (optional)", "e.g. warfarin, sertraline")

    banner = tk.Label(frm, text="", font=("Segoe UI", 13, "bold"), fg="white",
                      pady=10, wraplength=580, justify="center")
    out = tk.Text(frm, height=16, wrap="word", font=("Segoe UI", 10))

    def on_check(event=None):
        if not med.get().strip():
            banner.config(text="Please enter a medication.", bg=colors["UNKNOWN"])
            banner.pack(fill="x", pady=(12, 0))
            return
        verdict, findings, notes = check(cond.get(), med.get(), parse_age(age.get()),
                                         allergy.get(), other.get())
        label = {"AVOID": "NOT SAFE - AVOID", "CAUTION": "USE WITH CAUTION",
                 "NO_CONFLICT": "NO CONFLICT FOUND", "UNKNOWN": "UNKNOWN MEDICINE"}[verdict]
        banner.config(text=label, bg=colors[verdict])
        banner.pack(fill="x", pady=(12, 0))
        out.pack(fill="both", expand=True, pady=(8, 0))
        out.config(state="normal")
        out.delete("1.0", "end")
        out.insert("1.0", format_report(verdict, findings, notes, med.get().strip()))
        out.config(state="disabled")

    ttk.Button(frm, text="Check safety", command=on_check).pack(pady=(14, 0))
    root.bind("<Return>", on_check)
    root.mainloop()


def run_cli():
    print("=" * 60)
    print(" Medication Safety Checker (educational, not medical advice)")
    print("=" * 60)
    while True:
        cond = input("\nYour condition(s): ")
        med = input("Prescribed medication: ")
        age = parse_age(input("Age (optional, Enter to skip): "))
        allergy = input("Known allergies (optional): ")
        other = input("Other medicines you take (optional): ")
        verdict, findings, notes = check(cond, med, age, allergy, other)
        print("\n" + "-" * 60)
        print(format_report(verdict, findings, notes, med.strip()))
        print("-" * 60)
        if input("\nCheck another? (y/n): ").strip().lower() != "y":
            break


if __name__ == "__main__":
    try:
        run_gui()
    except Exception:  # no display / tkinter missing
        run_cli()
