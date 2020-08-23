import bz2
import pickle
from django.core.management.base import BaseCommand
from thesis_ui.models import Article, Topic, ArticleTopicDistribution, ReportedError
from shutil import disk_usage
from resources import lda_query
from resources import configuration as config


class Command(BaseCommand):
    help = 'Command that for each document gets the top 3 topics based on the currently active LDA model'

    def add_arguments(self, parser):
        parser.add_argument("-i", "--input", help="Path to one or more files that contain mappings of article "
                                                  "identifiers to "
                                                  "their article topics. The file is a pickled binary file, compressed "
                                                  "with the bz2 module. The loaded object should be a dictionary "
                                                  "mapping article identifiers to N topic distributions, contained in "
                                                  "a list. Each topic distribution should be a tuple of 2 items: the "
                                                  "topic index in position 0 and topic distibution value in position 1",
                            nargs="+", required=True)
        parser.add_argument("-e", "--errors", help="Path to one or more files that contain reported errors for "
                                                   "articles. These files should be text CSV files, with a header in "
                                                   "the first in line. There should be 2 columns: the first containing "
                                                   "the article identifier and the second the reported error string",
                            nargs="+")

    def handle(self, *args, **kwargs):
        input_files = kwargs["input"]
        print("Storing reported errors")

        # Map all articles based on their identifier, that do not currently have a topic distribution or a reported
        # error
        # all_article_identifiers_map = {article.identifier: article for article in
        #                                Article.objects.filter(articletopicdistribution__isnull=True,
        #                                                       reportederror__isnull=True).distinct()}

        # Map all topics based on their indexes, that are contained in the main LDA model
        # all_topics_map = {
        #     topic.index: topic for topic in Topic.objects.filter(
        #         parent_model__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"]
        #     ).distinct()
        # }

        rows_processed = 0
        commit_batch_size = 10000
        commit_batch = list()
        for filepath in input_files:
            with bz2.BZ2File(filepath, "rb") as bf_handle:
                upickler = pickle.Unpickler(bf_handle)
                print("File \"{}\"".format(filepath))
                print("")

                reached_eof = False
                while not reached_eof:
                    try:
                        article_topic = upickler.load()
                    except EOFError:
                        reached_eof = True
                        continue
                    try:
                        try:
                            article_object_reference = Article.objects.get(
                                identifier=article_topic[0],
                                articletopicdistribution__isnull=True,
                                reportederror__isnull=True
                            )
                        except Article.DoesNotExist:
                            continue
                        try:
                            topic_object_reference = Topic.objects.get(
                                index=article_topic[1],
                                parent_model__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"]
                            )
                        except Topic.DoesNotExist:
                            continue
                        commit_batch.append(
                            ArticleTopicDistribution(
                                article=article_object_reference,
                                topic=topic_object_reference,
                                value=article_topic[2]
                            )
                        )
                        rows_processed += 1

                        if rows_processed % commit_batch_size == 0:
                            print("Storing batch...")
                            ArticleTopicDistribution.objects.bulk_create(commit_batch)
                            commit_batch = list()
                            print("\t- Stored {} objects".format(rows_processed))
                    except Exception as ex:
                        pass
                        # print(ex)
                        # exit()
                if len(commit_batch) > 0:
                    print(
                        "File \"{}\" closing but {} rows are pending to be stored".format(filepath,
                                                                                          len(commit_batch))
                    )
                    ArticleTopicDistribution.objects.bulk_create(commit_batch)
                    commit_batch = list()
                    print("\t- Stored {} objects".format(rows_processed))
                bf_handle.close()
        if "errors" in kwargs and kwargs["errors"] is not None:
            print("Storing errors")
            import pandas as pd
            error_files = kwargs["errors"]

            errors = list()
            rows_processed = 0
            commit_batch_size = 10000
            # all_article_identifiers_map = {article.identifier: article for article in
            #                                Article.objects.filter(articletopicdistribution__isnull=True,
            #                                                       reportederror__isnull=True).distinct()}

            for error_file in error_files:
                reported_errors = pd.read_csv(error_file, encoding="utf-8", iterator=True, chunksize=1)
                print("File \"{}\"".format(error_file))
                print("")
                for reported_error in reported_errors:
                    article_identifier = reported_error.iloc[0]["ARTICLE_ID"]
                    try:
                        article_object_reference = Article.objects.get(
                            identifier=article_identifier,
                            articletopicdistribution__isnull=True,
                            reportederror__isnull=True
                        )
                    except Article.DoesNotExist:
                        continue
                    error_description = reported_error.iloc[0]["ERROR_DESCRIPTION"]
                    errors.append(ReportedError(
                        article=article_object_reference,
                        error_description=error_description
                    ))
                    rows_processed += 1
                    if rows_processed % commit_batch_size == 0:
                        print("Storing batch")
                        ReportedError.objects.bulk_create(errors)
                        print("\t- Stored {} reported errors".format(rows_processed))
                        errors = list()
                if len(errors) > 0:
                    print("File closing but {} rows are pending to be stored".format(len(errors)))
                    ReportedError.objects.bulk_create(errors)
                    errors = list()
                    print("\t- Stored {} objects".format(rows_processed))
