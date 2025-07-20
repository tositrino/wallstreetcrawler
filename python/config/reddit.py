"""
reddit.py - reddit settings

"""

work_directory = "../data/reddit"
result_file_name = "reddit-crawler-results"

trigger_count = 5

use_subreddit = "wallstreetbets"
cutoff_days = 1
post_limit = 100
comment_limit = 100

pattern_template = r"(?<!\w)(\${symbol}|{symbol})(?!\w)"

blacklist = {
    "BE",
    "GO",
    "IT",
    "OR",
    "SO",
    "NO",
    "UP",
    "FOR",
    "ON",
    "BY",
    "AS",
    "HE",
    "AM",
    "AN",
    "AI",
    "DD",
    "OP",
    "ALL",
    "YOU",
    "TV",
    "PM",
    "HAS",
    "ARM" "ARE",
    "PUMP",
    "EOD",
    "DAY",
    "WTF",
    "HIT",
    "NOW",
}
