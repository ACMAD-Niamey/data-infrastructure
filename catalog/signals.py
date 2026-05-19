from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from catalog.models import Layer, LayerColorStop


@receiver(post_save, sender=LayerColorStop)
def resync_layer_after_color_stop_save(sender, instance, **kwargs):
    layer = instance.layer
    layer.sync_tile_params_from_stops()


@receiver(post_delete, sender=LayerColorStop)
def resync_layer_after_color_stop_delete(sender, instance, **kwargs):
    instance.layer.sync_tile_params_from_stops()


@receiver(post_save, sender=Layer)
def resync_layer_after_layer_save(sender, instance, **kwargs):
    instance.sync_tile_params_from_stops()
