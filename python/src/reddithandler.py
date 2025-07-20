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


def reddit_crawler(
    target_dir=config.reddit.work_directory, pkl_file=config.nasdaq.pkl_file_name
):

    fn_name = "reddit_crawler"
    fn_start = time.time()
    fn_status = 0
    eh.verbose_print(
        1,
        f"{__name__}.{fn_name} - start crawler ... ",
        end="",
    )
    try:
        run_id = datetime.datetime.now().strftime("%y%m%d-%H%M")
        eh.verbose_print(1, f"[done, id=${run_id}]")

        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - initialize reddit opbject  ... ",
            end="",
        )
        if (
            os.getenv("REDDIT_CLIENT_ID") is None
            or os.getenv("REDDIT_CLIENT_SECRET") is None
            or os.getenv("REDDIT_USER_AGENT") is None
        ):
            raise ValueError(
                "REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET or REDDIT_USER_AGENT environment variables not set"
            )
        eh.verbose_print(1, "[done]")

        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )
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

        # load akronym data
        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - reading pickle data from [{pkl_file}] ... ",
            end="",
        )
        if not os.path.exists(pkl_file):
            raise FileNotFoundError(
                f"pkl file [{pkl_file}] does not exist, please run the nasdaq handler first"
            )
        with open(pkl_file_path, "rb") as f:
            all_symbols = pickle.load(f)

        symbols = [
            symbol for symbol in all_symbols if symbol not in config.reddit.blacklist
        ]
        eh.verbose_print(1, f"[done, found #{len(symbols)} symbol(s)")

        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - search for symbols in r/{config.reddit.use_subreddit} :",
        )

        # setup counter for symbol occurrences
        symbol_counts = Counter()
        # load subreddit and get latest posts

        subreddit = reddit.subreddit(config.reddit.use_subreddit)
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
            for symbol in symbols:
                # Regex für ganze Wörter: \b für Wortgrenzen
                pattern = config.reddit.pattern_template.format(
                    symbol=re.escape(symbol)
                )
                matches = len(re.findall(pattern, search_text))
                if matches > 0:
                    symbol_counts[symbol] += matches
                    eh.verbose_print(1, f"[{symbol} matches {matches}] ", end="")
            eh.verbose_print(1, "[done]\n")

        eh.verbose_print(
            1,
            f"{__name__}.{fn_name} - finished search, searched #{post_count} post(s) and #{comment_count} comment(s)",
        )

        # Ergebnisse filtern (>5 Treffer) und speichern
        filtered_results = {
            symbol: count
            for symbol, count in symbol_counts.items()
            if count > config.reddit.trigger_count
        }

        if filtered_results:
            # Als Dictionary mit Run-ID speichern
            result_data = {
                "run_id": run_id,
                "results": filtered_results,
                "total_posts": post_count,
            }

            result_file_path = os.path.join(
                config.reddit.work_directory,
                f"{config.reddit.result_file_name}-{run_id}",
            )
            eh.verbose_print(
                1,
                f"{__name__}.{fn_name} - saving results to [{result_file_path}] ... ",
                end="",
            )
            with open(result_file_path, "wb") as f:
                pickle.dump(result_data, f, protocol=pickle.HIGHEST_PROTOCOL)
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
                f"[done, no symbols with more than  {config.reddit.trigger_count} matches found]",
            )
    except Exception as e:
        fn_status = -1
        eh.verbose_print(1, "[ERROR]")
        eh.verbose_print(1, f"{__name__}.{fn_name} - exception occurred: {e}")
    fn_elapsed = time.time() - fn_start
    eh.verbose_print(
        1,
        f"{__name__}.{fn_name} - finisshed, duration={fn_elapsed:2.4f} second(s), status={fn_status}:",
    )
