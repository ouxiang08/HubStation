import logging
from typing import Iterable

from hubstation.collector.base import BaseCollector

logger = logging.getLogger(__name__)


class RSSCollection(BaseCollector):

    def extract(self) -> Iterable[str]:
        pass

