import logging
import sys


class ColorFormatter(logging.Formatter):
    def __init__(self, log_format=None, date_format=None):
        grey = "\x1b[38;20m"
        teal = "\x1b[36;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"

        if log_format is None:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

        self.date_format = date_format

        self.FORMATS = {
            logging.DEBUG: grey + log_format + reset,
            logging.INFO: teal + log_format + reset,
            logging.WARNING: yellow + log_format + reset,
            logging.ERROR: red + log_format + reset,
            logging.CRITICAL: bold_red + log_format + reset,
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=self.date_format)
        return formatter.format(record)


def create_logger(filename=None, filemode="w"):
    """by default prints to stdout, if filename is provided, also write to file
    filemode controls append or overwrite"""

    # log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_fmt, datefmt=date_fmt)

    # get all loggers
    logger = logging.getLogger()

    # scope restrictions
    # logging.getLogger('matplotlib').setLevel(logging.WARNING)
    scopes = dict(matplotlib=logging.WARNING)  # TODO turn into an arg

    if scopes is not None:
        for module, level in scopes.items():
            logging.getLogger(module).setLevel(level)

    # for printing to stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)  # <- this needs to be set as a default argument

    sys.excepthook = handle_unhandled_exception

    # config logger for writing to file
    # file_handler = logging.FileHandler(filename="%s.log" % exp_name, mode='w')
    if filename is not None:
        file_handler = logging.FileHandler(filename=filename, mode=filemode)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(filename=None):
    # to return a previously created logger
    logger = create_logger(filename, filemode="a")
    return logger


# logging unhandled exceptions
def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    # TODO make this cleaner that it doesn't use global namespace
    logging.critical(
        "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
    )
