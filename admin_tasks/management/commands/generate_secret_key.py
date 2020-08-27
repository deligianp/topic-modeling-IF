from django.core.management.utils import get_random_secret_key
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Command for generating a string that can be used as a secret key for the application"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        print(get_random_secret_key())
