import polars as pl
def get_patients_with_death_date(patient):
    patients = (
    patient.select(
            [
                "patient_id",
                "gender",
                "birth_date",
                "internal_death_date",
                "external_death_date",
            ]
        )
    )
    # consolidate death_age
    patients = patients.with_columns(
        pl.coalesce(["external_death_date", "internal_death_date"]).alias("death_date")
    ).select(["patient_id", "gender", "birth_date", "death_date"])
    return patients


def age_at_admission(included_patient_with_comorbidity_drug_demo):
    included_patient_with_comorbidity_drug_demo = included_patient_with_comorbidity_drug_demo.with_columns(
        (
            (pl.col("hosp_admission_datetime") - pl.col("birth_date")).dt.total_days()
            / 365.25
        )
        .floor()
        .cast(pl.Int32)
        .alias("age_at_admission")
    )
    return included_patient_with_comorbidity_drug_demo