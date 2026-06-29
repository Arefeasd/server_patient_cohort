import polars as pl

def normalize_text_expr(col_name: str) -> pl.Expr:
    """
    Normalize a text column for easier pattern matching.
    
    The goal is to make French unit names easier to search by:
    - replacing missing values by empty strings;
    - converting text to lowercase;
    - removing common French accents;
    - standardizing spaces.
    """

    return (
        # Select the column to normalize
        pl.col(col_name)
        # Replace missing values by an empty string
        .fill_null("")
        # Make sure the column is treated as text
        .cast(pl.Utf8)
        # Replace French accented characters by non-accented characters
        .str.to_lowercase()
        .str.replace_all("é", "e")
        .str.replace_all("è", "e")
        .str.replace_all("ê", "e")
        .str.replace_all("ë", "e")
        .str.replace_all("à", "a")
        .str.replace_all("â", "a")
        .str.replace_all("ç", "c")
        .str.replace_all("ï", "i")
        .str.replace_all("î", "i")
        .str.replace_all("ô", "o")
        .str.replace_all("ù", "u")
        .str.replace_all("û", "u")
        # Replace multiple spaces by one single space
        .str.replace_all(r"\s+", " ")
        # Remove spaces at the beginning and at the end
        .str.strip_chars()
    )


def add_icu_unit_flag(
    unit_mapping: pl.DataFrame,
    unit_name_col: str = "unit_name",
    unit_group_col: str = "unit_group",
    output_col: str = "icu_unit_flag",
) -> pl.DataFrame:
    """
    Add an ICU flag to unit_mapping.

    A unit is ICU if:
    - it contains ICU-related terms;
    - it is not pediatric or neonatal.
    """

    icu_pattern = (
        r"reanimation|"
        r"soins intensifs|"
        r"soin intensif|"
        r"surveillance continue|"
        r"soins critiques|"
        r"soin critique|"
        r"medecine intensive reanimation|"
        r"\brea\b|"
        r"\busi\b|"
        r"\busc\b|"
        r"\busic\b|"
        r"\businv\b"
    )

    pediatric_pattern = (
        r"pediatr|"
        r"\bped\b|"
        r"neonat|"
        r"\bneona\b|"
        r"enfant|"
        r"nourrisson"
    )

    return (
        unit_mapping
        # Create temporary normalized text columns.
        # These columns are only used for pattern matching.
        .with_columns([
            normalize_text_expr(unit_name_col).alias("_unit_name_text"),
            normalize_text_expr(unit_group_col).alias("_unit_group_text"),
        ])
        # Create two temporary flags:
        # 1. _icu_candidate: unit looks like ICU
        # 2. _pediatric_unit: unit looks pediatric or neonatal
        .with_columns([
            (   # Check ICU-related words in the unit name
                pl.col("_unit_name_text").str.contains(icu_pattern)
                # Or check ICU-related words in the unit group
                | pl.col("_unit_group_text").str.contains(icu_pattern)
            ).alias("_icu_candidate"),

            (   
                # Check pediatric/neonatal words in the unit name
                pl.col("_unit_name_text").str.contains(pediatric_pattern)

                 # Or check pediatric/neonatal words in the unit group
                | pl.col("_unit_group_text").str.contains(pediatric_pattern)
            ).alias("_pediatric_unit"),
        ])
        # Final ICU flag:
        # ICU = candidate ICU unit AND not pediatric/neonatal.
        .with_columns(
            (
                pl.col("_icu_candidate")
                & ~pl.col("_pediatric_unit")
            )
            .cast(pl.Int8)
            .alias(output_col)
        )
        # Remove temporary columns.
        # They were only needed to construct the final ICU flag.
        .drop([
            "_unit_name_text",
            "_unit_group_text",
            "_icu_candidate",
            "_pediatric_unit",
        ])
    )


def add_icu_flag_to_stay(
    stay: pl.DataFrame,
    unit_mapping_icu: pl.DataFrame,
) -> pl.DataFrame:
    """
    Join ICU unit information to the stay table.

    The join is done using unit_code and centre.
    If a unit is not found in unit_mapping_icu, icu_unit_flag is set to 0.
    """

    stay_with_icu = (
        stay
        .join(
            unit_mapping_icu,
            how="left",
            on=["unit_code", "centre"]
        )
        .with_columns(
            pl.col("icu_unit_flag").fill_null(0)
        )
    )

    return stay_with_icu