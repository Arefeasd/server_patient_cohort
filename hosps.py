import polars as pl

def get_hosp(
    stay_with_icu: pl.DataFrame
) -> pl.DataFrame:
    """
    Build a hospitalization-level table.

    The original stay table may contain several rows for the same hospitalization,
    because one patient can move between several hospital units.

    The output contains one row per hospitalization, identified by:
    patient_id + hosp_id + centre.

    inclusion_flag is equal to 1 if the hospitalization is an inclusion stay
    at least once.

    icu_stay_flag is equal to 1 if at least one unit during the hospitalization
    was identified as ICU.
    """

    hosp = (
        stay_with_icu
        .select(
            [
                "patient_id",
                "hosp_id",
                "centre",
                "hosp_admission_datetime",
                "hosp_discharge_datetime",
                "inclusion_flag",
                "icu_unit_flag",
            ]
        )
        .group_by(
            ["patient_id", "hosp_id", "centre"],
            maintain_order=True
        )
        .agg(
            [
                pl.col("hosp_admission_datetime")
                .min()
                .alias("hosp_admission_datetime"),

                pl.col("hosp_discharge_datetime")
                .max()
                .alias("hosp_discharge_datetime"),

                # If the same hospitalization appears both as antecedent and inclusion,
                # keep it as inclusion.
                pl.col("inclusion_flag")
                .max()
                .alias("inclusion_flag"),

                # ICU at hospitalization level
                pl.col("icu_unit_flag")
                .max()
                .alias("icu_stay_flag"),
            ]
        )
    )

    return hosp

def get_inclusion_hosps(
    hosp: pl.DataFrame
) -> pl.DataFrame:
    """
    Keep only inclusion hospitalizations.
    These are the hospitalizations where inclusion_flag == 1.
    """
    inclusion_hosps = hosp.filter(
        pl.col("inclusion_flag") == 1
    )
    return inclusion_hosps


def get_first_inclusion_hosps(
    inclusion_hosps: pl.DataFrame
) -> pl.DataFrame:
    """
    Select the first inclusion hospitalization for each patient.
    If a patient has more than one inclusion hospitalization,
    we keep the earliest one according to hosp_admission_datetime.
    """
    first_inclusion_hosps = (
        inclusion_hosps
    
        # Sort hospitalizations by patient and admission date.
        # For each patient, the earliest inclusion hospitalization comes first.
        .sort(["patient_id", "hosp_admission_datetime"])
    
        # Keep only one row per patient.
        # Because the table was sorted before,
        # keep="first" keeps the earliest inclusion hospitalization.
        .unique(
            subset=["patient_id"],
            keep="first"
        )
    )
    return first_inclusion_hosps


def get_preceding_hosps(
    hosp: pl.DataFrame
) -> pl.DataFrame:
    """
    Keep only non-inclusion hospitalizations.

    These are previous or other hospitalizations where inclusion_flag == 0.
    """
    preceding_hosps  = hosp.filter(pl.col("inclusion_flag") == 0)
    return preceding_hosps

def get_included_patients(
    first_inclusion_hosps: pl.DataFrame
) -> pl.DataFrame:
    """
    Get the list of included patients.

    Each patient appears only once.
    """
    included_patients = first_inclusion_hosps.select("patient_id").unique()
    return included_patients

def get_preceding_hosps_of_included_patients(
    preceding_hosps: pl.DataFrame,
    included_patients: pl.DataFrame
) -> pl.DataFrame:
    """
    Keep only non-inclusion hospitalizations belonging to included patients.

    This function joins preceding_hosps with the list of included patients
    using patient_id.
    """
    preceding_hosps_of_included_patients = (
        preceding_hosps
        .join(
            included_patients,
            on="patient_id",
            how="inner"
        )
    )
    return preceding_hosps_of_included_patients