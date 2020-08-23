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

from django.core.management.base import BaseCommand
from django.db import connection
from thesis_ui import models
from django.db.utils import IntegrityError
import resources
import os
import hashlib
import psycopg2


class Command(BaseCommand):
    help = 'Command that erases all data from the registered database relations'
    main_relations = ("thesis_ui_document", "thesis_ui_errorcode")

    def handle(self, *args, **kwargs):
        valid_entry = False
        while not valid_entry:
            entry = input(
                "You are about to erase all data from the relations\n\"{}\"\nand their related relations. Are you sure "
                "you want to continue? (y/N): ".format("\",\n\"".join(self.main_relations)))
            if entry.lower() == "n":
                return
            elif entry.lower() != "y":
                continue
            else:
                valid_entry = True
        query = ""
        for relation in self.main_relations:
            query += "TRUNCATE TABLE {} CASCADE;".format(relation)
        cursor = connection.cursor()
        cursor.execute(query)
        cursor.close()
        print("\nRelations \n\"{}\"\nhave been truncated.".format("\",\n\"".join(self.main_relations)))
