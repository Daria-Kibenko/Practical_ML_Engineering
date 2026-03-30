from base_model import BaseModel
from collections import Counter


class ZipfModel(BaseModel):

    def name(self) -> str:
        return "zipf_model"

    def analyze(self, tokens: list[str]) -> dict:
        freq = Counter(tokens)
        values = sorted(freq.values(), reverse=True)

        if len(values) < 2:
            return {"zipf_ratio": 0.0}

        return {"zipf_ratio": values[0] / values[1]}