from models.zipf_model import ZipfModel
from models.heaps_model import HeapsModel
from models.diversity_model import DiversityModel


class MLService:
    def __init__(self):
        self.__models = {
            "zipf": ZipfModel(),
            "heaps": HeapsModel(),
            "diversity": DiversityModel()
        }

    def run_model(self, model_name: str, tokens: list[str]) -> dict:
        model = self.__models.get(model_name)
        if not model:
            raise ValueError("Model not found")

        return model.analyze(tokens)
