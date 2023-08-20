import logging
from typing import Iterable

from hubstation.collector.base import BaseCollector

logger = logging.getLogger(__name__)


class WebCollection(BaseCollector):


    deepLevel = 0

    def extract(self) -> Iterable[str]:
        pass

