from utils.tokenizer import Tokenizer


class CorpusService:
    def __init__(self):
        self.__corpora = {}

    def add_corpus(self, corpus_id: str, text: str):
        self.__corpora[corpus_id] = text

    def get_tokens(self, corpus_id: str) -> list[str]:
        text = self.__corpora.get(corpus_id, "")
        return Tokenizer.tokenize(text)