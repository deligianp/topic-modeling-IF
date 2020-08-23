from abc import ABCMeta, abstractmethod
from resources import stopwords
from resources.util import functions

import string
import json
import nltk
import inspect
import sys

class BasePreprocessor(metaclass=ABCMeta):

    @abstractmethod
    def perform_preprocess(self, text_data):
        pass


class DefaultPreprocessor(BasePreprocessor):
    """
    A default implementation of a preprocessor factory.

    The proper format for defining a preprocessor of this factory is "default [*MINIMUM_TERMS_PER_DOCUMENT]
    [*MINIMUM_CHARACTERS_PER_TERM]". The two arguments are optional and if omitted they get values
    MINIMUM_TERMS_PER_DOCUMENT=10 and MINIMUM_CHARACTERS_PER_TERM=3.

    Each preprocessor created performs the following transformations on each text
        1. Remove punctuation except the dash('-')
        2. Turn every text to lowercase
        3. Lemmatize then stem each term

    The preprocessor also makes sure that each document given has a non-empty string text representation. It also checks
    whether a document has at least MINIMUM_TERMS_PER_DOCUMENT terms and each term has at least
    MINIMUM_CHARACTERS_PER_TERM characters
    """

    stopwords_set = stopwords.stopwords
    lemmatizer = nltk.stem.WordNetLemmatizer()
    stemmer = nltk.stem.SnowballStemmer("english")
    minimum_term_length=3
    minimum_terms_per_document=10

    def __init__(self, *args, **kwargs):
        super(DefaultPreprocessor, self).__init__(*args, **kwargs)
        functions.nltk_verify_resource("tokenizers/punkt", "punkt")
        functions.nltk_verify_resource("corpora/wordnet", "wordnet")

    def perform_preprocess(self, input_document_tuple, **kwargs):
        if "worker_logger" in kwargs:
            if "worker_id" in kwargs:
                kwargs["worker_logger"].debug("{}: Got article {}".format(kwargs["worker_id"], input_document_tuple[0]))
            else:
                kwargs["worker_logger"].debug("Got article {}".format(input_document_tuple[0]))
        nonstemmed = dict()
        text = input_document_tuple[1]
        assert type(text) is str, "Document \"{}\" does not have a string text".format(input_document_tuple[0])
        assert text != "", "Document \"{}\" has no text".format(input_document_tuple[0])

        table = str.maketrans('', '', string.punctuation.replace('-', ''))
        no_punctuation = text.lower().translate(table)
        terms = nltk.tokenize.word_tokenize(no_punctuation)
        stemmed_terms = list()
        for term in terms:
            if term not in self.stopwords_set and term.isalpha():
                stemmed = self.stemmer.stem(self.lemmatizer.lemmatize(term))
                if len(stemmed) >= self.minimum_term_length:
                    stemmed_terms.append(stemmed)
                    if stemmed not in nonstemmed:
                        nonstemmed[stemmed] = dict()
                    if term not in nonstemmed[stemmed]:
                        nonstemmed[stemmed][term] = 1
                    else:
                        nonstemmed[stemmed][term] += 1

        if len(stemmed_terms) >= self.minimum_terms_per_document:
            output_article_tuple = *input_document_tuple[:1], " ".join(stemmed_terms), *input_document_tuple[2:]
            return [output_article_tuple, json.dumps(nonstemmed)]
        else:
            raise Exception("Too few terms for document \"{}\"".format(input_document_tuple[0]))


available_preprocessors = {
    (cl[0].lower()[:-len("Preprocessor")] if cl[0].endswith("Preprocessor") else cl[0].lower()): cl[1]
    for cl in inspect.getmembers(sys.modules[__name__], inspect.isclass) if
    (issubclass(cl[1], BasePreprocessor) and cl[0] != "BasePreprocessor")
}
