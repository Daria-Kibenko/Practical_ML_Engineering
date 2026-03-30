from base_metric import BaseMetric


class YuleMetric(BaseMetric):
    def calculate(self, tokens: list[str]) -> float:
        freq = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1

        m1 = len(tokens)
        m2 = sum(v * v for v in freq.values())

        return (m2 - m1) / (m1 * m1) if m1 else 0
