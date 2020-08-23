# import argparse
# import os
# from thesis_ui import models
#
#
# def check_path(path):
#     if os.path.exists(path):
#         pass
#
#
# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(
#         description='This script is being run by the db maintainer to reset and refill the database with the corpus data.')

#     parsed_args = parser.parse_args()
#     corpus_path = parsed_args.corpus_path
#     corpus_false_documents_path = parsed_args.corpus_false_document_path
#     print(corpus_path)
#     print(corpus_false_documents_path)
#     paper = models.Paper(paper_identifier='a0b1c2')
#     paper.save()
import csv

from django.core.management.base import BaseCommand
from django.db import connection
from thesis_ui import models
from django.db.utils import IntegrityError
import resources
import importlib
import os
import hashlib

from thesis_ui.models import Document


class Command(BaseCommand):
    help = 'Command that loads data from CSV files to the database'
    registered_relations = {"document":
                                ("thesis_ui_document",
                                 ("document_identifier", "abstract")),
                            "errorcode":
                                ("thesis_ui_errorcode",
                                 ("error_description",))
                            }

    def get_registered_relation(self, given_alias):
        if given_alias in self.registered_relations:
            return self.registered_relations[given_alias]
        else:
            return given_alias

    def add_arguments(self, parser):
        parser.add_argument("path", help="Alias of the model")
        # parser.add_argument("csv_paths",
        #                     help="Paths to CSV files or parent directories of CSV files of documents to be "
        #                          "loaded on the database", nargs="+")
        # parser.add_argument("-r", "--recursive",
        #                     help="Recursively discover CSV files in subdirectories of given directories",
        #                     action="store_true")
        # parser.add_argument("-d", "--delimiter", help="Delimiter of target CSV files. Default: ','", default=",")

    def discover_files(self, target_path, file_extension, recursion_level):
        if os.path.exists(target_path):
            target_path = os.path.abspath(target_path)
            if os.path.isfile(target_path):
                if target_path.endswith("." + file_extension):
                    if os.access(target_path, os.R_OK):
                        return [target_path]
                    else:
                        return -1
                else:
                    return -2
            elif os.path.isdir(target_path):
                if os.access(target_path, os.R_OK) and os.access(target_path, os.X_OK):
                    accepted_files = list()
                    directory_files = os.listdir(target_path)
                    for file in directory_files:
                        if os.path.isfile(os.path.join(target_path, file)):
                            parse_res = self.discover_files(os.path.join(target_path, file), file_extension,
                                                            recursion_level)
                            if type(parse_res) is not int:
                                accepted_files.extend(parse_res)
                        elif os.path.isdir(os.path.join(target_path, file)):
                            if recursion_level != 0:
                                parse_res = self.discover_files(os.path.join(target_path, file), file_extension,
                                                                recursion_level=recursion_level - 1)
                                if type(parse_res) is not int:
                                    accepted_files.extend(parse_res)
                        else:
                            return -3
                    return accepted_files
                else:
                    return -1
            else:
                return -3
        else:
            return -4

    def handle(self, *args, **kwargs):
        path = kwargs["path"]
        module = importlib.import_module(path)
        module.execute()

        # model_information = kwargs["model_alias"]
        # if type(model_information) is not tuple:
        #     print("Invalid model alias \"{}\".\nValid model aliases: \"{}\"".format(model_information, "\", \"".join(
        #         self.registered_relations.keys())))
        #     return
        # delimiter = kwargs["delimiter"]
        # if kwargs["recursive"]:
        #     recursion_level = -1
        # else:
        #     recursion_level = 0
        # target_files = list()
        # for csv_path in csv_paths:
        #     parse_res = self.discover_files(csv_path, "csv", recursion_level)
        #     if type(parse_res) is int:
        #         if parse_res == -1:
        #             print("WARNING: Not enough permissions for \"{}\"".format(os.path.abspath(csv_path)))
        #         elif parse_res == -2:
        #             print("WARNING: \"{}\" is not a valid CSV file".format(os.path.abspath(csv_path)))
        #         elif parse_res == -3:
        #             print("WARNING: \"{}\" points to neither a directory nor a file".format(os.path.abspath(csv_path)))
        #         else:
        #             print("WARNING: \"{}\" does not exist".format(csv_path))
        #     else:
        #         if len(parse_res) == 0:
        #             print("WARNING: No suitable files found in \"{}\"".format(os.path.abspath(csv_path)))
        #         else:
        #             for discovered_csv_file in parse_res:
        #                 if discovered_csv_file not in target_files:
        #                     target_files.append(discovered_csv_file)
        # if len(target_files) == 0:
        #     print("ERROR: No CSV files were found in the given directories")
        # else:
        #     for csv_file in target_files:
        #         with open(csv_file, "r", encoding="utf-8") as csv_file_handle:
        #             csv_file_handle.close()
