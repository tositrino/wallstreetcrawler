"""
reportshandler.py - handles reports
"""

# standard includes
from collections import Counter, OrderedDict
from docx import Document
from docx.shared import Pt
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

# reports handler class
# this class handles the reports


class ReportsHandler:
    def __init__(
        self,
        classic_dir=config.reports.classic_reports_dir,
        ai_dir=config.reports.ai_reports_dir,
        summary_dir=config.reports.summary_reports_dir,
        totals_suffix=config.reports.totals_suffix,
        vblth=config.verbose_threshold,
        dblth=config.debug_threshold,
    ):
        self.class_name = "ReportsHandler"
        self.classic_directory = classic_dir
        self.ai_directory = ai_dir
        self.summary_directory = summary_dir
        self.totals_suffix = totals_suffix
        self.vblth = vblth
        self.dblth = dblth

    @staticmethod
    def copy_paragraph_with_formatting(source_para, target_doc):
        """copy a formatted paragraph to target document"""
        new_para = target_doc.add_paragraph()
        new_para.style = source_para.style
        new_para.alignment = source_para.alignment
        for run in source_para.runs:
            new_run = new_para.add_run(run.text)
        new_run.bold = run.bold
        new_run.italic = run.italic
        new_run.underline = run.underline
        new_run.font.name = run.font.name
        new_run.font.size = run.font.size
        new_run.font.color.rgb = run.font.color.rgb
        if run.font.highlight_color:
            new_run.font.highlight_color = run.font.highlight_color

    @staticmethod
    def copy_table_with_formatting(source_table, target_doc):
        """copy formatted table to target doctument"""
        rows = len(source_table.rows)
        cols = len(source_table.columns)
        new_table = target_doc.add_table(rows=rows, cols=cols)
        new_table.style = source_table.style
        for i, row in enumerate(source_table.rows):
            for j, cell in enumerate(row.cells):
                new_cell = new_table.cell(i, j)
                new_cell.paragraphs[0].clear()
                for para in cell.paragraphs:
                    ReportsHandler.copy_paragraph_with_formatting(para, new_cell)

    @staticmethod
    def copy_document_content(source_doc, target_doc):
        """copy all document data to target document"""
        for element in source_doc.element.body:
            if element.tag.endswith("p"):
                for para in source_doc.paragraphs:
                    if para._element == element:
                        ReportsHandler.copy_paragraph_with_formatting(para, target_doc)
                        break
            elif element.tag.endswith("tbl"):
                for table in source_doc.tables:
                    if table._element == element:
                        ReportsHandler.copy_table_with_formatting(table, target_doc)
                        break

    def find_latest_file_and_prefix(self, directory):
        """
        find the latest file in the given directory
        """
        method_name = "find_latest_file_and_prefix"
        method_start = time.time()
        method_status = 0
        latest_file = ""
        latest_time = None
        prefix = None
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - searching for latest file in [{directory}] ... ",
            end="",
        )
        file_count = 0
        error_count = 0
        for filename in os.listdir(directory):
            if filename.endswith(".docx"):
                try:
                    if "_" in filename:
                        # Format: [υυmmdd-hhmm]_??????.docx
                        prefix_candidate = filename.split("_")[0]
                    elif self.totals_suffix in filename:
                        # Format: [yυmmdd-hhmm]_totals.docx
                        prefix_candidate = filename.replace(self.totals_suffix, "")
                    else:
                        continue
                    # check/validate time
                    dt = datetime.strptime(prefix_candidate, "%y%m%d-%H%M")
                    file_path = os.path.join(directory, filename)
                    file_time = os.path.getmtime(file_path)
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
                        latest_file = file_path
                        prefix = prefix_candidate
                except (ValueError, IndexError):
                    continue
                except Exception as e:
                    method_status = -1
                    eh.verbose_print(1, f"[ERROR]\nERROR - exception occurred: {e}")

        if len(latest_file) == 0 or latest_time is None:
            method_status = -1
            eh.verbose_print(self.vblth, f"[no file found, status={method_status}]")
        else:
            eh.verbose_print(
                self.vblth,
                f"[done, found {latest_file}#{len(same_time_files)} file(s)]",
            )
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status, latest_file, prefix

    def generate(self):
        """generate report summary from classic and ai reports."""
        method_name = "generate"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth, f"{self.class_name}.{method_name} - generate full report:"
        )

        # Find latest files and prefixes
        status, latest_file1, prefix1 = self.find_latest_file_and_prefix(
            self.classic_directory
        )
        if status != 0 or latest_file1 is None or prefix1 is None:
            method_status = -1
            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} -  failed to find latest classic report file.",
            )
        status, latest_file2, prefix2 = self.find_latest_file_and_prefix(
            self.ai_directory
        )
        if status != 0 or latest_file1 is None or prefix1 is None:
            method_status = -1
            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} -  failed to find latest ai report file.",
            )
        if prefix1 != prefix2:
            method_status = -1
            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} -  prefixes do not match!\n  [{prefix1}] != [{prefix2}]",
            )
        if method_status == 0:
            try:
                doc1 = Document(latest_file1)
                doc2 = Document(latest_file2)
                report_doc = Document()
            except Exception as e:
                method_status = -1
                eh.verbose_print(
                    1,
                    f"{self.class_name}.{method_name} - exception creating documents: {e}]",
                )
        if method_status == 0:
            for curdoc in [doc1, doc2]:
                # Copy styles from document
                for style in curdoc.styles:
                    try:
                        if style.name not in [s.name for s in report_doc.styles]:
                            report_doc.styles.add_style(style.name, style.type)
                    except:
                        pass  # Ignore errors for already existing styles
            # copy document content
            ReportsHandler.copy_document_content(curdoc, report_doc)
            # add pagebreak
            report_doc.add_page_break()
        if method_status == 0:
            try:
                # save the result
                result_path = os.path.join(
                    self.summary_directory, f"{prefix1}_Report.docx"
                )
                report_doc.save(result_path)
            except Exception as e:
                method_status = -1
                eh.verbose_print(
                    1,
                    f"{self.class_name}.{method_name} - exception creating documents: {e}]",
                )

        if method_status != 0:
            eh.verbose_print(
                1, f"{self.class_name}.{method_name} - failed to generate report."
            )
        else:
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - report successfully generated: as {result_path}",
            )
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status
