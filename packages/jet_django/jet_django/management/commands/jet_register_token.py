from django.core.management import BaseCommand

from jet_bridge_base.commands.register_token import register_token_command


class Command(BaseCommand):
    def handle(self, *args, **options):
        register_token_command()
