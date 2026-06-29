import polars as pl
import json
import duckdb

def load_disease_dict(
    json_path: str
) -> dict:
    """
    Load disease dictionary from a JSON file.

    The JSON file contains diseases as keys and CIM-10 codes as values.
    """
    # Load the disease dictionary
    with open(json_path, 'r', encoding = 'utf-8') as f:
        data = json.load(f)
    disease_dict = {disease: list(codes.keys()) for disease, codes in data.items()}
    return disease_dict


def build_comorbidity_select_clauses(
    disease_dict: dict
) -> list[str]:
    """
    Build SQL clauses for comorbidity indicators.

    Each disease becomes one SQL expression using MAX(CASE WHEN ...).
    """
    # Construct the SQL select list
    select_clauses = []
    for disease, codes in disease_dict.items():
        # filter out empty codes
        valid_codes = [c for c in codes if c!=""]
        # Create a comma-seperated string of codes wrapped in single quotes 
        code_str = ", ".join([f"'{c}'" for c in valid_codes])
    
        # Format the SQL case
        if disease == 'Cancer actif':
            clause = "MAX(CASE WHEN concept_code LIKE 'C%' AND CAST(SUBSTR(concept_code, 2, 2) AS INTEGER) BETWEEN 0 and 97 THEN 1 ELSE 0 END) AS \"Cancer actif\""
        else: 
            clause = f"MAX(CASE WHEN concept_code IN ({code_str}) THEN 1 ELSE 0 END) AS \"{disease}\""
        select_clauses.append(clause)
    return select_clauses


def get_comorbidities(
    preceding_hosps_of_included_patients_with_cim10: pl.DataFrame,
    disease_dict: dict
) -> pl.DataFrame:
    """
    Create hospitalization-level comorbidity indicators.

    The input table contains previous hospitalizations of included patients
    joined with CIM-10 diagnosis codes.

    The output table has one row per hospitalization and one column per disease.
    """
    select_clauses = build_comorbidity_select_clauses(disease_dict)
    con = duckdb.connect()

    con.register(
        "preceding_hosps_of_included_patients_with_cim10",
        preceding_hosps_of_included_patients_with_cim10
    )
    query = f"""
    SELECT 
        p.patient_id,
        p.hosp_id,
        p.centre,
        p.inclusion_flag,
        p.hosp_admission_datetime,
        p.hosp_discharge_datetime,	
        p.icu_stay_flag,
        {", ".join(select_clauses)}
    FROM preceding_hosps_of_included_patients_with_cim10 AS p
    GROUP BY 
        p.patient_id,
        p.hosp_id,
        p.centre,
        p.inclusion_flag,
        p.hosp_admission_datetime,
        p.hosp_discharge_datetime,	
        p.icu_stay_flag
    """
    comorbidities = con.execute(query).pl()

    con.close()

    return comorbidities


disease_cols = ["Cardiopathie ischémique", "Fibrillation atriale", "Insuffisance cardiaque chronique",
               "Pacemaker", "Pontage aorto-coronarien", "Insuffisance rénale chronique", "Antécédent d'AVC",
               "Cirrhose", "Cancer actif", "Immunodépression", "Dyslipidémie", "Diabète"]

def get_patient_comorbidities(
    comorbidities: pl.DataFrame
) -> pl.DataFrame:
    """
    Aggregate comorbidity indicators at the patient level.

    The input table may contain several rows for the same patient,
    because each row can correspond to a previous hospitalization
    or a previous medical record.

    For each patient and for each disease column, the function keeps
    the maximum value.

    Since disease columns are binary indicators:
        1 = the disease is present
        0 = the disease is absent

    taking the maximum means:
        - if the disease appears at least once for the patient,
          the final value is 1;
        - if the disease never appears for the patient,
          the final value is 0.

    The output contains one row per patient_id.
    """
    # Aggregate comorbidities at patient level
    patient_comorbidities = (
        comorbidities
        # Group all previous hospitalizations of the same patient
        .group_by("patient_id")
        # For each disease, keep 1 if it appears at least once
        .agg([
            pl.col(col).max().alias(col)
            for col in disease_cols
        ])
    )
    return patient_comorbidities


def get_included_patients_with_comorbidity(
    first_inclusion_hosps: pl.DataFrame,
    patient_comorbidities: pl.DataFrame,
    disease_cols: list[str]
) -> pl.DataFrame:

    """
    Add patient-level comorbidity indicators to included patients.

    The output keeps all included patients.
    Missing comorbidity values are replaced by 0.
    """

    # Build the final patient-level table
    included_patient_with_comorbidity = (
    
        # Start with one row per included patient
        first_inclusion_hosps
    
        # Add previous comorbidities by patient_id
        .join(
            patient_comorbidities,
            on="patient_id",
            how="left"  # keep all included patients
        )
    
        # Replace missing disease values by 0
        # and store them as small integers
        .with_columns([
            pl.col(col).fill_null(0).cast(pl.Int8)
            for col in disease_cols
        ])
    )
    return included_patient_with_comorbidity

    