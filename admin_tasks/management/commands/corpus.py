import numpy as np
from thesis_ui.models import Corpus, Article
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.utils.text import slugify
from django.contrib.postgres.search import SearchVector
from django.core.management import BaseCommand
from gensim.models import LdaModel as GensimLdaModel
from resources.util import docfetch
from resources import readers
import time
import textwrap


class Command(BaseCommand):
    help = "Command for loading, listing, updating and removing corpora from the application's database"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command", help="Use \"[COMMAND] -h\" to display the related help "
                                                                "messages for each command")

        load_subparser = subparsers.add_parser("load")
        load_subparser.add_argument(
            "reader", help="The reader to be used in order to retrieve the articles and store them inside the "
                           "database. Readers should be defined inside resources.readers",
            choices=readers.available_readers
        )
        load_subparser.add_argument("corpus_files_paths",
                                    help="Paths to the corpus files that will be used to retrieve the articles",
                                    nargs="+")
        load_subparser.add_argument("name", help="Application-wide unique name identifying the corpus",
                                    type=lambda x: x[:32]
                                    )
        load_subparser.add_argument(
            "description", help="A readable name/description for the corpus",
            type=lambda x: x[:64]
        )

        list_subparser = subparsers.add_parser("list")
        list_subparser.add_argument("--detailed", action="store_true",
                                    help="If set, the command will respond with a detailed listing of the stored "
                                         "LdaModels and their attributes")

        delete_subparser = subparsers.add_parser("delete")
        delete_subparser.add_argument("name", help="Name of the LDA model to be deleted")

        update_subparser = subparsers.add_parser("update")
        update_subparser.add_argument("name", help="Current name of the target LDA model")
        update_subparser.add_argument("-n", "--new-name", type=lambda x: slugify(x[:30]),
                                      help="The new name of the LDA model")
        update_subparser.add_argument("-d", "--description", type=lambda x: x[:50],
                                      help="The new description of the model")
        update_subparser.add_argument("-t", "--training-context", type=lambda x: x[:200],
                                      help="The new training context of the model")
        update_subparser.add_argument("--main", action="store_true",
                                      help="If set, then the targeted LDA model will be set as the application's main "
                                           "LDA model")
        update_subparser.add_argument("--demote", action="store_true",
                                      help="If set and the \"--main\" flag is not used, then demotes the target LDA "
                                           "model if it is set as the main LDA model.")
        update_subparser.add_argument("-p", "--preprocessor-name", type=lambda x: x[:64],
                                      help="The new preprocessor name as defined inside the resources.preprocessors "
                                           "module", default="default")
        update_subparser.add_argument("--bow", help="If set, any new texts will be vectorized using the bag-of-words "
                                                    "vectorization", action="store_true")
        update_subparser.add_argument("--tfidf", action="store_true",
                                      help="If set and the \"--bow\" flag is not used, any new texts will be "
                                           "vectorized using the bag-of-words vectorization")

    def handle(self, *args, **options):
        action = options["command"]
        if action == "delete":
            pass
            # model_name = options["name"]
            # try:
            #     delete_model(model_name)
            # except LdaModel.DoesNotExist as lda_dne:
            #     print(str(lda_dne))
        elif action == "list":
            pass
            # list_models(options["detailed"])
        elif action == "load":
            reader_class = readers.available_readers[options["reader"]]
            corpus_files_paths = options["corpus_files_paths"]
            name = options["name"]
            description = options["description"]

            reader = reader_class(*corpus_files_paths)
            try:
                load_corpus(reader, name, description)
            except FileNotFoundError as fnfe:
                print(str(fnfe))
            except IntegrityError as int_err:
                print(str(int_err))
            except Exception as ex:
                print(str(ex))
        else:
            pass
            # model_name = options["name"]
            # new_model_name = options["new_name"]
            # description = options["description"]
            # training_context = options["training_context"]
            # set_main = options["main"]
            # demote = options["demote"]
            # try:
            #     update_model(model_name, new_name=new_model_name, description=description,
            #                  training_context=training_context,
            #                  set_main=set_main, demote=demote)
            # except LdaModel.DoesNotExist as lda_dne:
            #     print(
            #         str(lda_dne) + "\nCouldn't find an LdaModel with name \"{}\".\nUse the list_models command to get "
            #                        "a list of the available models.".format(model_name))
            # except IntegrityError as int_err:
            #     print(str(int_err) + "\nMake sure that any new model name given, is unique for all stored models.\nUse "
            #                          "the list_models command to get a list of the available models.")
            # except Exception as ex:
            #     print(str(ex))


def load_corpus(reader, name, description, batch=10000, callback=lambda *args: None):
    max_items_to_write = 0
    try:
        for _ in reader:
            max_items_to_write += 1
    except Exception as ex:
        print(str(ex))

    total = 1 + 2 * max_items_to_write
    completed = 0

    callback(0, 100, "Creating corpus object")
    with transaction.atomic():
        corpus_object = Corpus(name=name, description=description)
        corpus_object.save()

        completed += 1
        callback(completed, total, "Created corpus object")
        with transaction.atomic():
            articles_batch = list()
            articles_loaded = 0
            for document in reader:
                batch_articles_loaded = 0
                identifier = document[0]
                abstract = document[1]
                title = document[2].get("title", identifier)
                year = document[2].get("year", None)
                authors = ", ".join(document[3].get("authors", [""]))
                language = document[2].get("language", "")

                articles_batch.append(Article(identifier=identifier, abstract=abstract, title=title, year=year,
                                              authors=authors, language=language, corpus=corpus_object))
                articles_loaded += 1
                batch_articles_loaded += 1
                if batch_articles_loaded >= batch:
                    Article.objects.bulk_create(articles_batch, ignore_conflicts=True)
                    with transaction.atomic():
                        for article in articles_batch:
                            article.search_vector = SearchVector('title', weight='A') + SearchVector('abstract',
                                                                                                     weight='B')
                        Article.objects.bulk_update(articles_batch)

                    completed += 2 * batch_articles_loaded
                    articles_batch = list()
                    callback(completed, total, "Loaded {} articles".format(completed - 1))
            if len(articles_batch) >= batch:
                Article.objects.bulk_create(articles_batch, ignore_conflicts=True)
                with transaction.atomic():
                    for article in articles_batch:
                        article.search_vector = SearchVector('title', weight='A') + SearchVector('abstract',
                                                                                                 weight='B')
                    Article.objects.bulk_update(articles_batch)

                completed += 2 * len(articles_batch)
                articles_batch = list()
                callback(completed, total, "Loaded {} articles".format(completed - 1))
            callback(100, 100, "Corpus {} loaded".format(corpus_object.name))
    return name, description, articles_loaded
# def create_model(name, path, description, training_context="", main=False, topn=50,
#                  preprocessor_name="", use_tfidf=False, callback=lambda *args: None):
#     new_name = slugify(name)
#     description = description or name
#     training_context = training_context or ""
#     preprocessor_name = preprocessor_name or "default"
#
#     # Can raise a FileNotFoundError
#     callback(0, 100, "Attempting to load model from \"{}\"".format(path))
#     model_obj = GensimLdaModel.load(path)
#     num_topics = model_obj.num_topics
#     dictionary = model_obj.id2word
#     topic_terms_matrix = model_obj.get_topics()
#     topn_topic_terms_indices = np.flip(np.argsort(topic_terms_matrix), axis=1)[:, :topn]
#
#     total = 2 + num_topics + 2 * num_topics * topn
#     completed = 0
#
#     with transaction.atomic():
#         new_model = LdaModel(name=new_name, path=path, description=description, training_context=training_context,
#                              is_main=main, preprocessor_name=preprocessor_name, use_tfidf=use_tfidf)
#         new_model.save()
#         completed += 1
#         callback(completed, total, "Created model \"{}\"".format(new_name))
#
#         terms = dict()
#         for topic_index in range(len(topn_topic_terms_indices)):
#             for term_index in topn_topic_terms_indices[topic_index]:
#                 if term_index not in terms:
#                     term = Term.objects.get_or_create(string=dictionary[term_index])[0]
#                     terms[term_index] = term
#
#             completed += topn
#             callback(completed, total, "Creating model's terms")
#
#         with transaction.atomic():
#             topics = {topic_index: Topic(index=topic_index, keyphrase="", parent_model=new_model) for topic_index in
#                       range(num_topics)}
#             Topic.objects.bulk_create(list(topics.values()))
#
#             completed += num_topics
#             round_string = "Created model's terms and topics"
#             callback(completed, total, round_string)
#
#             with transaction.atomic():
#                 topic_term_distributions = list()
#                 for topic_index in topics:
#                     for term_index in topn_topic_terms_indices[topic_index]:
#                         topic_term_distributions.append(
#                             TopicTermDistribution(topic=topics[topic_index], term=terms[term_index],
#                                                   value=topic_terms_matrix[topic_index, term_index]))
#                     completed += topn
#                     round_string = "Connecting topics to terms"
#                     callback(completed, total, round_string)
#                 TopicTermDistribution.objects.bulk_create(topic_term_distributions)
#                 Term.objects.filter(topictermdistribution__isnull=True).distinct().delete()
#                 if main:
#                     with transaction.atomic():
#                         LdaModel.objects.filter(~Q(name=new_model.name)).update(is_main=False)
#     return name, num_topics, path, main
#
#
# def delete_model(name, callback=lambda *args: None):
#     retrieved_model = LdaModel.objects.filter(name=name)
#     if retrieved_model.count() == 0:
#         raise LdaModel.DoesNotExist("No models were found with name \"{}\"".format(name))
#     with transaction.atomic():
#         Term.objects.annotate(num_of_models=Count("topictermdistribution__topic__parent_model", distinct=True)).filter(
#             num_of_models=1, topictermdistribution__topic__parent_model__name=name).delete()
#         retrieved_model.delete()
#     return name
#
#
# def update_model(name, new_name=None, description=None, training_context=None, set_main=False, demote=False,
#                  preprocessor_name=None, use_tfidf=False, use_bow=False, callback=lambda *args: None):
#     model = LdaModel.objects.get(name=name)
#
#     if new_name is not None:
#         model.name = slugify(new_name)
#
#     if description is not None:
#         model.description = description
#
#     if training_context is not None:
#         model.training_context = training_context
#
#     if set_main or demote:
#         model.is_main = set_main
#
#     if preprocessor_name is not None:
#         model.preprocessor_name = preprocessor_name
#
#     if use_bow or use_tfidf:
#         model.use_tfidf = not use_bow
#
#     with transaction.atomic():
#         if set_main:
#             LdaModel.objects.filter(~Q(name=name), is_main=True).update(is_main=False)
#         model.save()
#     return new_name, description, training_context
#
#
# def list_models(detailed=False):
#     stored_models = LdaModel.objects.all().values().annotate(num_topics=Count('model_topics'))
#     output_strings = list()
#     if detailed:
#         for i in range(len(stored_models)):
#             output_strings.append(
#                 "\n".join(docfetch.sanitize_docstring("{}. {}{} with {} topics\n\n\t{}{}\n\n\t- Loaded from "
#                                                       "\"{}\"\n\n\t- Preprocessor name: {}\n\n\t- Use tf-idf: "
#                                                       "{}".format(
#                     i,
#                     stored_models[i]["name"],
#                     "- MAIN MODEL" if stored_models[i]["is_main"] else "",
#                     stored_models[i]["num_topics"],
#                     stored_models[i]["description"],
#                     "\n\n\t{}".format(
#                         stored_models[i]["training_context"]
#                     ) if stored_models[i]["training_context"] != "" else "",
#                     stored_models[i]["path"],
#                     stored_models[i]["preprocessor_name"],
#                     stored_models[i]["use_tfidf"]
#                 ), normalize_indentation=False)
#                 )
#             )
#         print("\n\n".join(output_strings))
#     else:
#         print("\n".join([stored_model["name"] for stored_model in stored_models]))
