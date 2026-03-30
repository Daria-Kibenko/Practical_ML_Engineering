from base_model import BaseModel


class HeapsModel(BaseModel):

    def name(self) -> str:
        return "heaps_model"

    def analyze(self, tokens: list[str]) -> dict:
        vocab = len(set(tokens))
        n = len(tokens)

        return {"heaps_k": vocab / (n ** 0.5) if n else 0}