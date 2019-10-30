import logging

from jet_bridge_base import settings


logger = logging.getLogger('jet_bridge')
level = logging.DEBUG if settings.DEBUG else logging.INFO

ch = logging.StreamHandler()


class Formatter(logging.Formatter):

    formats = {
        logging.INFO: '%(message)s'
    }
    default_format = '%(levelname)s - %(asctime)s: %(message)s'

    def formatMessage(self, record):
        return self.formats.get(record.levelno, self.default_format) % record.__dict__

formatter = Formatter('%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S')

ch.setFormatter(formatter)
ch.setLevel(level)

logger.setLevel(level)
logger.addHandler(ch)
