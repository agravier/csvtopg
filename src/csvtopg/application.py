import logging

from csvtopg.configuration import Config

log = logging.getLogger(__name__)


class CSVToPg:
    def __init__(self, config: Config):
        self.config = config
        log.debug("Configured: %s", self.config)
