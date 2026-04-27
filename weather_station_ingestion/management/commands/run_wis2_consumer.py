import logging
import signal

from django.core.management.base import BaseCommand

from weather_station_ingestion.services.wis2_consumer import WIS2Consumer

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the WIS2 MQTT consumer"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting WIS2 consumer..."))
        consumer = WIS2Consumer()

        def _shutdown(signum, frame):
            sig_name = signal.Signals(signum).name
            log.info("Received %s — disconnecting from broker…", sig_name)
            consumer.client.disconnect()
            consumer.client.loop_stop()

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

        consumer.connect()
        consumer.loop_forever()
        self.stdout.write(self.style.SUCCESS("WIS2 consumer stopped."))

