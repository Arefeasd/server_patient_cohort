import polars as pl

def create_treatment_flags(df_tr: pl.DataFrame) -> pl.DataFrame:
    """
    Create binary treatment indicators from ATC codes.

    The function keeps only:
    patient_id, text_id, code_atc, and the six treatment flag columns.
    """

    # Standardize the ATC code:
    # - replace null values with an empty string
    # - convert all codes to uppercase
    # This avoids null results when checking code prefixes.
    df_tr = df_tr.with_columns(
        pl.col("code_atc") 
        .fill_null("")
        .str.to_uppercase()
        .alias("code_atc")
    )

# Create binary indicators based on the ATC code prefixes.
df_tr_flags = df_tr.with_columns([

    # Beta-blockers
    pl.col("code_atc")
    .str.starts_with("C07")
    .cast(pl.Int8)
    .alias("beta_blocker"),

    # ACE inhibitors: plain or combinations
    (
        pl.col("code_atc").str.starts_with("C09A") |
        pl.col("code_atc").str.starts_with("C09B")
    )
    .cast(pl.Int8)
    .alias("ACEI"),

    # ARBs: plain or combinations, excluding ARNI
    (
        (
            pl.col("code_atc").str.starts_with("C09C") |
            pl.col("code_atc").str.starts_with("C09D")
        )
        &
        (~pl.col("code_atc").str.starts_with("C09DX04"))
    )
    .cast(pl.Int8)
    .alias("ARB"),

    # ARNI: sacubitril/valsartan
    pl.col("code_atc")
    .str.starts_with("C09DX04")
    .cast(pl.Int8)
    .alias("ARNI"),

    # Aldosterone antagonists / MRA
    pl.col("code_atc")
    .str.starts_with("C03DA")
    .cast(pl.Int8)
    .alias("anti_aldosterone"),

    # SGLT2 inhibitors
    pl.col("code_atc")
    .str.starts_with("A10BK")
    .cast(pl.Int8)
    .alias("sglt2i"),

    # Furosemide
    pl.col("code_atc")
    .str.starts_with("C03CA01")
    .cast(pl.Int8)
    .alias("furosemide"),
])

    # Keep only the identifiers, the ATC code, and the newly created flags.
    df_tr_flags = df_tr_flags.select([
        "patient_id",
        "text_id",
        "ent_name",
        "code_atc",
        "dose",
        "frequency/duration",
        "beta_blocker",
        "ACEI",
        "ARB",
        "ARNI",
        "anti_aldosterone",
        "sglt2i",
        "furosemide",
    ])

    # Return the final dataframe.
    return df_tr_flags

def get_patient_treatment_flags(
    treatments_with_flags: pl.DataFrame
) -> pl.DataFrame:
    """
    Aggregate treatment flags at the patient level.

    Each patient may have several treatment records.
    For each treatment class, the output flag is 1 if the patient
    has at least one record with that treatment, otherwise 0.

    Parameters
    ----------
    treatments_with_flags : pl.DataFrame
        DataFrame containing one row per treatment record and binary
        treatment indicators.

    Returns
    -------
    pl.DataFrame
        DataFrame with one row per patient and one binary flag per
        treatment class.
    """

    patient_treatment_flags = (
        treatments_with_flags

        # Group all treatment records belonging to the same patient.
        .group_by("patient_id", maintain_order=True)

        # For each treatment flag, take the maximum value.
        # If at least one row has value 1, the patient-level flag becomes 1.
        .agg([
            pl.col("beta_blocker").max().alias("beta_blocker"),
            pl.col("ACEI").max().alias("ACEI"),
            pl.col("ARB").max().alias("ARB"),
            pl.col("ARNI").max().alias("ARNI"),
            pl.col("anti_aldosterone").max().alias("anti_aldosterone"),
            pl.col("sglt2i").max().alias("sglt2i"),
            pl.col("furosemide").max().alias("furosemide"),
        ])
    )

    # Return one row per patient.
    return patient_treatment_flags

drug_cols = ["beta_blocker", "ACEI", "ARB", "ARNI", "anti_aldosterone", "sglt2i", "furosemide"]

def get_patient_with_comorbidity_drug(
    included_patients_with_comorbidity: pl.DataFrame,
    patient_treatment_flags: pl.DataFrame,
    drug_cols: list[str]
) -> pl.DataFrame:
    """
    Add patient-level drug indicators to included patients.

    The input table already contains comorbidity indicators.
    The output keeps all included patients.
    Missing drug values are replaced by 0.
    """

    patient_with_comorbidity_drug = (
        # Start from included patients with comorbidities
        included_patients_with_comorbidity

        # Add drug indicators by patient_id
        .join(
            patient_treatment_flags,
            on="patient_id",
            how="left"
        )

        # Replace missing drug values by 0
        .with_columns([
            pl.col(col).fill_null(0).cast(pl.Int8)
            for col in drug_cols
        ])
    )

    return patient_with_comorbidity_drug