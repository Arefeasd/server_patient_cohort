import polars as pl

def load_cim10(document_data: pl.DataFrame) -> pl.DataFrame:
    cim10 = (
        document_data
        .filter(pl.col("terminology_code").str.to_lowercase()  == "cim10")
        .select(["patient_id", "hosp_id", "concept_code", "centre"])
        .unique()
    )
    return cim10

def get_preceding_hosps_of_included_patients_with_cim10(
    preceding_hosps_of_included_patients: pl.DataFrame,
    cim10: pl.DataFrame
)-> pl.DataFrame:
    preceding_hosps_of_included_patients_with_cim10 = (
        preceding_hosps_of_included_patients
        .join(
            cim10,
            how = "left", 
            on = ["patient_id", "hosp_id", "centre"]
        )
    )
    return preceding_hosps_of_included_patients_with_cim10