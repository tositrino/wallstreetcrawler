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

# helper functions
# helper function to drop duplicates based on word comparison
# this function extends pandas' drop_duplicates by allowing comparison of only the first N words in string  columns
# with optional case-insensitive matching


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


# nasdaq handler class
# this class handles the download and processing of the nasdaq data


class NasdaqHandler:
    def __init__(
        self,
        url=config.nasdaq.source_url,
        target_dir=config.nasdaq.work_directory,
        file_name=config.nasdaq.original_file_name,
        result_name=config.nasdaq.result_file_name,
        add_prefix=config.nasdaq.add_dollar_sign,
        vblth=config.verbose_threshold,
        dblth=config.debug_threshold,
    ):
        self.class_name = "NasdaqHandler"
        self.url = url
        self.target_dir = target_dir
        self.file_name = file_name
        self.result_name = result_name
        self.add_prefix = add_prefix
        self.vblth = vblth
        self.dblth = dblth
        self.original_csv = None
        self.result_csv = None
        self.original_xlsx = None
        self.result_xlsx = None
        self.result_pkl = None
        self.df = None
        self.df_filtered = None
        self.df_final = None
        self.symbols_list = None

    def download_and_prepare(self):
        """
        download and prepare nasdaq data and save it
        """
        method_name = "download_and_prepare"
        method_start = time.time()
        method_status = 0

        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - start:",
        )
        try:
            # make sure the target directory exists
            if os.path.exists(self.target_dir):
                eh.debug_print(
                    self.dblth,
                    f"{self.class_name}.{method_name} - target directory [{self.target_dir}] exists",
                )
            else:  # create target directory if it does not exist
                eh.debug_print(
                    self.dblth,
                    f"{self.class_name}.{method_name} - target directory [{self.target_dir}] does not exist, creating it",
                )
                os.makedirs(self.target_dir, exist_ok=True)

            # download the csv file
            self.original_csv = os.path.join(self.target_dir, f"{self.file_name}.csv")
            if not os.path.exists(self.original_csv) or config.force_mode:
                # Download the CSV file
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - download data from {self.url}  ... ",
                    end="",
                )
                response = requests.get(self.url)
                response.raise_for_status()  # Raise an exception for bad status codes

                # Save the downloaded content
                with open(self.original_csv, "wb") as f:
                    f.write(response.content)
                eh.verbose_print(self.vblth, "[done]")

            # Read the CSV file
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - reading data from [{self.original_csv}] ... ",
                end="",
            )
            self.df = pd.read_csv(self.original_csv, encoding="utf-8", low_memory=False)
            eh.verbose_print(self.vblth, "[done]")

            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - original dataset contains {len(self.df)} records",
            )
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - columns {list(self.df.columns)}",
            )

            # create excel file from original data
            self.original_xlsx = os.path.join(self.target_dir, f"{self.file_name}.xlsx")
            if not os.path.exists(self.original_xlsx) or config.force_mode:
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - creating excel file [{self.original_xlsx} ] from data ... ",
                    end="",
                )
                self.df.to_excel(self.original_xlsx, index=False)
                eh.verbose_print(self.vblth, "[done]")

            # Filter out ETF entries (where ETF property is 'Y')
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - filter out ETF entries ... ",
                end="",
            )
            self.df_filtered = self.df[self.df["ETF"] != "Y"].copy()
            eh.verbose_print(
                self.vblth, f"[done, {len( self.df_filtered)} records remaining]"
            )

            # Remove duplicates based on Company Name, keeping first occurrence
            print("Removing duplicate company names...")
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - removing duplicate entries for company name ... ",
                end="",
            )
            # self.df_final = df_filtered.drop_duplicates(subset=["Company Name"], keep="first")
            self.df_final = drop_duplicates_with_word_comparison(
                self.df_filtered,
                subset=["Company Name"],
                compare_words=config.nasdaq.compare_words,
                case_sensitive=config.nasdaq.compare_case_sensitive,
                keep="first",
                inplace=False,
                ignore_index=True,
            )
            eh.verbose_print(
                self.vblth, f"[done, {len(self.df_final)} records remaining]"
            )

            if self.add_prefix:
                # Add a dollar sign prefix to the Symbol column
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - adding dollar sign prefix to Symbol column ... ",
                    end="",
                )
                self.df_final["Symbol"] = "$" + self.df_final["Symbol"].astype(str)
                # df_final["Symbol"] = df_final["Symbol"].apply(
                #    lambda x: f"${x}" if isinstance(x, str) else x
                # )
                eh.verbose_print(self.vblth, "[done]")

            # Save the final dataset as csv file
            self.result_csv = os.path.join(self.target_dir, f"{self.result_name}.csv")
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - saving cleaned data as csv file [{self.result_csv}] ... ",
                end="",
            )
            self.df_final.to_csv(self.result_csv, index=False)
            eh.verbose_print(self.vblth, f"[done]")

            # save the final dataset as excel file
            self.result_xlsx = os.path.join(self.target_dir, f"{self.result_name}.xlsx")
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - saving cleaned data as excel file [{self.result_xlsx}] ... ",
                end="",
            )
            self.df_final.to_excel(self.result_xlsx, index=False)
            eh.verbose_print(self.vblth, f"[done]")

            # Save the final cleaned dataset as pickle file
            self.result_pkl = os.path.join(self.target_dir, f"{self.result_name}.pkl")
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - saving cleaned symbol data as pickle file [{self.result_pkl}] ... ",
                end="",
            )
            symbols_list = self.df.iloc[0:, 0].dropna().tolist()
            # Save the symbols list as a pickle file
            pickle.dump(symbols_list, open(self.result_pkl, "wb"))
            eh.verbose_print(self.vblth, f"[done]")

            if config.debug_level > 0:
                eh.debug_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - debug mode enabled, load and show pickle content:",
                )
                eh.debug_print(
                    self.vblth, f" final data frame head:\n{self.df_final.head}"
                )
                eh.debug_print(
                    self.vblth, f":load and show pickle content ... ", end=""
                )
                with open(self.result_pkl, "rb") as f:
                    pkl_data = pickle.load(f)
                eh.verbose_print(self.vblth, f"[done]\n{pkl_data}")

            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - process completed successfully!",
            )

        except requests.exceptions.RequestException as e:
            method_status = -1
            print(f"Error downloading file: {e}")
        except pd.errors.EmptyDataError:
            method_status = -1
            print("Error: The downloaded file is empty or corrupted")
        except KeyError as e:
            method_status = -1
            print(f"Error: Expected column not found in CSV: {e}")
            print(
                "Available columns:",
                list(self.df.columns) if "df" in locals() else "Could not read CSV",
            )
        except Exception as e:
            method_status = -1
            print(f"An unexpected error occurred: {e}")

        self.summary()
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )

    def summary(self):
        """
        Print a summary of the downloaded and processed data.
        """
        eh.verbose_print(
            self.vblth,
            f"{self.class_name} - Summary of downloaded and processed data:",
        )
        original_records = len(self.df) if self.df is not None else 0
        filtered_records = len(self.df_filtered) if self.df_filtered is not None else 0
        final_records = len(self.df_final) if self.df_final is not None else 0
        symbol_records = len(self.symbols_list) if self.symbols_list is not None else 0
        eh.verbose_print(self.vblth, f"Files created:")
        eh.verbose_print(
            self.vblth, f"- {self.original_csv} (#{original_records} record(s))"
        )
        eh.verbose_print(
            self.vblth, f"- {self.original_xlsx} (#{original_records} record(s))"
        )
        eh.verbose_print(
            self.vblth, f"- {self.result_csv} (#{final_records} record(s))"
        )
        eh.verbose_print(
            self.vblth, f"- {self.result_xlsx} (#{final_records} record(s))"
        )
        eh.verbose_print(
            self.vblth, f"- {self.result_pkl} (#{symbol_records} record(s))"
        )

        eh.verbose_print(self.vblth, f"Records processed:")
        eh.verbose_print(self.vblth, f"- Original records: #{original_records}")
        eh.verbose_print(
            self.vblth,
            f"- ETF entries removed: #{ original_records - filtered_records}",
        )
        eh.verbose_print(
            self.vblth,
            f"- Duplicate company names removed: #{filtered_records - final_records}",
        )
        eh.verbose_print(self.vblth, f"- Final records: #{final_records}")
