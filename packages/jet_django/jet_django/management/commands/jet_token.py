from django.core.management import BaseCommand

from jet_bridge_base.commands.token import token_command


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('token', nargs='?', type=str)

    def handle(self, *args, **options):
        token_command()
