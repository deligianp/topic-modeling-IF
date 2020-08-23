import numpy as np
from celery.worker.control import revoke

from admin_tasks.celery import app
from thesis_ui.models import Comparison, TopicsComparison, Topic, LdaModel
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.utils.text import slugify
from django.core.management import BaseCommand
from django.core.cache import cache
from gensim.models import LdaModel as GensimLdaModel
from resources.util import docfetch
import time
import textwrap


class Command(BaseCommand):
    help = "Command for cleaning the cache"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        active_task = cache.get("active_admin_task", None)
        if active_task:
            print(active_task["task_id"])
            app.control.revoke(active_task["task_id"], terminate=True)
            cache.set("active_admin_task", None)
