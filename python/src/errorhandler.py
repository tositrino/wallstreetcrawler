"""
Centralised error handling. Contains function definitions of prints to be used for various occasions.
"""

import datetime
import io
import logging
import os
import sys
import time
import config.main as config

# output


def print_ub(*vargs, **kwargs):
    """print_up() - unbuffered console print
    Args:
        *vargs        : print args (variable args)
    Returns:
        int           : 0 on success, else errorcode
    """
    print(*vargs, **kwargs)
    sys.stdout.flush()
    return 0


def debug_print(thresh: int, *vargs, **kwargs):
    """debugPrint() - unbuffered console print if debug level set above threshold
    Args:
        thresh        > threshhold, print only if thresh>=config.debugLevel
        *vargs        : print args (variable args)
    Returns:
        int           : 0 on success, else errorcode
    """
    if config.debug_level < thresh and config.logging == False:
        return
    sio = io.StringIO()
    print(*vargs, file=sio, end="")
    if config.logging:
        logging.debug(sio.getvalue())
    if config.debug_level >= thresh:
        print_ub(sio.getvalue(), **kwargs)
    return 0


def verbose_print(thresh, *vargs, **kwargs):
    """verbosePrint() - unbuffered console print if verbosity level set above threshold
    Args:
        thresh        > threshhold, print only if thresh>=config.verboseLevel
        *vargs        : print args (variable args)
    Returns:
        int           : 0 on success, else errorcode
    """
    if config.verbose_level < thresh and config.logging == False:
        return
    sio = io.StringIO()
    print(*vargs, file=sio, end="")
    if config.logging:
        logging.info(sio.getvalue())
    if config.verbose_level >= thresh:
        print_ub(sio.getvalue(), **kwargs)
    return 0


# exit handling


def atexit(afn):
    """atexit function implementation (see c, c++)
    Args:
        afn           : atexit function
    Returns:
        int           : 0 on success, else errorcode(-2 for invalid argument)
    """
    dbth = config.debug_threshold
    rc = -2
    if afn is not None:
        if config.debug_level >= dbth:
            try:
                fn = afn.__name__
            except:
                fn = str(afn)
            debug_print(
                dbth,
                "DEBUG: {0}.errhandler.atexit() - append function{1}".format(
                    config.APP_VERNAME, fn
                ),
            )
        config.atexit_list.append(afn)
    rc = 0
    return rc


def enforceRetcode(rc: int):
    """enforce a specific return code. after using this function, the application
       will always return theis code, no matter what errors will occur between this
       call and termination
    Args:
        rc(int)       : return code to enforce
    Returns:
        the last force_return_code
    """
    if rc != 0:
        config.force_return_code = rc
        config.return_code = rc


def terminate(msg="", rc=0):
    """call defined atexit routines and then terminate the program
    Args:
        msg(str)      : a final message
        rc(int)       : return code (for the system)
    Returns:
        should not return at all, otherwise there is a severe problem, so it always
        returns -1
    """
    dbth = config.debug_threshold
    if config.in_termination:
        debug_print(
            dbth,
            "DEBUG: {0}.errhandler.terminate(): already in termination".format(
                config.APP_VERNAME
            ),
        )
        return -1
    config.in_termination = True
    debug_print(
        dbth,
        "DEBUG: {0}.errhandler.terminate():".format(config.APP_VERNAME),
    )
    while len(config.atexit_list) > 0:
        afn = config.atexit_list.pop()
        if afn is not None:
            if config.debug_level >= dbth:
                try:
                    fn = afn.__name__
                except:
                    fn = str(afn)
                debug_print(
                    dbth,
                    "DEBUG: {0}.errhandler.atexit() - calling function{1}".format(
                        config.APP_VERNAME, fn
                    ),
                )
        afn()
    showWarnings()
    showErrors()
    verbose_print(0, msg)

    if config.force_return_code != 0:
        config.return_code = config.force_return_code
    elif config.return_code == 0:
        config.return_code = rc

    debug_print(
        dbth,
        "DEBUG: {0}.errhandler.terminate() exiting with retCode={1}".format(
            config.APP_VERNAME, config.return_code
        ),
    )
    sys.exit(config.return_code)
    return -1


# errors


def addError(msg: str, **kwargs):
    """add error string to error message list
    Args:
        msg(str)    : an error message
        name=str    : optional name, defaults to "ERROR"
        level=val   : optional userlevel value, where 0 is the default
                      and means "no special relevance"
    Returns:
        int         : number of messages in list
    """
    name = kwargs.get("name", "ERROR")
    msgrec = {
        "name": name,
        "level": int(kwargs.get("level", "0")),
        "message": "{0}: {1}".format(name, msg),
    }
    config.error_count += 1
    config.error_messages.append(msgrec)
    # print("errorhandler.addError:() msg=[{0}]".format(msg))
    # for key, value in kwargs.items():
    #    print("errorhandler.addError:() {0}={1}".format(key, value))
    return len(config.error_messages)


def showErrors():
    """show/print error from list and clear list
    Args:
        none
    Returns:
        int           : number of messages printed
    """
    if config.error_count == 0:
        return
    ec = 0
    for msg in config.error_messages:
        verbose_print(0, "{0}".format(msg.get("message", "invalid error")))
        ec += 1
    config.error_count = 0
    config.error_messages = []
    if config.max_errors > 0 and ec > config.max_errors:
        terminate(
            "FATAL: too many errors ({0} of {1}), exiting".format(
                ec, config.max_errors
            ),
            1,
        )
    return ec


# warnings


def addWarning(msg: str, **kwargs):
    """add warning string to warning message list
    Args:
        msg(str)  : a warning message
        name=str      : optional name, defaults to WARNING
        level=val     : optional userlevel value, where 0 is the default
                        and means "no special relevance"
    Returns:
        int           : number of messages in list
    """
    name = kwargs.get("name", "WARNING")
    msgrec = {
        "name": name,
        "level": int(kwargs.get("level", "0")),
        "message": "{0}: {1}".format(name, msg),
    }
    config.warn_count += 1
    config.warn_messages.append(msgrec)
    # print("errorhandler.addWarning:() msg=[{0}]".format(msg))
    # for key, value in kwargs.items():
    #    print("errorhandler.addWarning:() {0}={1}".format(key, value))
    return len(config.warn_messages)


def showWarnings():
    """show/print warnings from list and clear list
    Args:
        none
    Returns:
        int           : number of messages printed
    """
    wc = 0
    if config.warn_count == 0:
        return
    for msg in config.warn_messages:
        print_ub("{0}".format(msg.get("message", "invalid warning")))
        wc += 1
    config.warn_count = 0
    config.warn_messages = []
    if config.max_warnings > 0 and wc > config.max_warnings:
        terminate(
            "FATAL: too many warnings ({0} of {1}), exiting".format(
                wc, config.max_warnings
            ),
            1,
        )
    return wc
