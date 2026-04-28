from __future__ import annotations

import ssl

import paho.mqtt.client as mqtt
from django.conf import settings


class MQTTClientFactory:
    def build(self, on_connect, on_message, on_disconnect) -> mqtt.Client:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.username_pw_set(
            settings.WIS2_BROKER_USERNAME,
            settings.WIS2_BROKER_PASSWORD,
        )
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        return client