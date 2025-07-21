"""
reddithandler.py - handles reddit
"""

# standard includes
from collections import Counter
import datetime
import io
import logging
import os
from openpyxl import load_workbook
import pandas as pd
import shutil
import pickle
import praw
import re
import time

# module configs
import config.main as config

# local modules
import src.errorhandler as eh

# reddit handler class
# this class handles the reddit posts data


class UpdateHandler:
    def __init__(
        self,
        template_dir=config.updates.template_directory,
        result_dir=config.updates.result_directory,
        vblth=config.verbose_threshold,
        dblth=config.debug_threshold,
    ):
        self.class_name = "UpdateHandler"
        self.template_directory = template_dir
        self.result_dir = result_dir
        self.vblth = vblth
        self.dblth = dblth

    def read_pickles(self, directory=config.reddit.work_directory):
        """read all pkl files from a given directory"""
        method_name = "read_pickles"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - reading pickle files from [{directory}]:",
        )
        data_list = []
        error_count = 0
        file_count = 0
        for filename in os.listdir(directory):
            if filename.endswith(".pkl") or filename.endswith(".pickle"):
                file_count += 1
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - read [{filename}] ... ",
                    end="",
                )
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, "rb") as f:
                        data = pickle.load(f)
                        data_list.append(data)
                    eh.verbose_print(self.vblth, f"[done]")
                except Exception as e:
                    error_count += 1
                    eh.verbose_print(
                        self.vblth, f"[ERROR]\nERROR reading {filename}: {e}"
                    )
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - read {file_count} file(s) with {error_count} error(s):",
        )
        if error_count != 0:
            method_status = -1
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return data_list

    def create_dataframe(self, data_list):
        "create new dataframe with dynamic columns for all symbols"
        method_name = "read_pickles"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - create dataframe ... ",
            end="",
        )
        df = None
        all_symbols = set()
        rows = []
        for entry in data_list:
            if "results" not in entry:
                eh.verbose_print(
                    self.vblth,
                    f"[ERROR] - 'results' key not found in entry: {entry}",
                )
                continue
            all_symbols.update(entry["results"].keys())
        all_symbols = sorted(all_symbols)

        for entry in data_list:
            if "results" not in entry:
                eh.verbose_print(
                    self.vblth,
                    f"[ERROR] - 'results' key not found in entry: {entry}",
                )
                continue
            row = {acronym: 0 for acronym in all_symbols}
            row.update(entry["results"])
            row["run_id"] = entry["run_id"]
            rows.append(row)

        df = pd.DataFrame(rows, columns=["run_id"] + list(all_symbols))
        df["date"] = df["run_id"].apply(lambda x: x[:6])
        df["time"] = df["run_id"].apply(lambda x: x[7:])
        df = df.sort_values(by=["date", "time"]).drop(columns=["date", "time"])
        df = df.reset_index(drop=True)
        eh.verbose_print(
            self.vblth, f"[done, {df.shape[0]} row(s), {df.shape[1]} column(s)"
        )
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return df

    def update_results(self, df, template_path=None, result_path=None) -> int:
        "update a preformatted Excel template with new data"
        method_name = "read_pickles"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth, f"{self.class_name}.{method_name} - update results:"
        )
        try:
            if template_path is None:
                template_path = os.path.join(
                    config.updates.template_directory,
                    config.updates.excel_template_name,
                )
            if result_path is None:
                result_path = os.path.join(
                    config.updates.result_directory, config.updates.excel_result_name
                )
            template_name = os.path.basename(template_path)
            result_name = os.path.basename(result_path)
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template file not found: {template_path}")
            os.makedirs(os.path.dirname(result_path), exist_ok=True)
            # copy template to result path
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - copy template {template_name} -> {result_name} ... ",
                end="",
            )
            shutil.copy2(template_path, result_path)
            eh.verbose_print(self.vblth, f"[done]")

            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - read and verify {result_name} ... ",
                end="",
            )
            wb = load_workbook(result_path)
            ws = wb.active
            # check header presence
            existing_headers = []
            if ws.max_row >= 1:
                for col in range(1, ws.max_column + 1):
                    cell_value = ws.cell(row=1, column=col).value
                    if cell_value:
                        existing_headers.append(str(cell_value))
            eh.verbose_print(self.vblth, f"[done]")
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - existing headers: \n. {existing_headers}",
            )
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - DataFrame columns: \n {list(df.columns)}",
            )

            # remove old data
            if ws.max_row > 1:
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - delete old data ... ",
                    end="",
                )
                ws.delete_rows(2, ws.max_row - 1)
                eh.verbose_print(self.vblth, f"[done]")

            # update headers if necessary
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - update header ... ",
                end="",
            )
            for col_idx, column_name in enumerate(df.columns, 1):
                ws.cell(row=1, column=col_idx, value=column_name)
            eh.verbose_print(self.vblth, f"[done]")

            # insert new data
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - insert new data ... ",
                end="",
            )
            for row_idx, (_, row_data) in enumerate(df.iterrows(), 2):
                for col_idx, value in enumerate(row_data.values, 1):
                    ws.cell(row=row_idx, column=col_idx, value=value)
            eh.verbose_print(
                self.vblth, f"[done,#{len(df)} row(s), {len(df.columns)} column(s)]"
            )

            # save updated result
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - save updated result as {result_name} ... ",
                end="",
            )
            wb.save(result_path)
            eh.verbose_print(self.vblth, f"[done]")
        except Exception as e:
            method_status = -1
            eh.verbose_print(1, "[ERROR]")
            eh.verbose_print(
                1, f"{self.class_name}.{method_name} - exception occurred: {e}"
            )
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status

    def pickle_to_result(self):
        "read pickle files and update result from an excel template with the data"
        method_name = "pickle_to_result"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(self.vblth, f"{self.class_name}.{method_name} - start:")
        # read pickle files
        data_list = self.read_pickles()
        if not data_list:
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - no pickle files found, aborting",
            )
            return None
        # create DataFrame
        df = self.create_dataframe(data_list)
        if df is None or df.empty:
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - DataFrame creation failed, aborting",
            )
            return None
        # update results from excel template
        success = self.update_results(df)

        if success:
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - DataFrame generated, header:\n{df.head()}",
            )
        else:
            method_status = -1
            df = None
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return df
