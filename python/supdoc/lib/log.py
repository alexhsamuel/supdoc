import functools
import inspect
import logging
from   logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from   logging import debug, info, warning, error, critical

from   . import itr
from   . import py

#-------------------------------------------------------------------------------

# FIXME: Do better.
logging.basicConfig(
    format="%(asctime)s.%(msecs)03d [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S")


#-------------------------------------------------------------------------------

LEVEL_NAMES = dict(
    DEBUG   =DEBUG, 
    INFO    =INFO, 
    WARING  =WARNING,
    ERROR   =ERROR, 
    CRITICAL=CRITICAL,
)
    

def ensure_level(level):
    try:
        level = int(level)
    except:
        try:
            level = LEVEL_NAMES[str(level).upper()]
        except KeyError:
            raise ValueError("not a log level: {}".format(level))
    if 0 < level:
        return level
    else:
        raise ValueError("invalid log level: {}".format(level))


def add_option(parser):
    """
    Adds a logging command-line option to an `argparse.Parser`.
    """
    import argparse

    class Action(argparse.Action):

        def __call__(self, parser, namespace, value, option_string):
            level = ensure_level(value)
            logging.getLogger().setLevel(level)

    parser.add_argument(
        "--log", metavar="LEVEL", default="WARNING", action=Action,
        help="set root logging level to LEVEL")
    

#-------------------------------------------------------------------------------

def get(name=None):
    """
    Returns the logger for `name`.

    @param name
      The logger name.  If `None`, uses the caller's global `__name__`.
    """
    if name is None:
        frame = inspect.stack()[1][0]
        try:
            name = frame.f_globals["__name__"]
        except KeyError:
            logging.warning("caller has no __name__; using root logger")
            name = None
    return logging.getLogger(name)


#-------------------------------------------------------------------------------

def log_call(log=logging.debug, *, show_self=False):
    """
    Returns a decorator that logs calls to a method.

    Example::

      @log_call(logger.info)
      def my_function(x, y):
          return 2 * x + y

      >>> my_function(3, 4)
      [INFO] my_function(3, 4)
      10

    @param log
      The logging method to use for logging calls.
    @param show_self
      If false and the decorated function's first argument is named "self",
      the first argument is not included in the log.
    """
    def log_call(fn):
        name = fn.__name__
        remove_self = (
            not show_self 
            and itr.nth(inspect.signature(fn).parameters, 0) == "self"
        )

        @functools.wraps(fn)
        def wrapped(*args, **kw_args):
            log(py.format_call(
                name, *(args[1 :] if remove_self else args), **kw_args))
            return fn(*args, **kw_args)

        return wrapped

    return log_call



