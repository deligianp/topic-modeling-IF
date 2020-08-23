from django.core.management.base import BaseCommand
from thesis_ui.models import Article
from django.contrib.postgres.search import SearchVector
from django.db.models import Subquery
from shutil import disk_usage


class Command(BaseCommand):
    help = 'Command that schedules the indexing of loaded DB documents'

    def handle(self, *args, **kwargs):
        batch_size = 10000
        total_indexed = 0
        while True:
            non_indexed_documents = Article.objects.filter(
                pk__in=Subquery(Article.objects.filter(search_vector=None).values("pk")[:batch_size])).update(
                search_vector=SearchVector('title', weight='A') + SearchVector('abstract', weight='B'))
            if non_indexed_documents == 0:
                break
            else:
                total_indexed += non_indexed_documents
                print("\rUpdated {} documents. Free disk size remaining: {} GB".format(total_indexed,
                                                                                       (disk_usage("/")[2]) / 2 ** 30),
                      end="")
        print("Job finished!")
        return
