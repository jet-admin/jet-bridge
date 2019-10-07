from django.core.management import BaseCommand

from jet_bridge_base.commands.reset_token import reset_token_command


class Command(BaseCommand):
    def handle(self, *args, **options):
        reset_token_command()
