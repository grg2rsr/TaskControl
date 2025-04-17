# from https://stackoverflow.com/a/56944256/4749250

import logging


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    teal = "\x1b[36;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: teal + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(level="debug"):
    if level == "debug":
        level = logging.DEBUG
    if level == "info":
        level = logging.INFO
    if level == "warning":
        level = logging.WARNING
    if level == "error":
        level = logging.ERROR
    if level == "critical":
        level = logging.CRITICAL

    # create logger with 'spam_application'
    logger = logging.getLogger()
    logger.setLevel(level)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(level)

    ch.setFormatter(CustomFormatter())

    logger.addHandler(ch)
    return logger


if __name__ == "__main__":
    logger = get_logger(level="debug")
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
