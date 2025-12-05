from django.core.management.base import BaseCommand
from alertas.services import generar_alertas

class Command(BaseCommand):
    help = 'Genera alertas automáticas (stock, vencimiento, riesgo)'

    def handle(self, *args, **options):
        generar_alertas()
        self.stdout.write(self.style.SUCCESS('Alertas generadas'))
