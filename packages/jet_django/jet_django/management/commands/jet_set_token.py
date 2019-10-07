from django.core.management import BaseCommand

from jet_bridge_base.commands.set_token import set_token_command


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('token', nargs='?', type=str)

    def handle(self, *args, **options):
        set_token_command(options.get('token'))
