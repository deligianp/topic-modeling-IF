import os
import json
from thesis_ui.models import LdaModel, Topic

from django.core.management import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "model_name", help="Name of the LdaModel whose topics will be mapped with the provided keyphrases"
        )
        parser.add_argument(
            "-k", "--keyphrases-file-path", help="Path to the keyphrases JSON file. Leave empty if you want the topic "
                                                 "keyphrases to be reverted to empty"
        )

    def handle(self, *args, **options):
        model_name = options["model_name"]
        keyphrases_file_path = options["keyphrases_file_path"]
        set_keyphrases(model_name, keyphrases_file_path)


def set_keyphrases(model_name, keyphrases_file_path=None):
    model_topics = {
        int(topic_obj.index): topic_obj for topic_obj in Topic.objects.filter(parent_model__name=model_name)
    }
    if len(model_topics) < 1:
        raise ValueError("Model \"{}\" does not exist".format(model_name))

    update_batch = list()

    if keyphrases_file_path:
        with open(keyphrases_file_path, "r", encoding="utf-8") as f_handle:
            keyphrases = json.load(f_handle)
        for topic_keyphrase in keyphrases:
            index = topic_keyphrase["topic"]
            keyphrase = topic_keyphrase["keyphrase"]

            if index in model_topics:
                model_topics[index].keyphrase = keyphrase

                update_batch.append(model_topics[index])
    else:
        for index in model_topics:
            model_topics[index].keyphrase = ""
            update_batch.append(model_topics[index])

    Topic.objects.bulk_update(update_batch)
