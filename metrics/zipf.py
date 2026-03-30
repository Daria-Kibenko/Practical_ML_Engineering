from base_metric import BaseMetric
from collections import Counter


class ZipfMetric(BaseMetric):
    def calculate(self, tokens: list[str]) -> float:
        freq = Counter(tokens)
        values = sorted(freq.values(), reverse=True)

        return values[0] / values[1] if len(values) > 1 else 0