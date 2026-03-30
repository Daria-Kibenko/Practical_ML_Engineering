from base_metric import BaseMetric


class SimpsonMetric(BaseMetric):
    def calculate(self, tokens: list[str]) -> float:
        freq = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1

        n = len(tokens)
        return sum((v/n)**2 for v in freq.values()) if n else 0