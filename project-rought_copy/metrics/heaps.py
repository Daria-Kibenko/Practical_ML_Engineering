from base_metric import BaseMetric


class HeapsMetric(BaseMetric):
    def calculate(self, tokens: list[str]) -> float:
        return len(set(tokens)) / (len(tokens) ** 0.5) if tokens else 0