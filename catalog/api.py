from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Layer
from .serializers import UILayersResponseSerializer, LayerSerializer


class UILayersView(APIView):
    """
    Read-only config endpoint consumed by React/MapLibre.
    Returns only layers whose dataset is published for UI.
    """
    
    @extend_schema(
        responses={200: UILayersResponseSerializer},
        tags=["catalog"],
        summary="Get UI layer configurations",
        description="Returns all published layers with their dataset metadata, tile configurations, and visualization parameters.",
    )
    def get(self, request):
        layers = (
            Layer.objects
            .select_related("dataset")
            .filter(dataset__is_published_for_ui=True)
            .order_by("title")
        )

        out = []
        for lyr in layers:
            ds = lyr.dataset
            out.append({
                "id": lyr.layer_id,
                "title": lyr.title,
                "type": lyr.layer_type,
                "project": ds.get_parent().slug if ds.get_parent() else None,
                "dataset": {
                    "id": ds.dataset_id,
                    "title": ds.title,
                    "cadence": ds.cadence,
                    "dataset_type": ds.dataset_type,
                    "stac_collection": ds.stac_collection_id or ds.dataset_id,
                },
                "tile": {
                    "template": lyr.tile_template,
                    "params": lyr.tile_params or {},
                },
                "ui": {
                    "default_visible": lyr.default_visible,
                    "opacity": lyr.opacity,
                    "minzoom": lyr.minzoom,
                    "maxzoom": lyr.maxzoom,
                },
                "legend": lyr.legend or {},
                "updated_at": lyr.updated_at.isoformat(),
            })

        return Response({"version": "1.0", "layers": out})
