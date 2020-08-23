import numpy as np
from thesis_ui.models import LdaModel, Topic, Term, TopicTermDistribution
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.utils.text import slugify
from django.core.management import BaseCommand
from gensim.models import LdaModel as GensimLdaModel
from resources.util import docfetch
import time
import textwrap


class Command(BaseCommand):
    help = "Command for registering, listing, updating and deleting LDA models that are implemented by gensim"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command", help="Use \"[COMMAND] -h\" to display the related help "
                                                                "messages for each command")

        create_subparser = subparsers.add_parser("create")
        create_subparser.add_argument(
            "name", help="Name of the LdaModel. Must be unique across all models stored inside the database. Use "
                         "list command to get the names of the stored models\n\n"
                         "The name is limited to 30 characters and is pruned to that size if the provided name string "
                         "violates that limit.",
            type=lambda x: x[:30]
        )
        create_subparser.add_argument("model_file_path",
                                      help="Path to LdaModel path. This argument is required when creating a new "
                                           "LdaModel")
        create_subparser.add_argument(
            "-d", "--description", help="Description is used to represent the model throughout the "
                                        "interface in a more readable way than its name. \n\n If omitted on creation, "
                                        "the preformatted form of the given name is used.\n\nThe "
                                        "description is limited to 50 characters and is pruned to that size if the "
                                        "given description string violates that limit",
            type=lambda x: x[:50]
        )
        create_subparser.add_argument(
            "-t", "--training-context", help="Training context is used to describe the "
                                             "training configuration that was used for the production of the model. "
                                             "e.g. corpus, preprocessing configuration, etc.\n\n"
                                             "The training context is limited to 200 characters and is pruned to that "
                                             "size if the given training context string violates that limit",
            type=lambda x: x[:200]
        )
        create_subparser.add_argument(
            "--main", action="store_true", help="Switch that sets the model as the main model of the "
                                                "application"
        )
        create_subparser.add_argument("-N", help="The number of top terms that will be stored for the created model. ",
                                      type=int, default=50)
        create_subparser.add_argument("-p", "--preprocessor-name", type=lambda x: x[:64],
                                      help="The preprocessor name as defined inside the resources.preprocessors module")
        create_subparser.add_argument("--bow", help="If set, any new texts will be vectorized using the bag-of-words "
                                                    "vectorization", action="store_true")
        create_subparser.add_argument("--tfidf", action="store_true",
                                      help="If set and the \"--bow\" flag is not used, any new texts will be "
                                           "vectorized using the bag-of-words vectorization")

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
            model_name = options["name"]
            try:
                delete_model(model_name)
            except LdaModel.DoesNotExist as lda_dne:
                print(str(lda_dne))
        elif action == "list":
            list_models(options["detailed"])
        elif action == "create":
            new_model_name = options["name"]
            model_path = options["model_file_path"]
            description = options["description"]
            training_context = options["training_context"]
            is_main = options["main"]
            topn = options["N"]
            preprocessor_name = options["preprocessor_name"]
            use_tfidf = not options["bow"] and options["tfidf"]
            try:
                create_model(new_model_name, model_path, description, training_context, main=is_main, topn=topn,
                             preprocessor_name=preprocessor_name, use_tfidf=use_tfidf)
            except FileNotFoundError as fnfe:
                print(str(fnfe))
            except IntegrityError as int_err:
                print(str(int_err))
            except Exception as ex:
                print(str(ex))
        else:
            model_name = options["name"]
            new_model_name = options["new_name"]
            description = options["description"]
            training_context = options["training_context"]
            set_main = options["main"]
            demote = options["demote"]
            try:
                update_model(model_name, new_name=new_model_name, description=description,
                             training_context=training_context,
                             set_main=set_main, demote=demote)
            except LdaModel.DoesNotExist as lda_dne:
                print(
                    str(lda_dne) + "\nCouldn't find an LdaModel with name \"{}\".\nUse the list_models command to get "
                                   "a list of the available models.".format(model_name))
            except IntegrityError as int_err:
                print(str(int_err) + "\nMake sure that any new model name given, is unique for all stored models.\nUse "
                                     "the list_models command to get a list of the available models.")
            except Exception as ex:
                print(str(ex))


def create_model(name, path, description, training_context="", main=False, topn=50,
                 preprocessor_name="", use_tfidf=False, callback=lambda *args: None):
    new_name = slugify(name)
    description = description or name
    training_context = training_context or ""
    preprocessor_name = preprocessor_name or "default"

    # Can raise a FileNotFoundError
    callback(0, 100, "Attempting to load model from \"{}\"".format(path))
    model_obj = GensimLdaModel.load(path)
    num_topics = model_obj.num_topics
    dictionary = model_obj.id2word
    topic_terms_matrix = model_obj.get_topics()
    topn_topic_terms_indices = np.flip(np.argsort(topic_terms_matrix), axis=1)[:, :topn]

    total = 2 + num_topics + 2 * num_topics * topn
    completed = 0

    with transaction.atomic():
        new_model = LdaModel(name=new_name, path=path, description=description, training_context=training_context,
                             is_main=main, preprocessor_name=preprocessor_name, use_tfidf=use_tfidf)
        new_model.save()
        completed += 1
        callback(completed, total, "Created model \"{}\"".format(new_name))

        terms = dict()
        for topic_index in range(len(topn_topic_terms_indices)):
            for term_index in topn_topic_terms_indices[topic_index]:
                if term_index not in terms:
                    term = Term.objects.get_or_create(string=dictionary[term_index])[0]
                    terms[term_index] = term

            completed += topn
            callback(completed, total, "Creating model's terms")

        with transaction.atomic():
            topics = {topic_index: Topic(index=topic_index, keyphrase="", parent_model=new_model) for topic_index in
                      range(num_topics)}
            Topic.objects.bulk_create(list(topics.values()))

            completed += num_topics
            round_string = "Created model's terms and topics"
            callback(completed, total, round_string)

            with transaction.atomic():
                topic_term_distributions = list()
                for topic_index in topics:
                    for term_index in topn_topic_terms_indices[topic_index]:
                        topic_term_distributions.append(
                            TopicTermDistribution(topic=topics[topic_index], term=terms[term_index],
                                                  value=topic_terms_matrix[topic_index, term_index]))
                    completed += topn
                    round_string = "Connecting topics to terms"
                    callback(completed, total, round_string)
                TopicTermDistribution.objects.bulk_create(topic_term_distributions)
                Term.objects.filter(topictermdistribution__isnull=True).distinct().delete()
                if main:
                    with transaction.atomic():
                        LdaModel.objects.filter(~Q(name=new_model.name)).update(is_main=False)
    return name, num_topics, path, main


def delete_model(name, callback=lambda *args: None):
    retrieved_model = LdaModel.objects.filter(name=name)
    if retrieved_model.count() == 0:
        raise LdaModel.DoesNotExist("No models were found with name \"{}\"".format(name))
    with transaction.atomic():
        Term.objects.annotate(num_of_models=Count("topictermdistribution__topic__parent_model", distinct=True)).filter(
            num_of_models=1, topictermdistribution__topic__parent_model__name=name).delete()
        retrieved_model.delete()
    return name


def update_model(name, new_name=None, description=None, training_context=None, set_main=False, demote=False,
                 preprocessor_name=None, use_tfidf=False, use_bow=False, callback=lambda *args: None):
    model = LdaModel.objects.get(name=name)

    if new_name is not None:
        model.name = slugify(new_name)

    if description is not None:
        model.description = description

    if training_context is not None:
        model.training_context = training_context

    if set_main or demote:
        model.is_main = set_main

    if preprocessor_name is not None:
        model.preprocessor_name = preprocessor_name

    if use_bow or use_tfidf:
        model.use_tfidf = not use_bow

    with transaction.atomic():
        if set_main:
            LdaModel.objects.filter(~Q(name=name), is_main=True).update(is_main=False)
        model.save()
    return new_name, description, training_context


def list_models(detailed=False):
    stored_models = LdaModel.objects.all().values().annotate(num_topics=Count('model_topics'))
    output_strings = list()
    if detailed:
        for i in range(len(stored_models)):
            output_strings.append(
                "\n".join(docfetch.sanitize_docstring("{}. {}{} with {} topics\n\n\t{}{}\n\n\t- Loaded from "
                                                      "\"{}\"\n\n\t- Preprocessor name: {}\n\n\t- Use tf-idf: "
                                                      "{}".format(
                    i,
                    stored_models[i]["name"],
                    "- MAIN MODEL" if stored_models[i]["is_main"] else "",
                    stored_models[i]["num_topics"],
                    stored_models[i]["description"],
                    "\n\n\t{}".format(
                        stored_models[i]["training_context"]
                    ) if stored_models[i]["training_context"] != "" else "",
                    stored_models[i]["path"],
                    stored_models[i]["preprocessor_name"],
                    stored_models[i]["use_tfidf"]
                ), normalize_indentation=False)
                )
            )
        print("\n\n".join(output_strings))
    else:
        print("\n".join([stored_model["name"] for stored_model in stored_models]))
