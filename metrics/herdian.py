from base_metric import BaseMetric
import math


class HerdianMetric(BaseMetric):
    def calculate(self, tokens: list[str]) -> float:
        n = len(tokens)
        v = len(set(tokens))

        return math.log(v) / math.log(n) if n > 1 else 0