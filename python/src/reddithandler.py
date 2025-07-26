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
        work_dir=config.reddit.work_directory,
        posts_dir=config.reddit.posts_directory,
        pkl_file="",
        vblth=config.verbose_threshold,
        dblth=config.debug_threshold,
    ):
        self.class_name = "RedditHandler"
        self.work_dir = work_dir
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
        self.posts_dir = posts_dir
        self.post_file_path = ""
        self.prepared = False
        self.subreddit = None
        self.cutoff_time = None
        self.post_data = None
        self.symbol_counts = None

    def new_run_id(self):
        """
        generate a new run id
        """
        method_name = "new_run_id"
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - create new object run id ... ",
            end="",
        )
        self.run_id = datetime.datetime.now().strftime("%y%m%d-%H%M")
        eh.verbose_print(1, f"[done, id=${self.run_id}]")
        return self.run_id

    def update_post_file_path(self):
        """
        update the post file path with the current run id
        """
        method_name = "update_post_file_path"
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - update post file path ... ",
            end="",
        )
        self.post_file_path = os.path.join(
            self.posts_dir,
            f"{config.reddit.post_file_name_prefix}_{self.run_id}.pkl",
        )
        eh.verbose_print(1, f"[done, path={self.post_file_path}]")
        return self.post_file_path

    def prepare(self) -> bool:
        method_name = "prepare"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth, f"{self.class_name}.{method_name} - prepare handler", end=""
        )
        if self.prepared:
            eh.verbose_print(1, " ... [already prepared]")
        else:
            eh.verbose_print(1, ":")
            try:
                self.new_run_id()
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
                if os.path.exists(self.work_dir):
                    eh.debug_print(
                        1,
                        f"{self.class_name}.{method_name} - work directory [{self.work_dir}] exists",
                    )
                else:  # create target directory if it does not exist
                    eh.debug_print(
                        1,
                        f"{self.class_name}.{method_name} - work directory [{self.work_dir}] does not exist, creating it",
                    )
                    os.makedirs(self.work_dir, exist_ok=True)

                # setup/update post data file path
                self.update_post_file_path()

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

                # set subreddit , cutoff time and initialize post data and symbol counter
                self.subreddit = self.reddit.subreddit(config.reddit.use_subreddit)
                self.cutoff_time = datetime.datetime.now() - datetime.timedelta(
                    days=config.reddit.cutoff_days
                )
                self.post_data = []
                self.symbol_counts = Counter()
                self.prepared = True
            except Exception as e:
                self.prepared = False
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
        return self.prepared

    def extract_comments_with_hierarchy(self, post):
        """
        extract comments with hierarchy
        """
        comments_data = []
        comments_count = 0
        for comment in post.comments.list():
            # check only comments with at least commment_min_upvotes upvotes
            if comment.score >= config.reddit.commment_min_upvotes:
                # parent_id starts with "t1_" means it is a reply to another comment
                # parent_id starts with "t3_" means it is a direct reply to the post
                is_reply = comment.parent_id.startswith("t1_")
                comment_data = {
                    "comment_id": comment.id,
                    "body": comment.body,
                    "upvotes": comment.score,
                    "is_reply": is_reply,
                    "parent_id": comment.parent_id,
                }
                comments_data.append(comment_data)
                comments_count += 1
        return comments_count, comments_data

    def save_post_data(self):
        """
        save posts and comments data to a pickle file for mutliple use without having to crawl again
        """
        method_name = "save_posts_data"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - save post data to  [{self.post_file_path}] ... ",
            end="",
        )
        if not self.prepared:
            method_status = -1
            eh.verbose_print(
                self.vblth,
                "[ERROR]\nERROR: reddit handler not prepared, please run prepare() first",
            )
        else:
            with open(self.post_file_path, "wb") as f:
                pickle.dump(self.post_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        method_elapsed = time.time() - method_start
        eh.verbose_print(
            self.vblth,
            f"[done, saved #{len(self.post_data)} post(s), duration={method_elapsed:2.4f},, status={method_status}]",
        )
        return method_status

    def load_post_data(self):
        """
        load posts and comments data from a pickle file
        """
        method_name = "load_posts_data"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - load post data from [{self.post_file_path}] ... ",
            end="",
        )
        if not self.prepared:
            method_status = -1
            eh.verbose_print(
                self.vblth,
                "[ERROR]\nERROR: reddit handler not prepared, please run prepare() first",
            )
        else:
            with open(os.path.join(self.post_file_path, file), "rb") as f:
                self.post_data.append(pickle.load(f))
            if self.post_data is None or len(self.post_data) == 0:
                method_status = -1
                eh.verbose_print(
                    self.vblth,
                    f"[ERROR]\nERROR - no post data found in [{self.post_file_path}]",
                )

        method_elapsed = time.time() - method_start
        eh.verbose_print(
            self.vblth,
            f"[done, saved #{len(posts_data)} post(s), duration={method_elapsed:2.4f},, status={method_status}]",
        )
        return method_status

    def crawler(self, force: bool = False):
        method_name = "crawler"
        method_start = time.time()
        method_status = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - start:",
        )
        if not self.prepare():
            return
        if self.post_data is not None and len(self.post_data) > 0:
            if not force:
                eh.verbose_print(
                    1,
                    f"{self.class_name}.{method_name} - already crawled, please use --force to start a new crawl",
                )
                return method_status

            # reset runid
            self.new_run_id
            # update post file path
            self.update_post_file_path()
            # reset counter for symbol occurrences
            self.symbol_counts = Counter()
            self.post_data = []

        try:
            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} - search for symbols in r/{config.reddit.use_subreddit} :",
            )
            post_count = 0
            comment_count = 0
            for post in self.subreddit.new(limit=config.reddit.post_limit):
                post_time = datetime.datetime.fromtimestamp(post.created_utc)
                if post_time < self.cutoff_time:
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

                # create comment data
                comments_data = self.extract_comments_with_hierarchy(post)
                # create post data record
                post_data = {
                    "post_id": post.id,
                    "title": post.title,
                    "content": post.selftext,
                    "upvotes": post.score,
                    "created_utc": post.created_utc,
                    "url": post.url,
                    "comments": comments_data,
                }
                # and append to post_data
                self.post_data.append(post_data)

                # now search for each symbol in the search text
                for symbol in self.symbols:
                    pattern = config.reddit.pattern_template.format(
                        symbol=re.escape(symbol)
                    )
                    matches = len(re.findall(pattern, search_text))
                    if matches > 0:
                        self.symbol_counts[symbol] += matches
                        eh.verbose_print(1, f"[{symbol} matches {matches}] ", end="")
                eh.verbose_print(1, "[done]")

            eh.verbose_print(
                1,
                f"{self.class_name}.{method_name} - finished search, searched #{post_count} post(s) and #{comment_count} comment(s)",
            )
            # save posts data to file
            self.save_post_data()

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
                    f"{config.reddit.result_file_name_prefix}_{self.run_id}.pkl",
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

    def search(self, symbol):
        method_name = "search"
        method_start = time.time()
        method_status = 0
        results = []
        total_count = 0
        post_count = 0
        comment_count = 0
        total_matches = 0
        eh.verbose_print(
            self.vblth,
            f"{self.class_name}.{method_name} - search symbol [{symbol}]:",
        )
        if not self.prepare():
            method_status = -1
        else:
            # pattern = config.reddit.pattern_template.format(
            #            symbol=re.escape(symbol)
            #        )
            pattern = re.compile(
                r"(?<!\w)(\$"
                + re.escape(symbol)
                + r"|"
                + re.escape(symbol)
                + r")(?!\w)"
            )
            for post in self.subreddit.new(limit=config.reddit.post_limit):
                post_time = datetime.datetime.fromtimestamp(post.created_utc)
                if post_time < self.cutoff_time:
                    continue
                post_count += 1
                post_text = post.title + "\n" + (post.selftext or "")
                post_matches = pattern.findall(post_text)
                comment_matches = []
                try:
                    post.comments.replace_more(config.reddit.comment_limit)
                    for comment in post.comments.list():
                        if hasattr(comment, "body"):
                            comment_matches.extend(pattern.findall(comment.body))
                            comment_count += 1
                except:
                    pass

                total_matches = len(post_matches) + len(comment_matches)
                if total_matches > 0:
                    total_count += total_matches
                    all_variants = post_matches + comment_matches
                    variant_counts = {}
                    for variant in all_variants:
                        variant_counts[variant] = variant_counts.get(variant, 0) + 1

                    results.append(
                        {
                            "title": post.title,
                            "url": f"https://reddit.com{post.permalink}",
                            "post_hits": len(post_matches),
                            "comment_hits": len(comment_matches),
                            "variants": variant_counts,
                            "upvotes": post.score,
                            "num_comments": post.num_comments,
                        }
                    )

        method_elapsed = time.time() - method_start
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - searched #{post_count} post(s) and #{comment_count} comment(s)\n results={results}\n",
        )
        eh.verbose_print(
            1,
            f"{self.class_name}.{method_name} - finished, duration={method_elapsed:2.4f} second(s), status={method_status}:",
        )
        return total_count, results
