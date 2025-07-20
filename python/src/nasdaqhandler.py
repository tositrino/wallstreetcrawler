"""
nasdaq data handler

"""

# standard modules
import importlib
import logging
from pathlib import Path

# special modules (requirements)
import os
import pandas as pd
import pickle
import re
import requests
import time

# module configs
import config.main as config

# local modules
import src.errorhandler as eh


def drop_duplicates_with_word_comparison(
    df,
    subset=None,
    compare_words=0,
    case_sensitive=True,
    keep="first",
    inplace=False,
    ignore_index=False,
):
    """
    Drop duplicate rows based on partial word comparison in specified columns.

    This function extends pandas' drop_duplicates by allowing comparison of only
    the first N words in string columns, with optional case-insensitive matching.

    Parameters:
    -----------
    df : pandas.DataFrame
        The DataFrame to process
    subset : column label or sequence of labels, optional
        Only consider certain columns for identifying duplicates.
        If None, use all columns.
    compare_words : int, default 0
        Number of words to compare for duplicity detection.
        - If <= 0: compare all words (standard behavior)
        - If > number of words in text: compare all available words
    case_sensitive : bool, default True
        Whether the comparison should be case sensitive
    keep : {'first', 'last', False}, default 'first'
        Determines which duplicates (if any) to keep
    inplace : bool, default False
        Whether to modify the DataFrame in place or return a new one
    ignore_index : bool, default False
        If True, the resulting axis will be labeled 0, 1, …, n - 1

    Returns:
    --------
    pandas.DataFrame or None
        DataFrame with duplicates removed, or None if inplace=True

    Examples:
    ---------
    >>> df = pd.DataFrame({
    ...     'name': ['Apple Inc Corporation', 'Apple Inc Corp', 'Microsoft Corporation', 'Google LLC'],
    ...     'symbol': ['AAPL', 'AAPL2', 'MSFT', 'GOOGL']
    ... })
    >>>
    >>> # Compare only first 2 words, case insensitive
    >>> result = drop_duplicates_with_word_comparison(df, subset=['name'], compare_words=2, case_sensitive=False)
    >>> print(result)
    """

    # Create a copy if not inplace
    if inplace:
        result_df = df
    else:
        result_df = df.copy()

    # If subset is None, use all columns
    if subset is None:
        subset = df.columns.tolist()

    # Ensure subset is a list
    if isinstance(subset, str):
        subset = [subset]

    # If compare_words <= 0, use standard drop_duplicates
    if compare_words <= 0:
        return df.drop_duplicates(
            subset=subset, keep=keep, inplace=inplace, ignore_index=ignore_index
        )

    # Create temporary columns for comparison
    temp_columns = []

    for col in subset:
        if col not in df.columns:
            raise KeyError(f"Column '{col}' not found in DataFrame")

        temp_col_name = f"_temp_comparison_{col}"
        temp_columns.append(temp_col_name)

        # Process each value in the column
        processed_values = []

        for value in df[col]:
            if pd.isna(value):
                # Handle NaN values
                processed_values.append(value)
            elif isinstance(value, str):
                # Split into words (handling multiple spaces, tabs, etc.)
                words = re.split(r"\s+", value.strip())

                # Take only the specified number of words
                if compare_words > len(words):
                    selected_words = words  # Use all available words
                else:
                    selected_words = words[:compare_words]

                # Join back and apply case sensitivity
                processed_value = " ".join(selected_words)
                if not case_sensitive:
                    processed_value = processed_value.lower()

                processed_values.append(processed_value)
            else:
                # For non-string values, convert to string and process
                str_value = str(value)
                words = re.split(r"\s+", str_value.strip())

                if compare_words > len(words):
                    selected_words = words
                else:
                    selected_words = words[:compare_words]

                processed_value = " ".join(selected_words)
                if not case_sensitive:
                    processed_value = processed_value.lower()

                processed_values.append(processed_value)

        # Add temporary column to result_df
        result_df[temp_col_name] = processed_values

    # Apply drop_duplicates on temporary columns
    result_df = result_df.drop_duplicates(
        subset=temp_columns, keep=keep, inplace=False, ignore_index=ignore_index
    )

    # Remove temporary columns
    result_df = result_df.drop(columns=temp_columns)

    # Handle inplace parameter
    if inplace:
        df.drop(df.index, inplace=True)
        df.update(result_df)
        df.reset_index(drop=True, inplace=True)
        return None
    else:
        return result_df


def download_and_process_nasdaq_listings(
    url=config.nasdaq.source_url,
    target_dir=config.nasdaq.work_directory,
    file_name=config.nasdaq.original_file_name,
    result_name=config.nasdaq.result_file_name,
    add_prefix=config.nasdaq.add_dollar_sign,
):
    """
    Download NASDAQ listings CSV, process it, and save in multiple formats.
    """
    fn_name = "download_and_process_nasdaq_listings"
    fn_start = time.time()
    fn_status = 0
    eh.verbose_print(
        1,
        f"{__name__}.{fn_name} - start:",
    )
    try:
        # make sure the target directory exists
        if os.path.exists(target_dir):
            eh.debug_print(
                1, f"{__name__}.{fn_name} - target directory [{target_dir}] exists"
            )
        else:  # create target directory if it does not exist
            eh.debug_print(
                1,
                f"{__name__}.{fn_name} - target directory [{target_dir}] does not exist, creating it",
            )
            os.makedirs(target_dir, exist_ok=True)

        original_csv = os.path.join(target_dir, f"{file_name}.csv")
        if not os.path.exists(original_csv) or config.force_mode:
            # Download the CSV file
            eh.verbose_print(
                1,
                f"{__name__}.{fn_name} - download data from {url}  ... ",
                end="",
            )
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes

            # Save the downloaded content
            with open(original_csv, "wb") as f:
                f.write(response.content)
            eh.verbose_print(1, "[done]")

        # Read the CSV file
        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - reading data from [{original_csv}] ... ",
            end="",
        )
        df = pd.read_csv(original_csv, encoding="utf-8", low_memory=False)
        eh.verbose_print(1, "[done]")

        eh.verbose_print(
            1, f"{__name__}.{fn_name} - original dataset contains {len(df)} records"
        )
        eh.verbose_print(1, f"{__name__}.{fn_name} - columns {list(df.columns)}")

        # create excel file from original data
        original_xlsx = os.path.join(target_dir, f"{file_name}.xlsx")
        if not os.path.exists(original_xlsx) or config.force_mode:
            eh.verbose_print(
                1,
                f"{__name__}.{fn_name} - creating excel file [{original_xlsx} ] from data ... ",
                end="",
            )
            df.to_excel(original_xlsx, index=False)
            eh.verbose_print(1, "[done]")

        # Filter out ETF entries (where ETF property is 'Y')
        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - filter out ETF entries ... ",
            end="",
        )
        df_filtered = df[df["ETF"] != "Y"].copy()
        eh.verbose_print(1, f"[done, {len( df_filtered)} records remaining]")

        # Remove duplicates based on Company Name, keeping first occurrence
        print("Removing duplicate company names...")
        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - removing duplicate entries for company name ... ",
            end="",
        )
        # df_final = df_filtered.drop_duplicates(subset=["Company Name"], keep="first")
        df_final = drop_duplicates_with_word_comparison(
            df_filtered,
            subset=["Company Name"],
            compare_words=config.nasdaq.compare_words,
            case_sensitive=config.nasdaq.compare_case_sensitive,
            keep="first",
            inplace=False,
            ignore_index=True,
        )
        eh.verbose_print(1, f"[done, {len(df_final)} records remaining]")

        if add_prefix:
            # Add a dollar sign prefix to the Symbol column
            eh.verbose_print(
                1,
                f"{__name__}.{fn_name} - adding dollar sign prefix to Symbol column ... ",
                end="",
            )
            df_final["Symbol"] = "$" + df_final["Symbol"].astype(str)
            # df_final["Symbol"] = df_final["Symbol"].apply(
            #    lambda x: f"${x}" if isinstance(x, str) else x
            # )
            eh.verbose_print(1, "[done]")

        # Save the final dataset as csv file
        result_csv = os.path.join(target_dir, f"{result_name}.csv")
        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - saving cleaned data as csv file [{result_csv}] ... ",
            end="",
        )
        df_final.to_csv(result_csv, index=False)
        eh.verbose_print(1, f"[done]")

        # save the final dataset as excel file
        result_xlsx = os.path.join(target_dir, f"{result_name}.xlsx")
        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - saving cleaned data as excel file [{result_xlsx}] ... ",
            end="",
        )
        df_final.to_excel(result_xlsx, index=False)
        eh.verbose_print(1, f"[done]")

        # Save the final cleaned dataset as pickle file
        result_pkl = os.path.join(target_dir, f"{result_name}.pkl")
        config.nasdaq.pkl_file_name = result_pkl
        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - saving cleaned data as pickle file [{result_pkl}] ... ",
            end="",
        )
        symbols_list = df.iloc[0:, 0].dropna().tolist()
        # Save the symbols list as a pickle file
        pickle.dump(symbols_list, open(result_pkl, "wb"))
        eh.verbose_print(1, f"[done]")

        if config.debug_level > 0:
            eh.debug_print(
                1,
                f"{__name__}.{fn_name} - debug mode enabled, load and show pickle content:",
            )
            eh.debug_print(1, f" final data frame head:\n{df_final.head}")
            eh.debug_print(1, f":load and show pickle content ... ", end="")
            with open(result_pkl, "rb") as f:
                pkl_data = pickle.load(f)
            eh.verbose_print(1, f"[done]\n{pkl_data}")

        #  clean up temporary file
        # os.remove("temp_nasdaq.csv")
        eh.verbose_print(1, f"{__name__}.{fn_name} - process completed successfully!")
        eh.verbose_print(1, "\nProcess completed successfully!")
        eh.verbose_print(1, f"Files created:")
        eh.verbose_print(1, f"- {original_csv} ({len(df)} records)")
        eh.verbose_print(1, f"- {original_xlsx} ({len(df)} records)")
        eh.verbose_print(1, f"- {result_csv} ({len(df_final)} records)")
        eh.verbose_print(1, f"- {result_xlsx} ({len(df_final)} records)")
        eh.verbose_print(1, f"- {result_pkl} ({len(symbols_list)} records)")

        # Show some statistics
        eh.verbose_print(1, f"\nSummary:")
        eh.verbose_print(1, f"- Original records: {len(df)}")
        eh.verbose_print(1, f"- ETF entries removed: {len(df) - len(df_filtered)}")
        eh.verbose_print(
            1, f"- Duplicate company names removed: {len(df_filtered) - len(df_final)}"
        )
        eh.verbose_print(1, f"- Final records: {len(df_final)}")

    except requests.exceptions.RequestException as e:
        fn_status = -1
        print(f"Error downloading file: {e}")
    except pd.errors.EmptyDataError:
        fn_status = -1
        print("Error: The downloaded file is empty or corrupted")
    except KeyError as e:
        fn_status = -1
        print(f"Error: Expected column not found in CSV: {e}")
        print(
            "Available columns:",
            list(df.columns) if "df" in locals() else "Could not read CSV",
        )
    except Exception as e:
        fn_status = -1
        print(f"An unexpected error occurred: {e}")

    fn_elapsed = time.time() - fn_start
    eh.verbose_print(
        1,
        f"{__name__}.{fn_name} - finisshed, duration={fn_elapsed:2.4f} second(s), status={fn_status}:",
    )
