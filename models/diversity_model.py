from base_model import BaseModel
from metrics.yule import YuleMetric
from metrics.simpson import SimpsonMetric


class DiversityModel(BaseModel):

    def name(self) -> str:
        return "diversity_model"

    def analyze(self, tokens: list[str]) -> dict:
        return {
            "yule": YuleMetric().calculate(tokens),
            "simpson": SimpsonMetric().calculate(tokens)
        }