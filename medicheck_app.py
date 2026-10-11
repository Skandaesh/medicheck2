"""
Medication Safety Checker - single-file Streamlit app (with dosage meter).

Setup:   pip install streamlit
Run:     streamlit run medicheck_app.py
On Streamlit Cloud: this is the ONLY file you need to upload (plus a
requirements.txt containing the line:  streamlit ).

Educational tool only - not medical advice.
"""
import streamlit as st

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
# DOSE REFERENCE (typical ADULT maximums, in mg, from standard labelling).
# These are upper limits only. They do not tell you the right dose for you -
# that is decided by your prescriber (kidney function, weight, etc. matter).
# ----------------------------------------------------------------------------
DOSE_LIMITS = {
    # drug: (max single dose mg, max total per day mg)
    "ibuprofen": (800, 3200),
    "naproxen": (500, 1250),
    "diclofenac": (75, 150),
    "aspirin": (1000, 4000),
    "paracetamol": (1000, 4000),
    "metformin": (1000, 2550),
    "amoxicillin": (1000, 3000),
    "atorvastatin": (80, 80),
    "rosuvastatin": (40, 40),
    "lisinopril": (80, 80),
    "losartan": (100, 100),
    "metoprolol": (200, 400),
    "atenolol": (100, 100),
    "sertraline": (200, 200),
    "escitalopram": (20, 20),
    "fluoxetine": (80, 80),
    "tramadol": (100, 400),
    "ciprofloxacin": (750, 1500),
    "pseudoephedrine": (60, 240),
    "diphenhydramine": (50, 300),
    "sildenafil": (100, 100),
}

DOSE_ALIASES = {
    "brufen": "ibuprofen", "advil": "ibuprofen", "motrin": "ibuprofen",
    "tylenol": "paracetamol", "acetaminophen": "paracetamol", "crocin": "paracetamol",
    "dolo": "paracetamol", "panadol": "paracetamol", "glucophage": "metformin",
    "voltaren": "diclofenac", "zoloft": "sertraline", "prozac": "fluoxetine",
    "viagra": "sildenafil", "sudafed": "pseudoephedrine", "benadryl": "diphenhydramine",
    "disprin": "aspirin", "ecosprin": "aspirin",
}


def find_dose_drug(medication):
    med = medication.lower()
    for name in list(DOSE_LIMITS) + list(DOSE_ALIASES):
        if _contains(med, name):
            return DOSE_ALIASES.get(name, name)
    return None


def assess_dose(medication, dose_mg, doses_per_day, age=None, tags=()):
    """
    Compare a prescribed dose with typical adult maximums.
    Returns None if no dose was entered, otherwise a dict with:
      status: WITHIN / OVER_SINGLE / OVER_DAILY / NO_DATA / NOT_ASSESSED
      severity: "AVOID", "CAUTION" or None
      message, daily_total, daily_max, single_max
    """
    if not dose_mg:
        return None
    times = doses_per_day or 1
    daily_total = dose_mg * times
    result = {"status": "NO_DATA", "severity": None, "message": "",
              "daily_total": daily_total, "daily_max": None, "single_max": None}

    if age is not None and age < 18:
        result["status"] = "NOT_ASSESSED"
        result["message"] = ("Children's doses depend on weight and the exact product, so "
                             "this app does not judge them. Follow the dose on the "
                             "prescription label and ask the doctor or pharmacist.")
        return result

    if find_med_class(medication) == "warfarin":
        result["status"] = "NOT_ASSESSED"
        result["message"] = ("Warfarin doses are individualized using blood tests (INR), so "
                             "there is no standard maximum. Only take the dose your "
                             "clinic tells you.")
        return result

    drug = find_dose_drug(medication)
    if drug is None:
        result["message"] = ("No dose reference is available for this medicine in the app. "
                             "Check the prescription label or ask your pharmacist.")
        return result

    single_max, daily_max = DOSE_LIMITS[drug]
    extra = ""
    if drug == "paracetamol" and ({"liver", "alcohol"} & set(tags)):
        daily_max = 2000
        extra = " (lowered because of liver disease / alcohol use; your doctor may set a different limit)"
    result["single_max"], result["daily_max"] = single_max, daily_max
    summary = (f"{dose_mg:g} mg x {times} per day = {daily_total:g} mg/day. "
               f"Usual adult maximums for {drug}: {single_max} mg per dose, "
               f"{daily_max} mg per day{extra}.")

    if daily_total > daily_max:
        result["status"], result["severity"] = "OVER_DAILY", "AVOID"
        result["message"] = ("DAILY TOTAL ABOVE the usual adult maximum. " + summary +
                             " Re-check the prescription with your pharmacist and do not "
                             "change doses on your own.")
    elif dose_mg > single_max:
        result["status"], result["severity"] = "OVER_SINGLE", "CAUTION"
        result["message"] = ("SINGLE DOSE above the usual adult maximum. " + summary +
                             " Confirm with your pharmacist or doctor.")
    else:
        result["status"] = "WITHIN"
        result["message"] = ("Dose is within usual adult limits. " + summary +
                             " Whether it is the right dose for you is for your prescriber.")
    return result


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


def check(conditions, medication, age=None, allergies="", other_meds="",
          dose_mg=None, doses_per_day=None):
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

    # Dose check
    dose = assess_dose(medication, dose_mg, doses_per_day, age, tags)
    if dose:
        if dose["severity"]:
            findings.append((dose["severity"], "[dose] " + dose["message"]))
        else:
            notes.append(dose["message"])
    if dose_mg and age is None and not (dose and dose["status"] == "NOT_ASSESSED"):
        notes.append("No age entered, so the dose was compared with adult limits.")

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
# STREAMLIT UI
# ----------------------------------------------------------------------------
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
