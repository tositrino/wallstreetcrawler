"""
main.py - main config

"""

import os

# APP standard variables

APP_VERNAME = "wallstreetcrawler"
APP_VERID = "0.4.1"
APP_VERINFO = "crawl through reddits and collect wallstreet infos"
APP_RELDATE = "2025/07/22"
APP_RELINFO = "v0.4.1"
APP_COPYRIGHT = "copyright (c) 2025 by development at ths dot one"
APP_LICENSE = "GPL3"
APP_LICENSEINFO = "please see ./LICENSE file in the main directory for further info"
APP_WARRANTY = "this software comes with absolutely no warranties whatsoever"
APP_NODEID = 0x5741434E

# control variables

# debug level and threshold
debug_level: int = 0
debug_threshold: int = 1
# verbose level and threshold
verbose_level: int = 1
verbose_threshold: int = 1
# force mode (overwrite existing files)
force_mode: bool = False
# cleanmode (clear all files before writing to them (do not append)
clean_mode: bool = True

logging: bool = True
log_level = None
log_directory = "../intermediate_data/logs"
log_file_name = f"{APP_VERNAME}.log"
log_file_mode = "w"

max_errors = 1
error_count = 0
error_messages = []
max_warnings = 0
warn_count = 0
warn_messages = []
force_return_code = 0
return_code = 0
atexit_list = []
in_termination = 0

# environment file (loaded with dotenv)
env_file = f"~/lsr/etc/env/{APP_VERNAME}.env"

# directory settings
data_directory = "../data"

# import all other configs here
import config.nasdaq as nasdaq
import config.reddit as reddit
import config.updates as updates
import config.aibroker as aibroker
import config.reports as reports

# end of main config
