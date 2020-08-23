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
    help = "Command for registering, listing, updating and deleting data processing nodes"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command", help="Use \"[COMMAND] -h\" to display the related help "
                                                                "messages for each command")

        create_subparser = subparsers.add_parser("register")
        create_subparser.add_argument(
            "host_ipv4", help="IPv4 of the host node where resource files can be found.")
        create_subparser.add_argument("username",
                                      help="Name of user account which will be used to retrieve files from the host")
        create_subparser.add_argument("withdrawal_directory_path", help="Path to the directory, on the host node, "
                                                                        "where the resource files are located")

        list_subparser = subparsers.add_parser("list")
        list_subparser.add_argument("--detailed", action="store_true",
                                    help="If set, the command will respond with a detailed listing of the data "
                                         "processing nodes")

        delete_subparser = subparsers.add_parser("delete")
        delete_subparser.add_argument("host_ipv4", help="Registered host's IPv4 address")

        update_subparser = subparsers.add_parser("update")
        update_subparser.add_argument("host_ipv4")
        update_subparser.add_argument("--new-host-ipv4", help="Host's new IPv4 address")
        update_subparser.add_argument("-u", "--username", help="New user name that will be used to connect to the host "
                                                               "node")
        update_subparser.add_argument("-d", "--directory",
                                      help="New withdrawal directory where resource files are located")

    def handle(self, *args, **options):
        action = options["command"]
        try:
            if action == "delete":
                host_ipv4 = options["host_ipv4"]
                delete_data_processing_node(host_ipv4)
            elif action == "list":
                list_data_processing_nodes(options["detailed"])
            elif action == "register":
                host_ipv4 = options["host_ipv4"]
                username = options["username"]
                withdrawal_directory = options["withdrawal_directory_path"]
                register_data_processing_node(host_ipv4, username, withdrawal_directory)
            else:
                host_ipv4 = options["host_ipv4"]
                new_host_ipv4 = options["new_host_ipv4"]
                username = options["username"]
                withdrawal_directory = options["directory"]
                update_data_processing_node(host_ipv4, new_host_ipv4=new_host_ipv4, username=username,
                                            withdrawal_directory=withdrawal_directory)
        except Exception as ex:
            print(str(ex))


def register_data_processing_node(host_ipv4, username, withdrawal_directory, callback=lambda *args: None):
    callback(0, 100, "Registering new data processing node")
    dpn = atmodels.DataProcessingNode(host=host_ipv4, username=username, withdrawal_directory=withdrawal_directory)
    try:
        dpn.save()
    except IntegrityError as int_er:
        raise IntegrityError(
            "Host IPv4 address \"{}\" is already defined for another data processing node object".format(host_ipv4)
        )
    except DataError as dpn_de:
        raise DataError(
            "Invalid host IPv4 address was given: {}".format(host_ipv4)
        )
    callback(100, 100, "Registered new data processing node with on host IPv4 address \"{}\"".format(host_ipv4))
    return host_ipv4, username, withdrawal_directory


def delete_data_processing_node(host_ipv4, callback=lambda *args: None):
    callback(0, 100, "Deleting target data processing node on host IPv4 address \"{}\"".format(host_ipv4))
    try:
        dpn = atmodels.DataProcessingNode.objects.get(host=host_ipv4)
        dpn.delete()
    except atmodels.DataProcessingNode.DoesNotExist as dpn_dne:
        raise atmodels.DataProcessingNode.DoesNotExist(
            "No data processing node exists with a host IPv4 address \"{}\"".format(host_ipv4)
        )
    except DataError as dpn_de:
        raise DataError(
            "Invalid host IPv4 address was given: {}".format(host_ipv4)
        )
    callback(100, 100, "Deleted target data processing node on host IPv4 address \"{}\"".format(host_ipv4))
    return host_ipv4


def update_data_processing_node(host_ipv4, new_host_ipv4=None, username=None, withdrawal_directory=None,
                                callback=lambda *args: None):
    callback(0, 100, "Updating target data processing node on host IPv4 address \"{}\"".format(host_ipv4))
    try:
        dpn = atmodels.DataProcessingNode.objects.get(host=host_ipv4)
    except DataError as dpn_de:
        raise DataError(
            "Invalid host IPv4 address was given: {}".format(host_ipv4)
        )
    except atmodels.DataProcessingNode.DoesNotExist as dpn_dne:
        raise atmodels.DataProcessingNode.DoesNotExist(
            "No data processing node exists with a host IPv4 address \"{}\"".format(host_ipv4)
        )

    if new_host_ipv4 is not None:
        dpn.host = new_host_ipv4

    if username is not None:
        dpn.username = username

    if withdrawal_directory is not None:
        dpn.withdrawal_directory = withdrawal_directory

    try:
        dpn.save()
    except DataError as dpn_de:
        raise DataError(
            "Invalid host IPv4 address was given: {}".format(new_host_ipv4)
        )
    except IntegrityError as dpn_ie:
        raise IntegrityError(
            "Host IPv4 address \"{}\" is already defined for another data processing node object".format(new_host_ipv4)
        )
    callback(100, 100, "Updated target data processing node on host IPv4 address \"{}\"".format(dpn.host))

    return new_host_ipv4, username, withdrawal_directory


def list_data_processing_nodes(detailed=False, callback=lambda *args: None):
    callback(0, 100, "Retrieving available data processing nodes")
    stored_dpns = atmodels.DataProcessingNode.objects.all().values()
    output_strings = list()
    if detailed:
        for i in range(len(stored_dpns)):
            output_strings.append(
                "\n".join(docfetch.sanitize_docstring("{}@{}\n\n\tDirectory: {}".format(
                    stored_dpns[i]["username"],
                    stored_dpns[i]["host"],
                    stored_dpns[i]["withdrawal_directory"]
                ), normalize_indentation=False))
            )
        print("\n\n".join(output_strings))
    else:
        print("\n".join([stored_dpn["host"] for stored_dpn in stored_dpns]))
    callback(100, 100, "Listed available data processing nodes")
