"""Base transformer"""


class BaseTransformer:
    """Base transformer"""

    def __init__(self, settings):
        self.settings = settings

    def transform(self, data: str) -> str:
        """Transform data"""
