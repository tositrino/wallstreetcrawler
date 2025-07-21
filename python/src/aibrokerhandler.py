"""
aibrokerhandler.py - ai broker class to analyse reddit posts for interesting events
"""

# standard includes
from collections import Counter
import datetime
from docx import Document
import glob
import google.generativeai as genai
import logging
import os
import pickle
import praw
import re
import time

# module configs
import config.main as config

# local modules
import src.errorhandler as eh

# aibroker handler class
# this class handles the ai broker


class AibrokerHandler:
    def __init__(
        self,
        model_name=config.aibroker.model_name,
        template_dir=config.updates.template_directory,
        result_dir=config.updates.result_directory,
        vblth=config.verbose_threshold,
        dblth=config.debug_threshold,
    ):
        self.class_name = "AibrokerHandler"
        self.model_name = model_name
        self.model = None
        self.template_directory = template_dir
        self.result_dir = result_dir
        self.vblth = vblth
        self.dblth = dblth
        self.prepared = False

    def prepare(self):
        """configure the ai broker model"""
        method_name = "configure"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - configure model {self.model_name} ... ",
        )
        if self.prepared:
            eh.verbose_print(self.vblth, f"[already prepared]")
        else:
            try:
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                self.model = genai.GenerativeModel(self.model_name)
                eh.verbose_print(self.vblth, f"[done]")
            except Exception as e:
                method_status = -1
                eh.verbose_print(1, f"[ERROR] - {e}")
            if method_status == 0:
                self.prepared = True
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status

    def get_latest_file_group(self, directory):
        """
        Find the latest file in the given directory result and group all files with the same time ID
        """
        method_name = "get_latest_file_group"
        method_start = time.time()
        method_status = 0
        latest_file = ""
        same_time_files = []
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - searching for files in [{directory}]:",
            end="",
        )
        pattern = os.path.join(folder_path, "*.pkl")
        files = glob.glob(pattern)
        if files is None or len(files) == 0:
            eh.verbose_print(self.vblth, f"[no files found]")
        else:
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = files[0]
            filename = os.path.basename(latest_file)
            time_match = re.match(r"(\d{6}-\d{4})_(.+)\.pkl", filename)
            if not time_match:
                same_time_files = [latest_file]
            else:
                time_id = time_match.group(1)
                # find file with the same time_id
                for file in files:
                    if os.path.basename(file).startswith(time_id):
                        same_time_files.append(file)
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return latest_file, same_time_files

    def extract_stock_symbol(self, filename):
        """
        extract symbol from filename and remove the index number, i.e. 20250717-0455-AMD.pkl -> AMD
        """
        basename = os.path.basename(filename)
        match = re.match(r"\d{6}-\d{4}_(.+)\.pkl", basename)
        if match:
            symbol_with_index = match.group(1)
            # remove the last 2 digits (index number)
            symbol = re.sub(r"\d{2}$", "", symbol_with_index)
            return symbol if symbol else "UNKNOWN"
        return "UNKNOWN"

    def extract_time_id(self, filename):
        """
        extract time ID from filename, i.e. 20250717-0455-AMD.pkl -> 20250717-0455
        """
        basename = os.path.basename(filename)
        match = re.match(r"(\d{6}-\d{4})_(.+)\.pkl", basename)
        return match.group(1) if match else None

    def load_pickle_file(self, filepath):
        """
        Loads data from a pickle file
        """
        method_name = "load_pickle_file"
        method_start = time.time()
        method_status = 0
        data = None
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - loading data from [{filepath}]:",
            end="",
        )
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
            eh.verbose_print(self.vblth, f"[done]")
        except Exception as e:
            method_status = -1
            eh.verbose_print(1, f"[ERROR] - {e}")
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return data

    def extract_post_meta(self, postdata):
        """
        extracts post metadata from the loaded pickle structure
        """
        method_name = "extract_post_meta"
        method_start = time.time()
        method_status = 0
        post_count = 0
        error_count = 0
        posts_meta = []
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - extracting post metadata ... ",
            end="",
        )

        if not postdata or len:
            eh.verbose_print(self.vblth, f"[no post data found]")
        else:
            # ensure we have a list
            if isinstance(postdata, dict):
                postdata = [postdata]
            for post in postdata:
                post_count += 1
                if not isinstance(post, dict):
                    error_count += 1
                    eh.verbose_print(
                        self.vblth,
                        f"[ERROR] - post data is not a dictionary: {post}, ignored.",
                    )
                    continue
                title = post.get("title", "no titel")
                upvotes = post.get("upvotes") or post.get("score") or 0
                num_comments = (
                    post.get("num_comments")
                    or post.get("comment_count")
                    or len(post.get("comments", []))
                )
                url = post.get("url", "no url")
                posts_meta.append(
                    {
                        "title": title,
                        "upvotes": upvotes,
                        "num_comments": num_comments,
                        "url": url,
                    }
                )
        eh.verbose_print(
            1,
            f"[done, #{post_count} posts, #{len(posts_meta)} metadata records, #{error_count}error(s)]",
        )
        if error_count > 0:
            method_status = -1
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status, posts_meta

    def analyze_with_gemini(self, data, stock_symbol):
        """
        use Google Gemini to analyze the data
        """
        method_name = "analyze_with_gemini"
        method_start = time.time()
        method_status = 0
        prompt = ""
        analysis = ""
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - analyzing data with {self.model_name} for {stock_symbol} ... ",
            end="",
        )
        if not self.model:
            eh.verbose_print(self.vblth, f"[model not configured]")
        elif not data or len(data) == 0:
            eh.verbose_print(self.vblth, f"[no data to analyze]")
        else:
            prompt = f"""
          Please analyse the post contents and comments on whether users are bullish or bearish towards the company {stock_symbol}.
          Data for analysis:\n{str(data)[:10000]}  
          Please structure your answer as follows:
          1. **Overall Assessment**: Bullish/Bearish/Neutral
          2. **Reasoning**: Why this assessment? Ideally quote comments with many upvotes that support your assessment.
          3. **Key Points**: The 3 most important arguments
          4. **Sentiment Score**: Rating from -10 (very bearish) to +10 (very bullish)"
          """
        if len(prompt) > 0:
            try:
                response = self.model.generate_content(prompt)
                eh.verbose_print(self.vblth, f"[done]")
                analysis = response.text
            except Exception as e:
                method_status = -1
                eh.verbose_print(1, f"[ERROR] - {e}")
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status, analysis

    def save_analysis(self, analysis_list, post_meta, time_id):
        """
        save gemini analysis results to a DOCX file
        """
        method_name = "save_analysis"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - saving analysis results for time ID {time_id} in {self.result_dir} ... ",
            end="",
        )
        if not analysis_list or len(analysis_list) == 0:
            eh.verbose_print(self.vblth, f"[analysis data is empty]")
        elif not post_meta or len(post_meta) == 0:
            eh.verbose_print(self.vblth, f"[post_meta is empty]")
        else:
            try:
                doc = Document()
                doc.add_heading(f"Analysis for the time id {time_id}", level=1)
                doc.add_paragraph(
                    f'analysis generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                )
                doc.add_paragraph("=" * 50)

                for stock_symbol, posts_meta, analysis_text in analysis_list:
                    doc.add_heading(f"Stock Symbol: {stock_symbol}", level=2)
                    doc.add_paragraph("Related  Post:", style=None)
                    for i, pm in enumerate(posts_meta, start=1):
                        p = doc.add_paragraph(style="List Bullet")
                        p.add_run(f"{i}. {pm['title']} ").bold = True
                        p.add_run(f"(↑ {pm['upvotes']} · 💬 {pm['num_comments']})")
                        doc.add_paragraph(f"URL: {pm['url']}", style="Caption")

                doc.add_paragraph()
                paragraphs = analysis_text.split("\n")
                for para in paragraphs:
                    if para.strip():
                        p = doc.add_paragraph()
                        parts = para.split("**")
                        for i, part in enumerate(parts):
                            if i % 2 == 1:
                                run = p.add_run(part)
                                run.bold = True
                            else:
                                p.add_run(part)

                doc.add_paragraph("-" * 30)

                # save result
                filename = f"{time_id}analysis.docx"
                filepath = os.path.join(self.result_dir, filename)
                doc.save(filepath)
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
        return method_status, filepath

    def analyse():
        """
        analyse the latest reddit posts for stock symbols and save the results
        """
        method_name = "analyse"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - starting analysis: ",
        )

        if self.prepare():
            latest_file, same_time_files = self.get_latest_file_group()
            if not latest_file or len(latest_file) == 0:
                return -1
            time_id = self.extract_time_id(latest_file)
            data = self.load_pickle_file(latest_file)
            if not data or len(data) == 0:
                return -1
            status, posts_meta = self.extract_post_meta(data)
            if status != 0 or not posts_meta or len(posts_meta) == 0:
                return -1

            analysis_results = []
            file_count = 0
            error_count = 0
            for file_path in same_time_files:
                file_count += 1
                stock_symbol = self.extract_stock_symbol(file_path)
                eh.verbose_print(
                    self.vblth,
                    f"{self.class_name}.{method_name} - analyzing {stock_symbol} from {file_path}] ... ",
                    end="",
                )
                data = self.load_pickle_file(file_path)
                if not data or len(data) == 0:
                    error_count += 1
                    eh.verbose_print(self.vblth, f"[no data, ignored]")
                    continue
                status, analysis_text = self.analyze_with_gemini(data, stock_symbol)

                if analysis_status != 0 or not analysis_text or len(analysis_text) == 0:
                    error_count += 1
                    eh.verbose_print(self.vblth, f"[no analysis text, ignored]")
                    continue

                analysis_results.append((stock_symbol, posts_meta, analysis_text))
                eh.verbose_print(self.vblth, f"[done]")

            # now save all this
            eh.verbose_print(
                self.vblth,
                f"{self.class_name}.{method_name} - saving analysis results ... ",
                end="",
            )
            if not analysis_results or len(analysis_results) == 0:
                eh.verbose_print(self.vblth, f"[no analysis results to save]")
            else:
                status, filepath = self.save_analysis(
                    analysis_results, posts_meta, time_id
                )
                if status == 0:
                    eh.verbose_print(self.vblth, f"[done, saved to {filepath}]")
                else:
                    eh.verbose_print(self.vblth, f"[ERROR] - saving analysis failed")
                    error_count += 1

        if error_count > 0:
            method_status = -1
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return method_status
