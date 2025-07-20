"""
reddithandler.py - handles reddit
"""

# standard includes
from collections import Counter
import datetime
import io
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

# reddit handler class
# this class handles the reddit posts data


class RedditHandler:
    def __init__(
        self,
        target_dir=config.reddit.work_directory,
        pkl_file="",
        vblth=config.verbose_threshold,
        dblth=config.debug_threshold,
    ):
        self.class_name = "RedditHandler"
        self.target_dir = target_dir
        self.pkl_file = pkl_file
        self.vblth = vblth
        self.dblth = dblth
        self.run_id = ""
        self.reddit_client_id = ""
        self.reddit_client_secret = ""
        self.reddit_user = ""
        self.reddit_user_agent = ""
        self.reddit = None
        self.all_symbols = None
        self.symbols = None
        self.symbol_counts = None
        self.result_data = None
        self.result_file_path = ""

    def crawler(self):

        method_name = "crawler"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - start:",
        )

        try:
            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} - create object id ... ",
                end="",
            )
            self.run_id = datetime.datetime.now().strftime("%y%m%d-%H%M")
            eh.verbose_print(1, f"[done, id=${self.run_id}]")

            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} - initialize reddit object  ... ",
                end="",
            )
            self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
            self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            self.reddit_user = os.getenv("REDDIT_USER")
            self.reddit_user_agent = os.getenv("REDDIT_USER_AGENT")
            if (
                self.reddit_client_id is None
                or len(self.reddit_client_id) == 0
                or self.reddit_client_secret is None
                or len(self.reddit_client_secret) == 0
                or self.reddit_user is None
                or len(self.reddit_user) == 0
            ):
                raise ValueError(
                    "REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET or REDDIT_USER environment variables not set"
                )
            if (self.reddit_user_agent is None or len(self.reddit_user_agent)) == 0:
                self.reddit_user_agent = f"{config.APP_VERNAME}/:v{config.APP_VERID} (by /u/{self.reddit_user})"
            self.reddit = praw.Reddit(
                client_id=self.reddit_client_id,
                client_secret=self.reddit_client_secret,
                user_agent=self.reddit_user_agent,
            )
            eh.verbose_print(1, "[done]")
            # make sure the target directory exists
            if os.path.exists(self.target_dir):
                eh.debug_print(
                    1,
                    f"{self.class_name}.{method_name} - target directory [{self.target_dir}] exists",
                )
            else:  # create target directory if it does not exist
                eh.debug_print(
                    1,
                    f"{self.class_name}.{method_name} - target directory [{self.target_dir}] does not exist, creating it",
                )
                os.makedirs(self.target_dir, exist_ok=True)

            # load akronym data
            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} - reading pickle data from [{self.pkl_file}] ... ",
                end="",
            )
            if self.pkl_file is None or len(self.pkl_file) == 0:
                self.pkl_file = os.path.join(
                    config.nasdaq.work_directory,
                    f"{config.nasdaq.result_file_name}.pkl",
                )
            if not os.path.exists(self.pkl_file):
                raise FileNotFoundError(
                    f"pkl file [{self.pkl_file}] does not exist, please run the nasdaq handler first"
                )
            with open(self.pkl_file, "rb") as f:
                self.all_symbols = pickle.load(f)

            self.symbols = [
                symbol
                for symbol in self.all_symbols
                if symbol not in config.reddit.blacklist
            ]
            eh.verbose_print(1, f"[done, found #{len(self.symbols)} symbol(s)]")

            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} - search for symbols in r/{config.reddit.use_subreddit} :",
            )

            # setup counter for symbol occurrences
            self.symbol_counts = Counter()
            # load subreddit and get latest posts

            subreddit = self.reddit.subreddit(config.reddit.use_subreddit)
            cutoff_time = datetime.datetime.now() - datetime.timedelta(
                days=config.reddit.cutoff_days
            )

            post_count = 0
            comment_count = 0
            for post in subreddit.new(limit=config.reddit.post_limit):
                post_time = datetime.datetime.fromtimestamp(post.created_utc)
                if post_time < cutoff_time:
                    continue
                post_count += 1
                eh.verbose_print(
                    1, f" search post {post_count}: {post.title[:50]} ...", end=""
                )
                # create search data (titel + content)
                search_text = f"{post.title} {post.selftext}"
                # load and add comments
                post.comments.replace_more(limit=config.reddit.comment_limit)
                for comment in post.comments.list():
                    search_text += f" {comment.body}"
                    comment_count += 1
                # now search for each symbol in the search text
                for symbol in self.symbols:
                    pattern = config.reddit.pattern_template.format(
                        symbol=re.escape(symbol)
                    )
                    matches = len(re.findall(pattern, search_text))
                    if matches > 0:
                        self.symbol_counts[symbol] += matches
                        eh.verbose_print(1, f"[{symbol} matches {matches}] ", end="")
                eh.verbose_print(1, "[done]\n")

            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} - finished search, searched #{post_count} post(s) and #{comment_count} comment(s)",
            )

            # filter results
            filtered_results = {
                symbol: count
                for symbol, count in self.symbol_counts.items()
                if count > config.reddit.trigger_count
            }

            if filtered_results:
                # create result data
                self.result_data = {
                    "run_id": self.run_id,
                    "results": filtered_results,
                    "total_posts": post_count,
                    "total_comments": comment_count,
                }
                self.result_file_path = os.path.join(
                    config.reddit.work_directory,
                    f"{config.reddit.result_file_name}-{self.run_id}",
                )
                eh.verbose_print(
                    1,
                    f"{self.class_name}.{method_name} - saving results to [{self.result_file_path}] ... ",
                    end="",
                )
                with open(self.result_file_path, "wb") as f:
                    pickle.dump(self.result_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                eh.verbose_print(
                    1,
                    f"[done, {len(filtered_results)} symbol(s) with more than {config.reddit.trigger_count} matches]",
                )
                for symbol, count in sorted(
                    filtered_results.items(), key=lambda x: x[1], reverse=True
                ):
                    eh.verbose_print(1, f"  {symbol}: #{count}  matches")
            else:
                eh.verbose_print(
                    1,
                    f"[done, no symbols with more than #{config.reddit.trigger_count} matches found]",
                )
        except Exception as e:
            fn_status = -1
            eh.verbose_print(1, "[ERROR]")
            eh.verbose_print(
                1, f"{self.class_name}.{method_name} - exception occurred: {e}"
            )

        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
