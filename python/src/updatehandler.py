"""
updatehandler.py - handles data updates
"""

# standard includes
from collections import Counter, OrderedDict
from docx import Document
from docx.shared import Pt
import datetime
import glob
import io
import logging
import os
from openpyxl import load_workbook
import pandas as pd
import pickle
import shutil
import re
import time

# module configs
import config.main as config

# local modules
import src.errorhandler as eh

# update handler class
# this class handles data updates


class UpdateHandler:
    def __init__(
        self,
        template_dir=config.updates.template_directory,
        result_dir=config.updates.result_directory,
        hotleads_input_dir=config.reddit.work_directory,
        hotleads_input_prefix=config.reddit.result_file_name_prefix,
        hotleads_dir=config.updates.hotleads_directory,
        hotleads_prefix=config.reddit.result_file_name_prefix,
        posts_dir=config.reddit.posts_directory,
        posts_prefix=config.reddit.post_file_name_prefix,
        vblth=config.verbose_threshold,
        dblth=config.debug_threshold,
    ):
        self.class_name = "UpdateHandler"
        self.template_directory = template_dir
        self.result_directory = result_dir
        self.hotleads_input_directory = hotleads_input_dir
        self.hotleads_input_prefix = hotleads_input_prefix
        self.hotleads_directory = hotleads_dir
        self.hotleads_prefix = hotleads_prefix
        self.posts_directory = posts_dir
        self.posts_prefix = posts_prefix
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

    def read_latest_symbol_data(
        self, directory=config.reddit.work_directory, latest_files=3
    ):
        """read the latest symbols from pickle files in a given directory"""
        method_name = "read_latest_symbols"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - reading latest symbol data from [{directory}]:",
        )
        files = []
        data_list = []
        run_ids = []
        results_list = []
        error_count = 0
        file_count = 0
        for filename in os.listdir(directory):
            if filename.endswith(".pkl") or filename.endswith(".pickle"):
                files.append(filename)

        if len(files) == 0:
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - no pickle files found in {directory}",
            )
        else:
            files_sorted = sorted(files, reverse=True)
            files = []
            for file in files_sorted:
                file_count += 1
                files.append(file)
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - read [{file}] ... ",
                    end="",
                )
                filepath = os.path.join(directory, file)
                try:
                    with open(filepath, "rb") as f:
                        data = pickle.load(f)
                        data_list.append(data)
                    eh.verbose_print(self.vblth, f"[done]")
                except Exception as e:
                    error_count += 1
                    eh.verbose_print(self.vblth, f"[ERROR]\nERROR reading {file}: {e}")
                if latest_files > 0 and file_count >= latest_files:
                    eh.verbose_print(
                        self.vblth,
                        f"{self.class_name}.{method_name} - reached limit of {latest_files} files, stopping",
                    )
                    break
        # reorder results
        files = files[::-1]
        data_list = data_list[::-1]
        run_ids = [d["run_id"] for d in data_list]
        results_list = [d["results"] for d in data_list]
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
        return method_status, files, data_list, run_ids, results_list

    def create_dataframe(self, data_list):
        "create new dataframe with dynamic columns for all symbols"
        method_name = "create_dataframe"
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
                    f"[ERROR] - 'results' key not found in entry:\n  {str(entry)[:50]} ...",
                )
                continue
            all_symbols.update(entry["results"].keys())
        all_symbols = sorted(all_symbols)

        for entry in data_list:
            if "results" not in entry:
                eh.verbose_print(
                    self.vblth,
                    f"[ERROR] - 'results' key not found in entry:\n  {str(entry)[:50]} ...",
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

    def save_excel_result(self, df, template_path=None, result_path=None) -> int:
        "update and save results as excel file from a a preformatted template"
        method_name = "save_excel_result"
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
                f"{self.class_name}.{method_name} - existing headers: \n  {existing_headers}",
            )
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - dataFrame columns: \n  {list(df.columns)}",
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

    def pickles_to_excel_result(self):
        "read pickle files and update result from an excel template with the data"
        method_name = "pickles_to_excel_result"
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
        success = self.save_excel_result(df)

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

    def save_word_result(self, hits, file_name):
        """update and save latest results as word document and pickle file"""
        method_name = "save_word_result"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth, f"{self.class_name}.{method_name} - saving files ... :"
        )
        try:
            # generate prefix from pkl filename
            prefix = os.path.basename(file_name).split("_")[0]
            # save as docx
            doc = Document()
            doc.add_heading("matches from pickle files", level=1)
            for symbol, data in hits.items():
                doc.add_heading(symbol, level=2)
                for run_id, value in zip(data["run_ids"], data["values"]):
                    p = doc.add_paragraph(f"{run_id}: {value}")
                    p.style.font.size = Pt(12)
                doc.add_paragraph("")
            # save docx file
            docx_filename = os.path.join(
                self.result_directory, f"{prefix}_hotleads.docx"
            )
            doc.save(docx_filename)
            # save pickle file
            pickle_filename = os.path.join(
                self.result_directory, f"{prefix}_hotleads.pkl"
            )
            with open(pickle_filename, "wb") as f:
                pickle.dump(hits, f)
        except Exception as e:
            method_status = -1
            eh.verbose_print(1, f"[ERROR]\nERROR - exception occurred: {e}")
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status

    def pickles_to_word_result(self):
        "read pickle files, update result and save as word document"
        method_name = "pickles_to_word_result"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(self.vblth, f"{self.class_name}.{method_name} - start:")
        # read pickle files
        hits = None
        status, files, data_list, run_ids, result_list = self.read_latest_symbol_data()
        if (
            files is not None
            and len(files) > 0
            and data_list is not None
            and len(data_list) > 0
        ):
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - read {len(data_list)} symbol data entries from {len(files)} files ... ",
                end="",
            )
            all_symbols = set()
            for r in result_list:
                all_symbols.update(r.keys())

            hits = OrderedDict()
            for symbol in all_symbols:
                values = []
                for r in result_list:
                    values.append(r.get(symbol, 0))
                while len(values) < 3:
                    values.insert(0, 0)
                latest_value = values[2]
                prev_value = values[1]
                avg_prev2 = (values[0] + values[1]) / 2

                if (
                    latest_value > prev_value
                    or latest_value > avg_prev2
                    or (values[0] == 0 and values[1] == 0 and latest_value > 0)
                ):
                    hits[symbol] = {"run_ids": run_ids, "values": values}
            if hits is None or len(hits) == 0:
                eh.verbose_print(self.vblth, f"[done, no valid symbol data found]]")
            else:
                eh.verbose_print(
                    self.vblth, f"[done, found {len(hits)} valid symbol data entries]"
                )
                status = self.save_word_result(hits, files[-1])
        if status != 0:
            method_status = status
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status

    def create_hotleads(self):
        """
        create hotleads data files from hotleads input dir.
        """
        method_name = "create_hotleads"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth, f"{self.class_name}.{method_name} - create hotleads data files:"
        )
        inputs_data = []
        try:
            os.makedirs(self.hotleads_directory, exist_ok=True)
            # find all pickle files in input dir
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - searching for hotlead input data files ... ",
                end="",
            )
            inputs_pattern = os.path.join(
                self.hotleads_input_directory, f"{self.hotleads_input_prefix}_*.pkl"
            )
            inputs_files = glob.glob(inputs_pattern)
            if not inputs_files or len(inputs_files) == 0:
                eh.verbose_print(self.vblth, f"[no input data files found]")
            else:
                eh.verbose_print(
                    self.vblth, f"[found #{len(inputs_files)} input data file(s)]"
                )
                for fpath in inputs_files:
                    fname = os.path.basename(fpath)
                    ftimestamp = fname.split("_")[1]
                    eh.verbose_print(
                        self.vblth,
                        f"{self.class_name}.{method_name} - loading data from [{fname}] ... ",
                        end="",
                    )
                    inputs_data = []
                    with open(fpath, "rb") as f:
                        inputs_data.append(pickle.load(f))
                    input_run_ids = [d.get("run_id", "undefined") for d in inputs_data]
                    inputs_results = [
                        d.get("results", "undefined") for d in inputs_data
                    ]
                    inputs_symbols = set()
                    for r in inputs_results:
                        inputs_symbols.update(r.keys())
                    eh.verbose_print(
                        self.vblth,
                        f"[done, #{len(inputs_results)}n results, #{len(inputs_symbols)} symbols]",
                    )

                    eh.verbose_print(
                        self.vblth,
                        f"{self.class_name}.{method_name} - detecting hits in input data ... ",
                        end="",
                    )
                    hits = OrderedDict()
                    for symbol in inputs_symbols:
                        values = []
                        for r in inputs_results:
                            values.append(r.get(symbol, 0))
                        while len(values) < 3:
                            values.insert(0, 0)
                        latest_value = values[2]
                        prev_value = values[1]
                        avg_prev2 = (values[0] + values[1]) / 2

                        if (
                            latest_value > prev_value
                            or latest_value > avg_prev2
                            or (values[0] == 0 and values[1] == 0 and latest_value > 0)
                        ):
                            hits[symbol] = {"run_ids": input_run_ids, "values": values}
                    if not hits or len(hits) == 0:
                        eh.verbose_print(self.vblth, f"[no hits detected]")
                    else:
                        eh.verbose_print(self.vblth, f"[found #{len(hits)} hit(s)]")
                        # create docx data and save
                        eh.verbose_print(
                            self.vblth,
                            f"{self.class_name}.{method_name} - saving hotleads as docx files ... ",
                            end="",
                        )
                        doc = Document()
                        doc.add_heading(
                            f"matches for run_id {ftimestamp} from ${fname}", level=1
                        )
                        for symbol, data in hits.items():
                            doc.add_heading(symbol, level=2)
                            for run_id, value in zip(data["run_ids"], data["values"]):
                                p = doc.add_paragraph(f"{run_id}: {value}")
                                p.style.font.size = Pt(12)
                            doc.add_paragraph("")
                        docx_path = os.path.join(
                            config.updates.hotleads_directory,
                            f"{self.hotleads_prefix}_{ftimestamp}_hotleads.docs",
                        )
                        doc.save(docx_path)
                        eh.verbose_print(self.vblth, f"[done]")
                        # save pickle data
                        eh.verbose_print(
                            self.vblth,
                            f"{self.class_name}.{method_name} - saving hotleads as pkl files ... ",
                            end="",
                        )
                        pkl_path = os.path.join(
                            config.updates.hotleads_directory,
                            f"{self.hotleads_prefix}_{ftimestamp}_hotleads.pkl",
                        )
                        with open(pkl_path, "wb") as f:
                            pickle.dump(hits, f)
                        eh.verbose_print(self.vblth, f"[done]")
        except Exception as e:
            method_status = -1
            eh.verbose_print(self.vblth, "[ERROR]")
            eh.verbose_print(
                self.vblth, f"{self.class_name}.{method_name} - exception occurred: {e}"
            )
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status

    def find_files_and_extract_timestamp(self):
        """
        Find the latest Hotleads and Posts files and extract the timestamp.

        Args:
            base_dir (str): Base directory to search for files.

        Returns:
            tuple: (hotleads_file, posts_file, timestamp) or (None, None, None)
        """
        method_name = "find_files_and_extract_timestamp"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - searching for hotleads ...",
            end="",
        )

        # prepare results
        found_files = []
        hotleads_file = None
        posts_file = None
        timestamp = None

        # search for hotleads and posts files
        hotleads_pattern = os.path.join(
            self.hotleads_directory, f"{self.hotleads_prefix}_*_hotleads.pkl"
        )
        hotleads_files = glob.glob(hotleads_pattern)
        if not hotleads_files or len(hotleads_files) == 0:
            eh.verbose_print(self.vblth, f"[no hotleads found]")
        else:
            eh.verbose_print(
                self.vblth, f"[found #{len(hotleads_files)} hotleads file(s)]"
            )
            for hf in hotleads_files:
                hfname = os.path.basename(hf)
                hotleads_timestamp = hfname.split("_")[1].split(".")[0]
                fd = {
                    "timestamp": hotleads_timestamp,
                    "hotleads_file": hf,
                    "posts_file": "",
                }
                found_files.append(fd)

        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - searching for posts ...",
            end="",
        )
        posts_pattern = os.path.join(self.posts_directory, f"{self.posts_prefix}_*.pkl")
        posts_files = glob.glob(posts_pattern)
        if not posts_files or len(posts_files) == 0:
            eh.verbose_print(self.vblth, f"[no posts found]")
        else:
            eh.verbose_print(self.vblth, f"[found #{len(posts_files)} posts file(s)]")
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - update found files record ...",
                end="",
            )
            for pf in posts_files:
                pfname = os.path.basename(pf)
                posts_timestamp = pfname.split("_")[1].split(".")[0]
                append = True
                for fd in found_files:
                    if fd["timestamp"] == posts_timestamp:
                        fd["posts_file"] = pf
                        append = False
                        break
                if append:
                    fd = {
                        "timestamp": posts_timestamp,
                        "hotleads_file": "",
                        "posts_file": pf,
                    }
                    found_files.append(fd)
            eh.verbose_print(
                self.vblth, f"[done, updated #{len(found_files)} record(s)]"
            )

        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - select latest valid record ...",
            end="",
        )
        if len(found_files) > 0:
            # now sort found files by timestamp
            found_files = sorted(found_files, key=lambda x: x["timestamp"])
            # get the latest entry file where both hotleads and posts are available
            for fd in found_files:
                # print(f"[{fd}]")
                if fd["hotleads_file"] and fd["posts_file"]:
                    hotleads_file = fd["hotleads_file"]
                    posts_file = fd["posts_file"]
                    timestamp = fd["timestamp"]
                    eh.verbose_print(
                        self.vblth,
                        f"[found hotleads and posts for timestamp {timestamp}]",
                    )
                    break
        if (
            not hotleads_file
            or not posts_file
            or not timestamp
            or len(hotleads_file) == 0
            or len(posts_file) == 0
            or len(timestamp) == 0
        ):
            method_status = -1
            eh.verbose_print(self.vblth, "[done, no valid record found")
        else:
            eh.verbose_print(self.vblth, f"[done, valid record found at [{timestamp}]]")
            eh.verbose_print(self.vblth, f". hotleads : {hotleads_file}]")
            eh.verbose_print(self.vblth, f". posts    : [{posts_file}]")

        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status, hotleads_file, posts_file, timestamp

    def process_hotleads_and_posts(self, hotleads_file, posts_file, timestamp):
        """
        Process Hotleads and Posts files and create filtered output files.

        Args:
            hotleads_file (str): Path to the Hotleads file.
            posts_file (str): Path to the Posts file.
            timestamp (str): Timestamp extracted from the Hotleads file name.
        """
        method_name = "process_hotleads_and_posts"
        method_start = time.time()
        method_status = 0

        filtered_posts = {}
        total_files_saved = 0
        matched_posts = None

        # load hotleads data
        try:
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - loading hotleads file ... ",
                end="",
            )
            with open(hotleads_file, "rb") as f:
                hotleads_data = pickle.load(f)
            eh.verbose_print(self.vblth, f"[#{len(hotleads_data)} hotleads]")
        except FileNotFoundError:
            method_status = -1
            eh.verbose_print(
                self.vblth, f"[ERROR]\n. hotleads file not found: {hotleads_file}"
            )
        # load posts data
        try:
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - loading posts file ... ",
                end="",
            )
            with open(posts_file, "rb") as f:
                posts_data = pickle.load(f)
            eh.verbose_print(self.vblth, f"[#{len(posts_data)} posts]")
        except FileNotFoundError:
            method_status = -1
            eh.verbose_print(
                self.vblth, f"[ERROR]\n. posts file not found: {posts_file}"
            )

        if method_status == 0:
            # extract stock symbols from hotleads
            stock_symbols = set(hotleads_data.keys())
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - symbols to handle:\n [{', '.join(stock_symbols)} ]",
            )

            # filter posts based on stock symbols
            for symbol in stock_symbols:
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - filter for symbol [{symbol}] ... ",
                    end="",
                )
                matched_posts = []
                for post in posts_data:
                    title = post.get("title", "")
                    content = post.get("content", "")
                    title_match = re.search(r"\b" + re.escape(symbol) + r"\b", title)
                    content_match = re.search(
                        r"\b" + re.escape(symbol) + r"\b", content
                    )

                    if title_match or content_match:
                        matched_posts.append(post)

                eh.verbose_print(
                    self.vblth,
                    f"[done, {len(matched_posts)} match(es)]",
                )
                if matched_posts is not None and len(matched_posts) > 0:
                    filtered_posts[symbol] = matched_posts
                    # save each symbol data to a separate file
                    for idx, single_post in enumerate(matched_posts, start=1):
                        output_filename = f"{timestamp}_{symbol}{idx:02d}.pkl"
                        output_path = os.path.join(
                            self.hotleads_directory, output_filename
                        )
                        eh.verbose_print(
                            self.vblth,
                            f"{self.class_name}.{method_name} - save symbol data as [{output_filename}] ... ",
                            end="",
                        )
                        with open(output_path, "wb") as f:
                            pickle.dump([single_post], f)
                        total_files_saved += 1
                        eh.verbose_print(
                            self.vblth,
                            f"[done, (Post-ID: {single_post.get('post_id', 'N/A')})]",
                        )

        eh.verbose_print(
            self.vblth,
            f" found #{len(filtered_posts)} symbols with matches",
        )
        eh.verbose_print(
            self.vblth,
            f" created #{total_files_saved} file(s) saved",
        )

        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status, filtered_posts

    def update_hotleads_posts(self):
        """
        Update Hotleads and Posts data by finding the latest files and processing them.

        Returns:
            dict: Filtered posts data indexed by stock symbols.
        """
        method_name = "update_hotleads_posts"
        method_status = 0
        eh.verbose_print(self.vblth, f"{self.class_name}.{method_name} - start:")

        # find latest hotleads and posts files
        status, hotleads_file, posts_file, timestamp = (
            self.find_files_and_extract_timestamp()
        )
        if status != 0 or not hotleads_file or not posts_file or not timestamp:
            method_status = -1
            eh.verbose_print(
                self.vblth, f"[ERROR] - no valid hotleads or posts files found"
            )
        else:
            # process hotleads and posts files
            status, filtered_posts = self.process_hotleads_and_posts(
                hotleads_file, posts_file, timestamp
            )
            if status != 0 or filtered_posts is None:
                method_status = -1
                eh.verbose_print(self.vblth, f"[ERROR] - no valid posts discovered")
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - finished, status[{method_status}]",
        )
        return method_status

    def update_results(self):
        "update results by calling all update functions"

        method_name = "update_results"
        eh.verbose_print(self.vblth, f"{self.class_name}.{method_name} - start:")
        self.pickles_to_excel_result()
        self.pickles_to_word_result()
        self.create_hotleads()
        self.update_hotleads_posts()
        eh.verbose_print(self.vblth, f"{self.class_name}.{method_name} - finished")
