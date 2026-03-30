class Tokenizer:

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return text.lower().split()
