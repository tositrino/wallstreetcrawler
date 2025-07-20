"""
The main script which runs all the analysis modules.

"""

# standard modules

from argparse import ArgumentParser
import dotenv
import io
import logging
import os
from pathlib import Path
import platform
import sys
import time

# special modules (requirements)

# module configs
import config.main as config

# local modules
# NOTE: see descriptions in modulehandler.py and test.py for more info about
#       the module call capabilities

import src.errorhandler as eh
import src.nasdaqhandler as nh
import src.reddithandler as rh
import src.updatehandler as uh


def show_version(mode: str = ""):
    """show program version and info
    Args:
      None
    Returns:
      None
    """
    vblth = 1
    eh.verbose_print(vblth, "#")
    eh.verbose_print(
        vblth,
        "# {0} version {1} - {2}".format(
            config.APP_VERNAME, config.APP_VERID, config.APP_VERINFO
        ),
    )
    eh.verbose_print(vblth, "# {0}".format(config.APP_COPYRIGHT))

    if mode == "all":
        eh.verbose_print(vblth, "# release note  : \n{0}".format(config.APP_RELINFO))

    eh.verbose_print(vblth, "# release date  : {0}".format(config.APP_RELDATE))
    eh.verbose_print(vblth, "# running on    : {0}".format(platform.platform()))
    eh.verbose_print(vblth, "# license model : {0}".format(config.APP_LICENSE))
    eh.verbose_print(vblth, "# {0}".format(config.APP_WARRANTY))
    eh.verbose_print(vblth, "#")
    eh.verbose_print(vblth, "")


def show_status():
    """show program status
    Args:
      None
    Returns:
      None
    """
    vblth = 1
    eh.verbose_print(vblth, "\nStatus Information\n------------------")
    eh.verbose_print(
        vblth, "  debug level                     = {0}".format(config.debug_level)
    )
    eh.verbose_print(
        vblth, "  debug level threshold           = {0}".format(config.debug_threshold)
    )
    eh.verbose_print(
        vblth,
        "   force mode                      = {0}".format(config.force_mode),
    )
    eh.verbose_print(
        vblth, "  verbose level                   = {0}".format(config.verbose_level)
    )
    eh.verbose_print(
        vblth,
        "  verbose level threshold         = {0}".format(config.verbose_threshold),
    )
    eh.verbose_print(
        vblth, "  logging                         = {0}".format(config.logging)
    )
    eh.verbose_print(
        vblth, "  logging level                   = {0}".format(config.log_level)
    )
    eh.verbose_print(
        vblth, "  log_directory                   = {0}".format(config.log_directory)
    )
    eh.verbose_print(
        vblth, "  log file name                   = {0}".format(config.log_file_name)
    )
    eh.verbose_print(
        vblth, "  log file mode                   = {0}".format(config.log_file_mode)
    )
    eh.verbose_print(
        vblth, "  data_directory                  = {0}".format(config.data_directory)
    )
    eh.verbose_print(
        vblth,
        "  nasdaq source url               = {0}".format(config.nasdaq.source_url),
    )
    eh.verbose_print(
        vblth,
        "  nasdaq working dir              = {0}".format(config.nasdaq.work_directory),
    )
    eh.verbose_print(
        vblth,
        "  nasdaq original file name       = {0}".format(
            config.nasdaq.original_file_name
        ),
    )
    eh.verbose_print(
        vblth,
        "  nasdaq result file name         = {0}".format(
            config.nasdaq.result_file_name
        ),
    )
    eh.verbose_print(
        vblth,
        "  nasdaq compare words            = {0}".format(config.nasdaq.compare_words),
    )
    eh.verbose_print(
        vblth,
        "  nasdaq compare case sensitive   = {0}".format(config.nasdaq.compare_words),
    )
    eh.verbose_print(
        vblth,
        "  reddit working dir              = {0}".format(config.reddit.work_directory),
    )
    eh.verbose_print(vblth, "")


def terminate(retcode: int = 0):
    """terminate the program
    Args:
      retcode: int - return code
    Returns:
      None
    """
    config.in_termination += 1
    if config.in_termination > 1:
        eh.debug_print(1, "DEBUG: terminate() - already in termination")
        return
    config.return_code = retcode
    eh.debug_print(1, "DEBUG: terminate() - retcode={0}".format(retcode))
    sys.exit(retcode)


def main():
    main_status = 0
    vblth = config.verbose_threshold
    dblth = config.debug_threshold

    # save startup time
    main_start = time.time()

    # load environment setting first (may be overidden by command line args)
    env_file_path = os.path.expanduser(config.env_file)
    if os.path.isfile(env_file_path):
        eh.debug_print(dblth, f"DEBUG: loading environment file [{env_file_path}]")
        dotenv.load_dotenv(env_file_path)
    else:
        eh.debug_print(
            dblth,
            f"DEBUG: environment file [{env_file_path}] not found, ignored",
        )
        main_status = 1

    # Setup argument parser
    parser = ArgumentParser()
    parser.add_argument(
        "--clean", "-c", action="store_true", help="Remove previous results"
    )
    parser.add_argument("--crawl", "-C", action="store_true", help="run crawler")
    parser.add_argument(
        "--data_file_path", help="data file name (csv)", default="", required=False
    )
    parser.add_argument("--debug", "-d", help="run in debug mode", action="store_true")
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="force downloads (overwrite existing files)",
    )
    parser.add_argument("--logfile", help="log file name", default="", required=False)
    parser.add_argument(
        "--logging", "-l", help="enable logging to file", action="store_true"
    )
    parser.add_argument("--noclean", help="disable debug mode", action="store_true")
    parser.add_argument("--nodebug", help="disable debug mode", action="store_true")
    parser.add_argument("--noforce", help="disable force mode", action="store_true")
    parser.add_argument(
        "--nologging", help="disable logging to file", action="store_true"
    )
    parser.add_argument(
        "--nasdaq_download",
        "-N",
        help=f"download and clean nasdaq listed symbols from [{config.nasdaq.source_url}]",
        # nargs="+",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--nasdaq_work_dir",
        help=f"nasdaq workdir, default=[{config.nasdaq.work_directory}]",
        required=False,
        default="",
    )
    parser.add_argument(
        "--reddit_work_dir",
        help=f"reddit work directory, default=[{config.reddit.work_directory}]",
        required=False,
        default="",
    )
    parser.add_argument("--quiet", "-q", help="be quiet", action="store_true")
    parser.add_argument(
        "--search",
        help=f"search [symbol] in reddit posts",
        nargs="+",
        required=False,
    )
    parser.add_argument(
        "--status", "-s", help="show status and exit", action="store_true"
    )
    parser.add_argument(
        "--update",
        help=f"update excel results",
        action="store_true",
        required=False,
    )
    parser.add_argument("--verbose", "-v", help="be more verbose", action="store_true")
    parser.add_argument(
        "--version", "-V", help="show version and exit", action="store_true"
    )
    # parse arguments
    args = parser.parse_args()

    # evaluate parsed arguments

    # setup logging
    if len(args.logfile) > 0:
        config.log_file_name = args.logfile
    if config.log_file_name is None or len(config.log_file_name) == 0:
        config.log_file_name = sys.argv[0] + ".log"
    if args.logging:
        config.logging = True
    if args.nologging:
        config.logging = False
    if config.logging:
        if config.log_level is None:
            if config.debug_level > 0:
                config.log_level = logging.DEBUG
            else:
                config.log_level = logging.INFO
        os.makedirs(config.log_directory, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(config.log_directory, config.log_file_name),
            filemode=config.log_file_mode,
            format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
            level=config.log_level,
        )
        logging.info("Logging initialized")

    if args.clean:
        config.clean_mode = 1
    if args.debug:
        config.debug_level += 1
    if args.force:
        config.force_mode = True
    if args.noclean:
        config.clean_mode = 0
    if args.nodebug:
        config.debug_level = 0
    if args.noforce:
        config.force_mode = False
    if args.verbose:
        config.verbose_level += 1
    if args.quiet:
        config.verbose_level = 0
    vblth = config.verbose_threshold
    dblth = config.debug_threshold

    # Args postprocessing
    # update paths
    if len(args.nasdaq_work_dir) > 0:
        config.nasdaq.work_directory = args.nasdaq_work_dir
    if len(args.reddit_work_dir) > 0:
        config.reddit.work_directory = args.reddit_work_dir

    # handle arguments / opcodes
    if args.version:
        config.verbose_level += 1
        show_version("all")
        exit(0)

    if args.status:
        config.verbose_level += 1
        show_status()
        exit(0)

    show_version()

    eh.debug_print(dblth, f"DEBUG: start {config.APP_VERNAME}")

    show_status()

    if main_status == 0:

        nasdaq_handler = nh.NasdaqHandler()
        reddit_handler = rh.RedditHandler()
        update_handler = uh.UpdateHandler()
        # do we download and process nasdaq listings ?
        if args.nasdaq_download is not None and args.nasdaq_download == True:
            eh.debug_print(
                dblth,
                f"DEBUG: download and process nasdaq listings from [{config.nasdaq.source_url}]",
            )
            nasdaq_handler.download_and_prepare()

        # make sure the pkl file path is set after nsdaq_download
        config.nasdaq.pkl_file_path = os.path.join(
            config.nasdaq.work_directory, f"{config.nasdaq.result_file_name}.pkl"
        )

        # do we crawl through the reddit posts ?
        if args.crawl is not None and args.crawl == True:
            eh.debug_print(
                dblth,
                f"DEBUG: crawl through the reddit posts [{config.reddit.use_subreddit}]",
            )
            reddit_handler.crawler()

        # do we search something :
        if args.search is not None and len(args.search) > 0:
            for symbol in args.search:
                reddit_handler.search(symbol)

        # do we update something :
        if args.update is not None and args.update == True:
            eh.debug_print(
                dblth,
                f"DEBUG: update excel result file [{config.updates.excel_result_name}]",
            )
            update_handler.pickle_to_result()

    # all done here
    main_elapsed = time.time() - main_start
    eh.debug_print(
        dblth,
        f"DEBUG: stop {config.APP_VERNAME}, duration={main_elapsed:2.4f} second(s), status={main_status}",
    )
    return main_status


# call main()
if __name__ == "__main__":
    terminate(main())
