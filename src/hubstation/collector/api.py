import logging
from typing import Iterable

from hubstation.collector.base import BaseCollector

logger = logging.getLogger(__name__)


class APICollection(BaseCollector):

    def extract(self) -> Iterable[str]:
        pass

