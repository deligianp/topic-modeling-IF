import numpy as np
from thesis_ui.models import Comparison, TopicsComparison, Topic, LdaModel
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.utils.text import slugify
from django.core.management import BaseCommand
from gensim.models import LdaModel as GensimLdaModel
from resources.util import docfetch
import time
import textwrap


class Command(BaseCommand):
    help = "Command for adding, listing, updating and deleting LDA models' comparisons"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command", help="Use \"[COMMAND] -h\" to display the related help "
                                                                "messages for each command")

        create_subparser = subparsers.add_parser("add")
        create_subparser.add_argument("comparison_file_path",
                                      help="Path to comparison fle")
        create_subparser.add_argument(
            "name", help="Name of the comparison to be registered. Must be unique across all models stored inside the "
                         "database. Use list command to get the names of the stored models\n\n"
                         "The name is limited to 30 characters and is pruned to that size if the provided name string "
                         "violates that limit.",
            type=lambda x: x[:30]
        )
        create_subparser.add_argument("minimum_value",
                                      help="Minimum value that can be observed by the metric used in the comparison",
                                      type=float)
        create_subparser.add_argument("maximum_value",
                                      help="Maximum value that can be observed by the metric used in the comparison",
                                      type=float)
        create_subparser.add_argument("type_of_comparison",
                                      help="The type of comparison: a 'score' comparison indicates that higher metric "
                                           "values correspond to greater similarity, a 'distance' comparison indicates "
                                           "that higher metric values correspond lower similarity "
                                           "(higher distance/divergence)",
                                      choices=("score", "distance"),
                                      type=str.lower)
        create_subparser.add_argument("model_0_name",
                                      help="The unique name of the existing model that takes part on the comparison as "
                                           "the first model")
        create_subparser.add_argument("model_1_name",
                                      help="The unique name of the existing model that takes part on the comparison as "
                                           "the second model")
        create_subparser.add_argument(
            "-d", "--description", help="Description is used to represent the comparison throughout the "
                                        "interface in a more readable way than its name. \n\n If omitted on addition, "
                                        "the preformatted form of the given name is used.\n\nThe "
                                        "description is limited to 50 characters and is pruned to that size if the "
                                        "given description string violates that limit",
            type=lambda x: x[:50]
        )

        list_subparser = subparsers.add_parser("list")
        list_subparser.add_argument("--detailed", action="store_true",
                                    help="If set, the command will respond with a detailed listing of the stored "
                                         "comparisons")

        delete_subparser = subparsers.add_parser("delete")
        delete_subparser.add_argument("name", help="Name of the comparison")

        update_subparser = subparsers.add_parser("update")
        update_subparser.add_argument("name", help="Current name of the comparison")
        update_subparser.add_argument("-n", "--new-name", type=lambda x: slugify(x[:30]),
                                      help="The new name of the comparison")
        update_subparser.add_argument("-d", "--description", type=lambda x: x[:50],
                                      help="The new description of the comparison")
        update_subparser.add_argument("--min", type=float,
                                      help="The new minimum value that can be observed by the comparison's metric")
        update_subparser.add_argument("--max", type=float,
                                      help="The new maximum value that can be observed by the comparison's metric")

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
        elif action == "add":
            comparison_name = options["name"]
            comparison_file_path = options["comparison_file_path"]
            minimum_value = options["minimum_value"]
            maximum_value = options["maximum_value"]
            score_comparison = options["type_of_comparison"] == "score"
            model_0_name = options["model_0_name"]
            model_1_name = options["model_1_name"]
            description = options["description"]
            try:
                add_comparison(new_model_name, model_path, description, training_context, main=is_main, topn=topn,
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


def add_comparison(name, path, description, minimum_value, maximum_value, model_0_name, model_1_name, is_score,
                   callback=lambda *args: None):
    comparison_name = slugify(name)
    description = description or name

    # Can raise a FileNotFoundError
    with transaction.atomic():
        callback(0, 100, "Creating comparison object with name \"{}\"".format(comparison_name))
        comparison_object = Comparison(
            name=comparison_name,
            description=description,
            type_of_comparison=0 if is_score else 1,
            lower_bound=minimum_value,
            upper_bound=maximum_value,
            lda_model_0=LdaModel.objects.get(name=model_0_name),
            lda_model_1=LdaModel.objects.get(name=model_1_name)
        )
        callback(1, 100, "Retrieving topics for each model")
        model_0_topics = {
            topic.index: topic for topic in Topic.objects.filter(parent_model__name=model_0_name)
        }
        model_1_topics = {
            topic.index: topic for topic in Topic.objects.filter(parent_model__name=model_1_name)
        }

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
