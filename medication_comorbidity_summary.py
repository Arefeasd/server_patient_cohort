import polars as pl

def summarize_medications_by_comorbidity(
    df: pl.DataFrame,
    disease_cols: list[str],
    med_cols: list[str],
    omt_col: str = "OMT_component_score"
) -> pl.DataFrame:
    """
    Create a summary table for diseases, medication use, and OMT score.

    For each disease, the function calculates:
    - number of patients with the disease
    - percentage of all patients with the disease
    - percentage of patients with the disease who take each medication
    - minimum OMT component score among patients with the disease
    - maximum OMT component score among patients with the disease
    """

    total_patients = df.height

    result_rows = []

    for disease in disease_cols:

        patients_with_disease = df.filter(
            pl.col(disease) == 1
        )

        n_disease = patients_with_disease.height

        percent_disease = (
            n_disease / total_patients * 100
            if total_patients > 0
            else 0
        )

        row = {
            "Disease": disease,
            "Number of patients": n_disease,
            "Percent of all patients": percent_disease
        }

        for med in med_cols:

            n_med = patients_with_disease.filter(
                pl.col(med) == 1
            ).height

            percent_med = (
                n_med / n_disease * 100
                if n_disease > 0
                else 0
            )

            row[f"Percent taking {med}"] = percent_med

        # Add min and max OMT score among patients with this disease
        if n_disease > 0:
            row[f"Min {omt_col}"] = patients_with_disease.select(
                pl.col(omt_col).min()
            ).item()

            row[f"Max {omt_col}"] = patients_with_disease.select(
                pl.col(omt_col).max()
            ).item()
        else:
            row[f"Min {omt_col}"] = None
            row[f"Max {omt_col}"] = None

        result_rows.append(row)

    result = pl.DataFrame(result_rows)

    return result