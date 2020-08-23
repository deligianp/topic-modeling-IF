import numpy as np
from thesis_ui.models import LdaModel, Topic, Term, TopicTermDistribution
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.db.utils import DataError
from django.utils.text import slugify
from django.core.management import BaseCommand
from gensim.models import LdaModel as GensimLdaModel
from admin_tasks import models as atmodels
from resources.util import docfetch
import time
import textwrap


class Command(BaseCommand):
    help = "Command for listing existing file groups or updating file groups' extensions and descriptions"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command", help="Use \"[COMMAND] -h\" to display the related help "
                                                                "messages for each command")
        list_subparser = subparsers.add_parser("list")
        list_subparser.add_argument("--detailed", action="store_true",
                                    help="If set, the command will respond with a detailed listing of the file groups "
                                         "and their associated extensions")

        update_subparser = subparsers.add_parser("update")
        update_subparser.add_argument("file_group_name")
        update_subparser.add_argument("--description", help="Descriptive string representing each file group")
        update_subparser.add_argument("-x", "--extensions", nargs="+",
                                      help="Associated extesnsions with a file group. Extensions should be delimited "
                                           "with SPACE, without the leading \".\" used in files' extensions")

    def handle(self, *args, **options):
        action = options["command"]
        try:
            if action == "list":
                list_file_groups(options["detailed"])
            else:
                file_group_name = options["file_group_name"]
                description = options["description"]
                extensions_list = options["extensions"]

                update_file_group(file_group_name, description=description, extensions_list=extensions_list)
        except Exception as ex:
            print(str(ex))


def update_file_group(file_group_name, description=None, extensions_list=None, callback=lambda *args: None):
    callback(0, 100, "Updating file group \"{}\"".format(file_group_name))
    try:
        file_group = atmodels.FileGroup.objects.get(name=file_group_name)
        current_extensions = set([
            ext_obj["fileextension__extension"] for ext_obj in
            atmodels.FileGroup.objects.filter(name=file_group_name).values("fileextension__extension")
        ])
    except atmodels.FileGroup.DoesNotExist as fg_dne:
        raise atmodels.FileGroup.DoesNotExist(
            "No file group exists named \"{}\"".format(file_group_name)
        )
    to_be_deleted = current_extensions - set(extensions_list)
    to_be_created = set(extensions_list) - current_extensions

    with transaction.atomic():
        if description is not None:
            file_group.description = description
            file_group.save()

        with transaction.atomic():
            if len(to_be_deleted) > 0:
                atmodels.FileExtension.objects.filter(extension__in=to_be_deleted,
                                                      file_group__name=file_group_name).delete()

            with transaction.atomic():
                if len(to_be_created) > 0:
                    new_file_extensions = [
                        atmodels.FileExtension(extension=extension, file_group=file_group) for extension in
                        to_be_created
                    ]
                    atmodels.FileExtension.objects.bulk_create(new_file_extensions)
    return file_group_name, description, list(current_extensions.union(to_be_created).difference(to_be_deleted))


def list_file_groups(detailed=False, callback=lambda *args: None):
    callback(0, 100, "Retrieving available file groups")
    if detailed:
        stored_file_groups = atmodels.FileGroup.objects.all().values("name", "description", "fileextension__extension")
        file_groups_output = dict()
        for i in range(len(stored_file_groups)):
            if stored_file_groups[i]["name"] not in file_groups_output:
                file_groups_output[stored_file_groups[i]["name"]] = [
                    stored_file_groups[i]["description"],
                    [stored_file_groups[i]["fileextension__extension"]]
                ]
            else:
                file_groups_output[stored_file_groups[i]["name"]][1].append(
                    stored_file_groups[i]["fileextension__extension"])
        output_strings = [
            "{} - {}\n\n\tExtensions:{}".format(
                file_group_name,
                file_groups_output[file_group_name][0],
                " ".join(
                    "." + extension for extension in file_groups_output[file_group_name][1]
                )
            ) for file_group_name in file_groups_output
        ]
        print("\n\n".join(output_strings))
    else:
        stored_file_groups = atmodels.FileGroup.objects.all().values("name")
        print("\n".join([stored_file_group["name"] for stored_file_group in stored_file_groups]))
    callback(100, 100, "Listed available data processing nodes")
