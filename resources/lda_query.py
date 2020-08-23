import gensim.models as g_models
import resources.configuration as config
import thesis_ui.models as models
from nltk import stem, tokenize
import string
from resources import stopwords as sw

MINIMUM_WORDS_PER_TEXT = 10


class PreprocessingError(ValueError):
    pass

def preprocess_text(text):
    # Remove punctuation and turn to lowercase
    table = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz',
                          string.punctuation.replace('-', ''))
    no_punc_text = text.translate(table)
    if no_punc_text.strip() != "":
        # Tokenization
        tokens = tokenize.word_tokenize(no_punc_text)
        if len(tokens) > MINIMUM_WORDS_PER_TEXT:
            index = 0
            while index < len(tokens):
                if sw.is_stopword(tokens[index]):
                    del tokens[index]
                else:
                    if not str.isalpha(tokens[index]):
                        del tokens[index]
                    else:
                        lemmatizer = stem.WordNetLemmatizer()
                        stemmer = stem.snowball.SnowballStemmer('english')
                        tokens[index] = stemmer.stem(lemmatizer.lemmatize(tokens[index], pos='n'))
                        if len(tokens[index]) < 3:
                            del tokens[index]
                        else:
                            index += 1
            if len(tokens) > MINIMUM_WORDS_PER_TEXT:
                return tokens
            raise PreprocessingError("Too small text after preprocessing")
        raise PreprocessingError("Too small text")
    raise PreprocessingError("Text is either empty or in an unknown encoding")


def query_lda_on_text(text_tokens):
    lda_model_path = models.LdaModel.objects.get(name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"]).path
    lda_model = g_models.LdaModel.load(lda_model_path)
    text_bow_vector = lda_model.id2word.doc2bow(text_tokens)
    all_document_topics = lda_model.get_document_topics(text_bow_vector, minimum_probability=0)
    return tuple(sorted(all_document_topics, key=lambda item: item[1], reverse=True)[
                 :config.CONFIG_VALUES["TOP_N_DOCUMENT_TOPICS"]])


def analyze_text(text):
    abstract_tokens = preprocess_text(text)
    top_n_document_topics = query_lda_on_text(abstract_tokens)
    return top_n_document_topics
