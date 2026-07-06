import polars as pl

def summarize_medications_by_comorbidity(
    df: pl.DataFrame,
    disease_cols: list[str],
    med_cols: list[str]
) -> pl.DataFrame:
    """
    Create a summary table for diseases and medication use.

    For each disease, the function calculates:
    - number of patients with the disease
    - percentage of all patients with the disease
    - percentage of patients with the disease who take each medication
    """

    # Total number of patients
    total_patients = df.height

    # Empty list to store rows
    result_rows = []

    # Loop over each disease
    for disease in disease_cols:

        # Keep only patients who have this disease
        patients_with_disease = df.filter(
            pl.col(disease) == 1
        )

        # Number of patients with this disease
        n_disease = patients_with_disease.height

        # Percentage of all patients with this disease
        percent_disease = n_disease / total_patients * 100

        # Create one row for this disease
        row = {
            "Disease": disease,
            "Number of patients": n_disease,
            "Percent of all patients": percent_disease
        }

        # Loop over each medication
        for med in med_cols:

            # Number of patients with this disease who also take this medication
            n_med = patients_with_disease.filter(
                pl.col(med) == 1
            ).height

            # Percentage among patients with this disease
            if n_disease > 0:
                percent_med = n_med / n_disease * 100
            else:
                percent_med = 0

            # Add this percentage to the row
            row[f"Percent taking {med}"] = percent_med

        # Add this row to the final result
        result_rows.append(row)

    # Convert result to Polars DataFrame
    result = pl.DataFrame(result_rows)

    return result