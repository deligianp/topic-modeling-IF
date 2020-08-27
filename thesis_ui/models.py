from django.db import models
from django.db import connection
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MinValueValidator, MaxValueValidator
from resources.configuration import CONFIG_VALUES
import psycopg2


# Create your models here.
class LdaModel(models.Model):
    name = models.CharField(max_length=30, unique=True)
    is_main = models.BooleanField(verbose_name="This LDA model is the main model")
    path = models.FilePathField(verbose_name="Model location",
                                recursive=True,
                                unique=True)
    description = models.CharField(max_length=50)
    # number_of_topics = models.PositiveIntegerField(validators=(MinValueValidator(1),))
    # number_of_terms = models.PositiveIntegerField(validators=(MinValueValidator(1),))
    # terms_dictionary_path = models.CharField(max_length=200)
    # non_stemmed_terms_dictionary_path = models.CharField(max_length=200, blank=True)
    training_context = models.TextField(max_length=200, null=True, blank=True,
                                        help_text="An optional more detailed text about the corpus that the model was "
                                                  "trained on and its properties")
    preprocessor_name = models.TextField(max_length=64, default="default",
                                         help_text="Name of the preprocessor to be used for custom texts when this "
                                                   "model is set to the application's main LDA model.")
    use_tfidf = models.BooleanField(default=False, help_text="Whether to use tf-idf vectorization for any custom text. "
                                                             "The tf-idf vectorization will be calculated with respect "
                                                             "to the term frequencies of the training corpus.")

    def __str__(self):
        return "Model {}({})".format(self.name, self.description) + (" - MAIN MODEL" if self.is_main else "")

    # @classmethod
    # def create(cls, name, path, description, number_description, number_of_terms, training_context):
    #     error_code = cls(error_description=error_description)
    #     return error_code


class Topic(models.Model):
    index = models.PositiveIntegerField()
    keyphrase = models.CharField(max_length=64, blank=True)
    parent_model = models.ForeignKey(LdaModel, on_delete=models.CASCADE, related_name="model_topics")

    def __str__(self):
        return "Topic {} of model: {}".format(self.index, self.parent_model.name)


class Term(models.Model):
    string = models.CharField(max_length=200, help_text="The actual term value", unique=True)
    parent_topics = models.ManyToManyField(Topic, related_name="topic_terms", through="TopicTermDistribution")

    class Meta:
        indexes = [models.Index(fields=("string",))]

    def __str__(self):
        return self.string


class Corpus(models.Model):
    name = models.CharField(max_length=32, verbose_name="Application-wide unique name identifying the corpus")
    description = models.CharField(max_length=64, verbose_name="A readable name/description for the corpus")


class Article(models.Model):
    identifier = models.CharField(max_length=100, verbose_name='Article identifier', unique=True)
    abstract = models.TextField(verbose_name="Abstract")
    title = models.CharField(max_length=500, verbose_name="Article title", blank=True)
    year = models.PositiveIntegerField(verbose_name="Year of publication", validators=(MinValueValidator(1930),),
                                       null=True, blank=True)
    authors = models.TextField(verbose_name="Authors and collaborators", blank=True)
    language = models.CharField(max_length=20, verbose_name="Language", blank=True)

    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)

    topics = models.ManyToManyField(Topic, related_name="article_topics", through="ArticleTopicDistribution")

    search_vector = SearchVectorField(null=True)

    def __str__(self):
        return self.title if self.title != "" else self.identifier

    class Meta:
        indexes = [GinIndex(fields=['search_vector']), models.Index(fields=['identifier'])]


class ReportedError(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE)
    error_description = models.CharField(max_length=80)

    def __str__(self):
        return self.error_description


class TopicTermDistribution(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=6, decimal_places=5, validators=(MinValueValidator(0), MaxValueValidator(1)),
                                help_text="The probability of the given term to exist in the given topic")

    def __str__(self):
        return "{} - {}, probability: {}".format(self.topic, self.term, self.value)


class ArticleTopicDistribution(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    rank = models.IntegerField(validators=(MinValueValidator(1),))
    value = models.DecimalField(max_digits=6, decimal_places=5, validators=(MinValueValidator(0), MaxValueValidator(1)))

    def __str__(self):
        return "{} - {}, probability: {}".format(self.article, self.topic, self.value)


class Comparison(models.Model):
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=50)
    type_of_comparison = models.SmallIntegerField(
        help_text="A score comparison indicates that the comparison of two topics is a score, meaning that the higher "
                  "the value, the better. In contrast, a distance comparison of two topics gives a divergence of "
                  "similarity of the two topics, thus the smaller the value, the better.",
        choices=((0, "Score comparison"), (1, "Distance comparison")))
    lower_bound = models.FloatField(blank=True, null=True,
                                    help_text="Lowest value of the comparison metric. Leave empty if it cannot be "
                                              "defined")
    upper_bound = models.FloatField(blank=True, null=True,
                                    help_text="Highest value of the comparison metric. Leave empty if it cannot be "
                                              "defined")
    lda_model_0 = models.ForeignKey(LdaModel, related_name="comparison_first_model", on_delete=models.CASCADE)
    lda_model_1 = models.ForeignKey(LdaModel, related_name="comparison_second_model", on_delete=models.CASCADE)

    def __str__(self):
        return "{}: Comparing models {}, {}".format(self.name, self.lda_model_0.name, self.lda_model_1.name)


class TopicsComparison(models.Model):
    parent_comparison = models.ForeignKey(Comparison, related_name="topics_measurement", on_delete=models.CASCADE)
    topic_0 = models.ForeignKey(Topic, related_name="comparison_first_topic", on_delete=models.CASCADE)
    # TODO: what happens if i delete a corresponding model, do they get deleted by topic, by comparison or an error is thrown?
    topic_1 = models.ForeignKey(Topic, related_name="comparison_second_topic", on_delete=models.CASCADE)
    value = models.FloatField()  # TODO: can i limit it inside the parent comparison's bounds

    def __str__(self):
        return "{}({}, {})={}".format(self.parent_comparison.name, self.topic_0, self.topic_1, self.value)


class Word(models.Model):
    string = models.CharField(max_length=220, unique=True)
    rank = models.PositiveIntegerField()
    stemmed = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="original_word")

    def __str__(self):
        return "{}".format(self.string)

    @classmethod
    def truncate(cls):
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE "{0}" CASCADE'.format(cls._meta.db_table))
