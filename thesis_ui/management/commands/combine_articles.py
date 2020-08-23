from django.core.management.base import BaseCommand
from thesis_ui.models import Article
from django.contrib.postgres.search import SearchVector
from django.db.models import Subquery
from shutil import disk_usage
import os
import json


class Command(BaseCommand):
    help = 'Command that combines information of article abstracts, languages and rest of metadata in one table'

    def handle(self, abstracts_directory, json_directory, languages_file, *args, **kwargs):
        meta_data_dict = dict()
        abstracts_directory=""
        jso
        json_files = os.listdir(json_directory)
        json_lines_passed = 0
        notifying_batch = 10000
        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f_handle:
                for f_line in f_handle:
                    line_dict = json.loads(f_line)
                    meta_data_dict[line_dict["identifier"]] = {
                        "title": line_dict["title"],
                        "authors": line_dict["authors"],
                        "year": line_dict["year"],
                        "language": "",
                        "abstract": ""
                    }
                    if json_lines_passed % notifying_batch == 0:
                        print("{} lines checked".format(json_lines_passed))
                    json_lines_passed+=1
                print("JSON file parsed. {} lines checked".format(json_lines_passed))
        with open(languages_file, "r", encoding="utf-8") as f_handle:
            for f_line in f_handle:
                identifier, language = f_line.split("\t")
                if identifier in meta_data_dict:
                    meta_data_dict[identifier]["language"] = language
