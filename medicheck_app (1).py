"""
Medication Safety Checker - single-file Streamlit app
  Tab 1: Combination checker (Duplication alarm + Interaction alarm)
  Tab 2: Condition & dose checker (dosage meter + caution score)
  Tab 3: Rulebook & sources (live statistics, JSON export for pharmacist review)

Setup:   pip install streamlit
Run:     streamlit run medicheck_app.py
On Streamlit Cloud: upload ONLY this file, plus a requirements.txt
containing the line:  streamlit

Educational tool only - not medical advice.
"""
import streamlit as st

import difflib
import json
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
    "macrolide": ["clarithromycin", "erythromycin", "azithromycin"],
    "diuretic": ["furosemide", "hydrochlorothiazide", "hctz", "torsemide"],
    "k_sparing": ["spironolactone", "amiloride", "triamterene"],
    "benzodiazepine": ["diazepam", "alprazolam", "lorazepam", "clonazepam"],
    "ccb_rate": ["verapamil", "diltiazem"],
    "bronchodilator": ["salbutamol", "albuterol", "levosalbutamol", "ventolin"],
    "thyroid": ["levothyroxine", "thyroxine", "eltroxin"],
    "polyvalent_cation": ["antacid", "gaviscon", "aluminium hydroxide",
                          "magnesium hydroxide", "calcium", "magnesium", "iron",
                          "ferrous sulfate", "zinc"],
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
    "benzodiazepine": [
        ("respiratory", "AVOID", "Benzodiazepines can slow breathing further."),
        ("myasthenia", "AVOID", "Can worsen muscle weakness in myasthenia gravis."),
        ("alcohol", "AVOID", "Alcohol plus benzodiazepines can dangerously slow breathing."),
        ("dementia", "CAUTION", "Higher risk of confusion and falls."),
        ("pregnancy", "CAUTION", "Risks and benefits must be weighed by your doctor."),
    ],
}

# Drug-drug interactions between classes (checked against "other medicines")
INTERACTIONS = [
    # (class set A, class set B, severity, explanation, kind)
    # kind: "toxic" = harmful together, "reduced" = one weakens the other, "both"
    ({"nsaid", "aspirin"}, {"warfarin"}, "AVOID",
     "Greatly increases the risk of serious bleeding.", "toxic"),
    ({"nsaid", "aspirin"}, {"ace_inhibitor", "diuretic", "beta_blocker"}, "CAUTION",
     "Painkillers like this can weaken blood-pressure medicines and strain the kidneys.", "both"),
    ({"nsaid", "aspirin"}, {"ssri"}, "CAUTION",
     "Increases the risk of stomach bleeding.", "toxic"),
    ({"nsaid", "aspirin"}, {"steroid"}, "CAUTION",
     "Both irritate the stomach; together they raise ulcer and bleeding risk.", "toxic"),
    ({"nsaid"}, {"aspirin"}, "CAUTION",
     "Taking two NSAID-type painkillers together raises stomach and kidney risks.", "toxic"),
    ({"pde5"}, {"nitrate"}, "AVOID",
     "Can cause a life-threatening drop in blood pressure.", "toxic"),
    ({"ssri"}, {"opioid"}, "CAUTION",
     "Risk of serotonin syndrome (and seizures with tramadol).", "toxic"),
    ({"ssri"}, {"maoi"}, "AVOID",
     "Risk of life-threatening serotonin syndrome.", "toxic"),
    ({"opioid"}, {"maoi"}, "AVOID",
     "Risk of serotonin syndrome / severe reactions.", "toxic"),
    ({"decongestant"}, {"maoi"}, "AVOID",
     "Risk of dangerous blood pressure spikes.", "toxic"),
    ({"warfarin"}, {"fluoroquinolone", "penicillin", "macrolide"}, "CAUTION",
     "Antibiotics can raise INR (blood thinness) and bleeding risk.", "toxic"),
    ({"warfarin"}, {"ssri"}, "CAUTION",
     "Both increase bleeding risk.", "toxic"),
    ({"warfarin"}, {"paracetamol"}, "CAUTION",
     "Regular high-dose paracetamol can raise INR and bleeding risk.", "toxic"),
    ({"beta_blocker"}, {"beta_blocker"}, "CAUTION",
     "Two beta-blockers together is unusual; confirm with a doctor.", "toxic"),
    ({"beta_blocker"}, {"ccb_rate"}, "AVOID",
     "Can slow the heart too much (heart block) and drop blood pressure.", "toxic"),
    ({"beta_blocker"}, {"bronchodilator"}, "CAUTION",
     "Beta-blockers can block the effect of salbutamol-type inhalers; the two work against each other.", "reduced"),
    ({"beta_blocker"}, {"decongestant"}, "CAUTION",
     "Decongestants raise blood pressure and work against beta-blockers.", "both"),
    ({"ace_inhibitor"}, {"steroid"}, "CAUTION",
     "Steroids can blunt blood-pressure control.", "reduced"),
    ({"ace_inhibitor"}, {"k_sparing"}, "AVOID",
     "Can cause dangerously high potassium; only combined with doctor-monitored blood tests.", "toxic"),
    ({"ace_inhibitor"}, {"diuretic"}, "CAUTION",
     "Can drop blood pressure and affect the kidneys, especially if dehydrated.", "toxic"),
    ({"opioid"}, {"benzodiazepine"}, "AVOID",
     "Together they can cause dangerous sedation and slowed breathing.", "toxic"),
    ({"opioid", "benzodiazepine"}, {"antihistamine_1"}, "CAUTION",
     "Adds drowsiness and can slow breathing and coordination.", "toxic"),
    ({"fluoroquinolone"}, {"steroid"}, "CAUTION",
     "Raises the risk of tendon inflammation and rupture.", "toxic"),
    ({"fluoroquinolone"}, {"metformin"}, "CAUTION",
     "Can cause blood sugar swings in people taking diabetes medicines.", "toxic"),
    ({"fluoroquinolone"}, {"polyvalent_cation"}, "CAUTION",
     "Antacids, iron, calcium, zinc or magnesium bind the antibiotic so it is absorbed poorly. "
     "Usually take the antibiotic at least 2 hours before or 6 hours after them (check the leaflet).", "reduced"),
    ({"thyroid"}, {"polyvalent_cation"}, "CAUTION",
     "Calcium, iron and antacids block thyroid-hormone absorption; separate them by about 4 hours.", "reduced"),
    ({"macrolide"}, {"statin"}, "CAUTION",
     "Can raise statin levels and the risk of muscle damage (mainly clarithromycin/erythromycin).", "toxic"),
    ({"macrolide"}, {"fluoroquinolone"}, "CAUTION",
     "Both can disturb heart rhythm (QT prolongation).", "toxic"),
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
    for a, b, severity, reason, _kind in INTERACTIONS:
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


def format_report(verdict, findings, notes, medication, score=None):
    lines = [f"Medication: {medication}", "", VERDICT_TEXT[verdict], ""]
    if score:
        lines += [f"Caution score: {score['score']}% ({score['level']})",
                  "(rough illustrative estimate, not a medical probability)", ""]
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
# CAUTION SCORE (0-100%)
# A rough, illustrative heuristic - NOT a clinical probability of harm.
#   * every finding adds a risk weight (AVOID ~75%, CAUTION ~20%)
#   * weights are scaled by the DOSE LEVEL (daily total vs usual adult max):
#       low dose -> x0.8, at the maximum -> x1.1, 150% of max -> x1.25
#     (allergy reactions are not scaled; they are not dose-dependent)
#   * the dose itself adds risk: a little when within limits, a lot when over
#   * weights are combined so they never exceed 100%
# ----------------------------------------------------------------------------


def score_level(score):
    if score is None:
        return "Unknown"
    if score < 20:
        return "Low"
    if score < 45:
        return "Moderate"
    if score < 70:
        return "High"
    return "Very high"


def caution_score(verdict, findings, dose=None):
    """Return {"score": int 0-100, "level": str, "parts": [(label, pct)]} or None."""
    if verdict == "UNKNOWN":
        return None

    ratio = None
    if dose and dose.get("daily_max"):
        ratio = dose["daily_total"] / dose["daily_max"]
    factor = 1.0 if ratio is None else 0.8 + 0.3 * min(ratio, 1.5)

    parts = []
    for sev, text in findings:
        m = re.match(r"\[(.*?)\]", text)
        tag = m.group(1) if m else ""
        if tag == "dose":
            continue                      # dose is handled separately below
        if tag == "allergy":
            w = 0.85
        else:
            w = (0.75 if sev == "AVOID" else 0.20) * factor
        label = text if len(text) <= 85 else text[:82] + "..."
        parts.append((label, min(w, 0.97)))

    if ratio is not None:
        pct_of_max = f"{ratio:.0%} of the usual adult daily maximum"
        if dose["status"] == "OVER_DAILY":
            w = min(0.90, 0.55 + 0.6 * (ratio - 1))
        elif dose["status"] == "OVER_SINGLE":
            w = 0.30
        else:
            w = 0.08 * ratio
        parts.append((f"Dose level: {dose['daily_total']:g} mg/day = {pct_of_max}", w))

    keep = 1.0
    for _, w in parts:
        keep *= (1 - w)
    score = round(100 * (1 - keep))

    # keep the number consistent with the verdict banner
    if verdict == "AVOID":
        score = max(score, 60)
    elif verdict == "CAUTION":
        score = min(max(score, 15), 59)
    score = max(0, min(100, score))

    return {"score": score, "level": score_level(score),
            "parts": [(l, round(100 * w)) for l, w in parts]}


def full_check(conditions, medication, age=None, allergies="", other_meds="",
               dose_mg=None, doses_per_day=None):
    """check() + dose assessment + caution score, all in one dict."""
    verdict, findings, notes = check(conditions, medication, age, allergies,
                                     other_meds, dose_mg, doses_per_day)
    dose = assess_dose(medication, dose_mg, doses_per_day, age,
                       find_condition_tags(conditions))
    return {"verdict": verdict, "findings": findings, "notes": notes,
            "dose": dose, "score": caution_score(verdict, findings, dose)}



# ----------------------------------------------------------------------------
# COMBINATION CHECKER: Duplication alarm + Interaction alarm
# ----------------------------------------------------------------------------
INGREDIENT_ALIASES = {
    **DOSE_ALIASES,
    "augmentin": "amoxicillin", "amoxyclav": "amoxicillin", "co-amoxiclav": "amoxicillin",
    "avil": "chlorpheniramine", "coumadin": "warfarin",
    "acetylsalicylic acid": "aspirin", "gtn": "nitroglycerin",
    "glyceryl trinitrate": "nitroglycerin", "ventolin": "salbutamol",
    "albuterol": "salbutamol", "thyroxine": "levothyroxine", "eltroxin": "levothyroxine",
    "hctz": "hydrochlorothiazide",
}

LABEL_OVERRIDES = {
    "calcium": "Calcium supplement", "iron": "Iron supplement",
    "zinc": "Zinc supplement", "magnesium": "Magnesium supplement",
    "antacid": "Antacid (any)", "hctz": "HCTZ",
}

# Pick-lists hold these as plain placeholders, so keep them out of the dropdown
_HIDDEN_OPTIONS = {"nsaid", "nitrate"}

# Medicines of the same group do the same job - taking two is a duplication.
DUPLICATION_GROUPS = [
    ("NSAID-type painkillers", {"nsaid", "aspirin"},
     "Both are anti-inflammatory painkillers. Doubling up adds stomach-bleeding, kidney and "
     "heart risks without more pain relief. (Low-dose aspirin prescribed for the heart is a "
     "separate matter - ask your doctor.)"),
    ("Statins", {"statin"},
     "Two statins together greatly raise the risk of muscle damage and liver injury."),
    ("ACE inhibitors / ARBs", {"ace_inhibitor"},
     "Both block the same blood-pressure hormone system. Combining them raises the risk of "
     "kidney problems, high potassium and very low blood pressure."),
    ("Beta-blockers", {"beta_blocker"},
     "Two beta-blockers can slow the heart dangerously and drop blood pressure."),
    ("SSRI antidepressants", {"ssri"},
     "Two antidepressants of this type risk serotonin syndrome (agitation, fever, fast heartbeat)."),
    ("Opioid painkillers", {"opioid"},
     "Opioids add up: risk of slowed breathing and overdose."),
    ("Fluoroquinolone antibiotics", {"fluoroquinolone"},
     "Two of these antibiotics double the tendon, nerve and seizure risks with no added benefit."),
    ("Penicillin antibiotics", {"penicillin"},
     "They do the same job; doubling up only increases side effects and allergy risk."),
    ("Macrolide antibiotics", {"macrolide"},
     "Two of these antibiotics add heart-rhythm and stomach side effects with no added benefit."),
    ("Corticosteroids", {"steroid"},
     "Two steroids add up: fluid retention, high blood sugar, mood changes and infection risk."),
    ("Erectile-dysfunction (PDE5) drugs", {"pde5"},
     "Taking two can cause a dangerous drop in blood pressure."),
    ("Sedating antihistamines", {"antihistamine_1"},
     "Two add up: heavy drowsiness, confusion, dry mouth and urinary retention."),
    ("Decongestants", {"decongestant"},
     "Two add up: high blood pressure, racing heart and tremor."),
    ("MAOIs", {"maoi"},
     "Two MAOIs together risk dangerous blood pressure spikes and serotonin syndrome."),
    ("Benzodiazepines", {"benzodiazepine"},
     "Two add up: heavy sedation and slowed breathing."),
]


def ingredient_of(name):
    name = name.lower().strip()
    return INGREDIENT_ALIASES.get(name, name)


def pretty(name):
    return LABEL_OVERRIDES.get(name, name.title())


def combo_options():
    """Dropdown options: {label shown to user: lookup key}."""
    options = {}
    for names in MED_CLASSES.values():
        for n in names:
            if n in _HIDDEN_OPTIONS:
                continue
            ing = ingredient_of(n)
            label = pretty(n) if ing == n else f"{pretty(n)} ({ing})"
            options[label] = n
    return dict(sorted(options.items()))


KIND_TEXT = {"toxic": "Toxic mix", "reduced": "Reduced effect (they work against each other)",
             "both": "Toxic mix + reduced effect"}


def check_combination(selected):
    """
    selected: list of medicine names/keys (as returned by combo_options()).
    Returns dict: verdict (STOP / CAUTION / SAFE / NEED_MORE),
                  duplicates [..], interactions [..]
    Each alarm entry: {"sev": "AVOID"|"CAUTION", "drugs": str, "text": str, "kind": str}
    """
    items = [(n, ingredient_of(n), find_med_class(n)) for n in selected]
    duplicates, interactions = [], []
    flagged = set()          # index pairs already reported as duplicates

    # Duplication alarm, part 1: the same active ingredient under two names
    by_ing = {}
    for idx, (n, ing, _cls) in enumerate(items):
        by_ing.setdefault(ing, []).append(idx)
    for ing, idxs in by_ing.items():
        if len(idxs) > 1:
            text = (f"These contain the same active ingredient ({ing}). "
                    "Taking both doubles your dose and can cause an overdose.")
            if ing == "paracetamol":
                text += (" Paracetamol overdose can seriously damage the liver even "
                         "when it feels like normal use.")
            duplicates.append({"sev": "AVOID", "kind": "duplicate",
                               "drugs": " + ".join(pretty(items[i][0]) for i in idxs),
                               "text": text})
            for a in idxs:
                for b in idxs:
                    if a < b:
                        flagged.add((a, b))

    # Duplication alarm, part 2: different medicines that do the same job
    for gname, classes, reason in DUPLICATION_GROUPS:
        members = [i for i, (_n, _ing, cls) in enumerate(items) if cls in classes]
        if len({items[i][1] for i in members}) > 1:
            duplicates.append({"sev": "AVOID", "kind": "duplicate",
                               "drugs": " + ".join(pretty(items[i][0]) for i in members),
                               "text": f"{gname}: {reason}"})
            for a in members:
                for b in members:
                    if a < b and items[a][1] != items[b][1]:
                        flagged.add((a, b))

    # Interaction alarm: pairs that become toxic or cancel each other out
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if (i, j) in flagged:
                continue
            ci, cj = items[i][2], items[j][2]
            if ci is None or cj is None:
                continue
            for a, b, sev, reason, kind in INTERACTIONS:
                if (ci in a and cj in b) or (ci in b and cj in a):
                    interactions.append({
                        "sev": sev, "kind": kind, "text": reason,
                        "drugs": f"{pretty(items[i][0])} + {pretty(items[j][0])}"})
                    break

    allf = duplicates + interactions
    if len(items) < 2:
        verdict = "NEED_MORE"
    elif any(f["sev"] == "AVOID" for f in allf):
        verdict = "STOP"
    elif allf:
        verdict = "CAUTION"
    else:
        verdict = "SAFE"
    return {"verdict": verdict, "duplicates": duplicates, "interactions": interactions}


def combo_score(result):
    """Combination risk score 0-100% (same illustrative method as caution_score)."""
    verdict = {"STOP": "AVOID", "CAUTION": "CAUTION", "SAFE": "NO_CONFLICT"}.get(result["verdict"])
    if verdict is None:
        return None
    findings = [(f["sev"], f"[combo] {f['drugs']}: {f['text']}")
                for f in result["duplicates"] + result["interactions"]]
    return caution_score(verdict, findings)


def format_combo_report(selected, result, score=None):
    lines = ["MEDICINE COMBINATION REPORT", "=" * 40,
             "Medicines: " + ", ".join(pretty(n) for n in selected), ""]
    lines.append({"STOP": "RESULT: STOP - dangerous combination found.",
                  "CAUTION": "RESULT: CAUTION - check with a doctor or pharmacist.",
                  "SAFE": "RESULT: NO CONFIGURED ALERT FOUND - no rule in this app's rulebook flagged this selection. This does not guarantee the combination is safe.",
                  "NEED_MORE": "RESULT: select at least two medicines."}[result["verdict"]])
    if score:
        lines.append(f"Combination risk score: {score['score']}% ({score['level']})")
    for title, entries in (("DUPLICATION ALARM", result["duplicates"]),
                           ("INTERACTION ALARM", result["interactions"])):
        lines += ["", title + (": clear" if not entries else ": TRIGGERED")]
        for f in entries:
            tag = "STOP" if f["sev"] == "AVOID" else "CAUTION"
            kind = KIND_TEXT.get(f["kind"], "")
            lines.append(f"  [{tag}] {f['drugs']}" + (f"  ({kind})" if kind else ""))
            lines.append(f"         {f['text']}")
    lines += ["", DISCLAIMER]
    return "\n".join(lines)



# ----------------------------------------------------------------------------
# TRANSPARENCY + USABILITY HELPERS (rulebook stats/export, "did you mean")
# ----------------------------------------------------------------------------
CLASS_DISPLAY = {
    "nsaid": "NSAID painkiller", "aspirin": "Aspirin (antiplatelet / painkiller)",
    "paracetamol": "Paracetamol", "metformin": "Metformin (diabetes)",
    "penicillin": "Penicillin antibiotic", "beta_blocker": "Beta-blocker",
    "ace_inhibitor": "ACE inhibitor / ARB", "statin": "Statin",
    "decongestant": "Decongestant", "antihistamine_1": "Sedating antihistamine",
    "warfarin": "Warfarin (blood thinner)", "ssri": "SSRI antidepressant",
    "opioid": "Opioid painkiller", "fluoroquinolone": "Fluoroquinolone antibiotic",
    "steroid": "Corticosteroid", "pde5": "PDE5 inhibitor", "nitrate": "Nitrate",
    "maoi": "MAOI", "macrolide": "Macrolide antibiotic", "diuretic": "Diuretic",
    "k_sparing": "Potassium-sparing diuretic", "benzodiazepine": "Benzodiazepine",
    "ccb_rate": "Rate-limiting calcium-channel blocker",
    "bronchodilator": "Bronchodilator inhaler", "thyroid": "Thyroid hormone",
    "polyvalent_cation": "Antacid / mineral supplement",
}


def rulebook_stats():
    n_rules = sum(len(v) for v in RULES.values())
    n_avoid = sum(1 for v in RULES.values() for _t, sev, _x in v if sev == "AVOID")
    return {
        "Drug classes": len(MED_CLASSES),
        "Drug names and brands (class lookup)": sum(len(v) for v in MED_CLASSES.values()),
        "Medicines in the combination dropdown": len(combo_options()),
        "Condition categories": len(CONDITION_TAGS),
        "Condition trigger phrases": sum(len(v) for v in CONDITION_TAGS.values()),
        "Condition rules": n_rules,
        "   of which AVOID": n_avoid,
        "   of which CAUTION": n_rules - n_avoid,
        "Drug-drug interaction rules": len(INTERACTIONS),
        "Duplication groups": len(DUPLICATION_GROUPS),
        "Brand-to-ingredient aliases": len(INGREDIENT_ALIASES),
        "Adult dose limits": len(DOSE_LIMITS),
    }


def rulebook_json():
    """Whole rulebook as JSON so a pharmacist can review it without reading code.
    Every rule has EMPTY 'source' and 'reviewed_by_pharmacist' fields to be filled in
    during validation - no citations are invented here."""
    review = {"source": "", "reviewed_by_pharmacist": False}
    data = {
        "note": "Educational prototype rulebook. NOT clinically validated.",
        "drug_classes": {c: {"label": CLASS_DISPLAY.get(c, c), "names": n}
                         for c, n in MED_CLASSES.items()},
        "ingredient_aliases": INGREDIENT_ALIASES,
        "condition_phrases": CONDITION_TAGS,
        "condition_rules": [
            {"drug_class": c, "condition": t, "severity": sev, "explanation": x, **review}
            for c, rules in RULES.items() for t, sev, x in rules],
        "interaction_rules": [
            {"class_a": sorted(a), "class_b": sorted(b), "severity": sev,
             "explanation": x, "kind": k, **review}
            for a, b, sev, x, k in INTERACTIONS],
        "duplication_groups": [
            {"group": g, "classes": sorted(c), "explanation": x, **review}
            for g, c, x in DUPLICATION_GROUPS],
        "adult_dose_limits_mg": {
            d: {"max_single_mg": lim[0], "max_daily_mg": lim[1], **review}
            for d, lim in DOSE_LIMITS.items()},
    }
    return json.dumps(data, indent=2)


def suggest_medicines(text, n=3):
    """'Did you mean' for a misspelt medicine name (never auto-corrects)."""
    text = text.lower().strip()
    if len(text) < 3:
        return []
    candidates = set(DOSE_LIMITS) | set(DOSE_ALIASES) | set(INGREDIENT_ALIASES)
    for names in MED_CLASSES.values():
        candidates |= {x for x in names if x not in _HIDDEN_OPTIONS}
    return [pretty(m) for m in difflib.get_close_matches(text, sorted(candidates), n=n, cutoff=0.7)]


def suggest_conditions(text):
    """Return [(typed, suggestion)] for condition phrases that matched nothing."""
    phrases = sorted({p for ps in CONDITION_TAGS.values() for p in ps})
    out = []
    for seg in re.split(r",|;|\band\b|\n", text.lower()):
        seg = seg.strip()
        if len(seg) < 5 or find_condition_tags(seg):
            continue
        match = difflib.get_close_matches(seg, phrases, n=1, cutoff=0.8)
        if match:
            out.append((seg, match[0]))
    return out



# ----------------------------------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Medication Safety Checker", page_icon="💊")

st.markdown("""
<style>
@keyframes stopflash { 0%,100% {opacity:1;} 50% {opacity:.55;} }
.mc-banner { color:white; padding:22px 14px; border-radius:14px; text-align:center; margin:8px 0 14px 0; }
.mc-stop { background:#c0392b; animation: stopflash 1.1s ease-in-out infinite; }
.mc-caution { background:#d68910; }
.mc-safe { background:#1e8449; }
.mc-title { font-size:44px; font-weight:800; line-height:1.1; }
.mc-title-sm { font-size:30px; font-weight:800; line-height:1.15; }
.mc-sub { font-size:16px; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

st.title("💊 Medication Safety Checker")
st.caption("Educational tool only - not medical advice.")

tab_combo, tab_cond, tab_rules = st.tabs(
    ["🚦 Combination checker", "🩺 Condition & dose checker", "📚 Rulebook & sources"])


def banner(css, icon, title, sub, small=False):
    tcls = "mc-title-sm" if small else "mc-title"
    st.markdown(
        f"<div class='mc-banner {css}'><div class='{tcls}'>{icon} {title}</div>"
        f"<div class='mc-sub'>{sub}</div></div>",
        unsafe_allow_html=True,
    )


def alarm_panel(title, entries):
    if not entries:
        st.success(f"🟢 {title}: clear")
        return
    st.error(f"🔴 {title}: TRIGGERED")
    for e in entries:
        icon = "🛑" if e["sev"] == "AVOID" else "⚠️"
        kind = KIND_TEXT.get(e["kind"], "")
        st.markdown(f"**{icon} {e['drugs']}**" + (f"  \n*{kind}*" if kind else ""))
        st.markdown(e["text"])


# =========================== TAB 1: COMBINATION ===========================
with tab_combo:
    st.markdown("Pick every medicine you are about to take. The app checks them "
                "against its safety rulebook instantly.")

    OPTIONS = combo_options()                      # label -> key
    NAME_TO_LABEL = {v: k for k, v in OPTIONS.items()}
    EXAMPLES = {
        "Aspirin + Ibuprofen": ["aspirin", "ibuprofen"],
        "Tylenol + Paracetamol": ["tylenol", "paracetamol"],
        "Sildenafil + Nitroglycerin": ["sildenafil", "nitroglycerin"],
        "Paracetamol + Ibuprofen": ["paracetamol", "ibuprofen"],
    }

    def set_example(names):
        st.session_state["combo_sel"] = [NAME_TO_LABEL[n] for n in names]

    st.caption("Try an example:")
    ex_cols = st.columns(len(EXAMPLES))
    for col, (lbl, names) in zip(ex_cols, EXAMPLES.items()):
        col.button(lbl, on_click=set_example, args=(names,), key="ex_" + lbl)

    chosen = st.multiselect("Medicines you are about to take", list(OPTIONS), key="combo_sel")

    if chosen:
        st.table([{"Selected medicine": l,
                   "Active ingredient": pretty(ingredient_of(OPTIONS[l])),
                   "Drug group": CLASS_DISPLAY.get(find_med_class(OPTIONS[l]), "-")}
                  for l in chosen])

    if len(chosen) < 2:
        st.info("Select at least two medicines to run the safety check.")
    else:
        keys = [OPTIONS[l] for l in chosen]
        res = check_combination(keys)
        csc = combo_score(res)
        n_alarms = len(res["duplicates"]) + len(res["interactions"])

        if res["verdict"] == "STOP":
            banner("mc-stop", "🛑", "STOP - REVIEW THIS COMBINATION",
                   f"{n_alarms} configured rule(s) triggered. Read the explanation below and "
                   "consult a pharmacist or clinician before taking these together.",
                   small=True)
        elif res["verdict"] == "CAUTION":
            banner("mc-caution", "⚠️", "CAUTION",
                   "Possible problem found. Check with your doctor or pharmacist "
                   "before taking these together.")
        else:
            banner("mc-safe", "✅", "NO CONFIGURED ALERT FOUND",
                   "No rule in the current dataset flagged this selection. "
                   "This does not guarantee the combination is safe - confirm with a pharmacist.",
                   small=True)

        a1, a2 = st.columns(2)
        with a1:
            st.markdown("#### Duplication alarm")
            st.caption("Two pills that do the same thing can cause an overdose.")
            alarm_panel("Duplication", res["duplicates"])
        with a2:
            st.markdown("#### Interaction alarm")
            st.caption("Drugs that turn toxic or cancel each other out.")
            alarm_panel("Interaction", res["interactions"])

        if csc:
            st.subheader("Combination risk score")
            m1, m2 = st.columns([1, 2])
            with m1:
                st.metric("Overall", f"{csc['score']}%", csc["level"], delta_color="off")
            with m2:
                st.progress(csc["score"] / 100)
                st.caption("0-19% Low  |  20-44% Moderate  |  45-69% High  |  70%+ Very high")
            st.caption("Rough illustrative estimate, not a medical probability of harm.")

        st.download_button(
            "Download this report (.txt)",
            data=format_combo_report(keys, res, csc),
            file_name="medicine_combination_report.txt",
        )


# ======================= TAB 2: CONDITION & DOSE ==========================
with tab_cond:
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
            dose_in = dose_mg if dose_mg > 0 else None
            r = full_check(conditions, medication, age, allergies, other_meds, dose_in, times)
            verdict, findings, notes, d, sc = (r["verdict"], r["findings"], r["notes"],
                                               r["dose"], r["score"])

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
                sug = suggest_medicines(medication)
                if sug:
                    st.warning("Did you mean: " + ", ".join(sug) + " ?  Re-type the name and check again.")

            for typed, sugg in suggest_conditions(conditions):
                st.caption(f"Condition not recognised: '{typed}'. Did you mean '{sugg}'?")

            if sc:
                st.subheader("Caution score")
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("Overall", f"{sc['score']}%", sc["level"], delta_color="off")
                with c2:
                    st.progress(sc["score"] / 100)
                    st.caption("0-19% Low  |  20-44% Moderate  |  45-69% High  |  70%+ Very high")
                if sc["parts"]:
                    with st.expander("What makes up this score?"):
                        for label, pct in sc["parts"]:
                            st.markdown(f"- **{pct}%** - {label}")
                        st.caption("Higher doses raise the weight of dose-related risks. "
                                   "Individual weights are combined, not simply added.")
                st.caption("The score is a rough illustrative estimate, not a medical "
                           "probability of harm.")

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
                st.code(format_report(verdict, findings, notes, medication.strip(), sc))

# ========================= TAB 3: RULEBOOK & SOURCES ======================
with tab_rules:
    st.markdown("Nothing is hidden: this is everything the app currently knows. "
                "The rulebook has **not** been clinically validated yet.")
    st.table([{"Item": k, "Count": v} for k, v in rulebook_stats().items()])
    st.download_button(
        "Download rulebook (JSON) for pharmacist review",
        data=rulebook_json(),
        file_name="medicheck_rulebook.json",
        mime="application/json",
    )
    st.caption("Every rule in the file has empty 'source' and 'reviewed_by_pharmacist' fields, "
               "to be filled in during validation.")
    with st.expander("Sources the rules should be validated against"):
        st.markdown(
            "- NHS Medicines A to Z - https://www.nhs.uk/medicines/\n"
            "- British National Formulary (BNF), NICE / Royal Pharmaceutical Society\n"
            "- MedlinePlus Drug Information - https://medlineplus.gov/druginformation.html\n"
            "- U.S. FDA drug labelling (Drugs@FDA)"
        )

st.divider()
st.caption(DISCLAIMER)
