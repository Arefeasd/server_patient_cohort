import polars as pl
import pandas as pd
import json 
from pycomorb import comorbidity
import icu_flag
import hosps
import cim10_utils
import comorbidity_utils
import drug
import patient_utils

unit_mapping = pl.read_parquet("unit_mapping.parquet")
stay = pl.read_parquet("stay.parquet")
patient = pl.read_parquet("patient.parquet")
document_data = pl.read_parquet("document_data.parquet")
treatments = pl.read_parquet("traitement.parquet")

# Add an ICU flag to unit_mapping.
unit_mapping_icu = icu_flag.add_icu_unit_flag(unit_mapping)

# Join the ICU information to the stay table.
stay_with_icu = icu_flag.add_icu_flag_to_stay(stay, unit_mapping_icu)

# Build a hospitalization-level table.
# The original stay table may contain several rows for the same hospitalization,
# because one patient can move between several units during one hospital stay.
hosp = hosps.get_hosp(stay_with_icu)

# Keep only inclusion hospitalizations.
# These are the hospitalizations where inclusion_flag == 1.
inclusion_hosps = hosps.get_inclusion_hosps(hosp)

# Select the first inclusion hospitalization for each patient.
# If a patient has more than one inclusion hospitalization,
# we keep the earliest one according to hosp_admission_datetime.
first_inclusion_hosps = hosps.get_first_inclusion_hosps(inclusion_hosps)

# Keep only hospital stays before the inclusion stay.
preceding_hosps = hosps.get_preceding_hosps(hosp)

# Get the unique list of patients with an inclusion hospital stay.
included_patients = hosps.get_included_patients(first_inclusion_hosps)

# Keep only preceding hospital stays belonging to included patients.
preceding_hosps_of_included_patients = hosps.get_preceding_hosps_of_included_patients(preceding_hosps, included_patients)

# Extract unique CIM-10 diagnosis codes with patient, hospital stay, and centre identifiers.
cim10 = cim10_utils.load_cim10(document_data)

# Add CIM-10 diagnosis codes to the preceding hospital stays of included patients.
preceding_hosps_of_included_patients_with_cim10 = cim10_utils.get_preceding_hosps_of_included_patients_with_cim10(preceding_hosps_of_included_patients, cim10)

# Load the disease dictionary
disease_dict = comorbidity_utils.load_disease_dict('cim10_nancy.json')

# Create one comorbidity indicator per disease for each preceding hospitalization.
comorbidities = comorbidity.get_comorbidities(
    preceding_hosps_of_included_patients_with_cim10,
    disease_dict
)

# Convert hospitalization-level comorbidity flags into patient-level comorbidity flags.
# For each patient, each disease flag is 1 if the disease appears in at least
# one previous hospitalization, otherwise 0.
patient_comorbidities = comorbidity.get_patient_comorbidities(comorbidities)

disease_cols = ["Cardiopathie ischémique", "Fibrillation atriale", "Insuffisance cardiaque chronique",
               "Pacemaker", "Pontage aorto-coronarien", "Insuffisance rénale chronique", "Antécédent d'AVC",
               "Cirrhose", "Cancer actif", "Immunodépression", "Dyslipidémie", "Diabète"]

# Add patient-level comorbidity flags to the first inclusion hospital stay table.
included_patients_with_comorbidity =comorbidity.get_included_patients_with_comorbidity(
    first_inclusion_hosps,
    patient_comorbidities,
    disease_cols
)

# Create binary treatment flags from ATC codes for each treatment record.
treatments_with_flags = drug.create_treatment_flags(treatments)

# Convert treatment records into patient-level treatment indicators.
# For each patient, each treatment flag is 1 if the patient has at least
# one medication record from that treatment class, otherwise 0.
patient_treatment_flags = drug.get_patient_treatment_flags(treatments_with_flags)

patient_with_comorbidity_drug = included_patients_with_comorbidity.join(
    patient_treatment_flags,
    on = "patient_id",
    how = "inner"
)

patient_with_death_date = patient_utils.get_patients_with_death_date(patient)

patient_with_comorbidity_drug_demo = patient_with_comorbidity_drug.join(
    patient_with_death_date,
    on = 
)