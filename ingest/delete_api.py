"""DELETE endpoints for STAC catalog items (optional MinIO purge)."""

from __future__ import annotations

from catalog.models import DatasetPage
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import _json_safe, validate_payload_for_cadence, KEY_OR_TOKEN_AUTH
from .models import DeletionRun
from .permissions import HasAPIKey
from .serializers import DeleteByDatetimeSerializer, DeleteResponseSerializer
from .stac_ops import resolve_item_ids_for_delete
from .tasks import process_deletion_run


def _delete_object_from_request(request) -> bool:
    raw = request.query_params.get("delete_object", "false")
    return str(raw).lower() in ("1", "true", "yes")


def _get_dataset(dataset_id: str):
    return DatasetPage.objects.filter(dataset_id=dataset_id).first()


def _enqueue_deletion(dataset, item_id: str, payload: dict, delete_object: bool) -> DeletionRun:
    run_payload = {**payload, "item_id": item_id}
    run = DeletionRun.objects.create(
        dataset_id=dataset.dataset_id,
        cadence=dataset.cadence,
        status="accepted",
        payload=run_payload,
        delete_object=delete_object,
    )
    process_deletion_run.delay(run.id)
    return run


_DELETE_OBJECT_PARAM = OpenApiParameter(
    name="delete_object",
    type=bool,
    location=OpenApiParameter.QUERY,
    required=False,
    description=(
        "If true, delete the MinIO object referenced by assets.data.href after reading the STAC item. "
        "If false (default), remove only the STAC catalog entry."
    ),
)


class DeleteDatasetItemView(APIView):
    """Delete a single STAC item by id (optional MinIO purge)."""

    authentication_classes = KEY_OR_TOKEN_AUTH
    permission_classes = [HasAPIKey]

    @extend_schema(
        responses={202: DeleteResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="dataset_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="STAC collection / dataset id",
            ),
            OpenApiParameter(
                name="item_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="STAC item id",
            ),
            _DELETE_OBJECT_PARAM,
        ],
        tags=["ingest"],
        description="""
        Delete one STAC item by **item_id**.

        - **Catalog only** (default): `DELETE .../items/{item_id}`
        - **STAC + MinIO file**: `DELETE .../items/{item_id}?delete_object=true`

        Returns 202 with a deletion run id (processed asynchronously by Celery).
        """,
    )
    def delete(self, request, dataset_id: str, item_id: str):
        dataset = _get_dataset(dataset_id)
        if not dataset:
            return Response(
                {"detail": f"Unknown dataset_id '{dataset_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        delete_object = _delete_object_from_request(request)
        run = _enqueue_deletion(dataset, item_id, {}, delete_object)
        return Response(
            {
                "run_id": run.id,
                "status": run.status,
                "item_id": item_id,
                "delete_object": delete_object,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DeleteDatasetItemByDatetimeView(APIView):
    """Delete a STAC item identified by datetime (optional MinIO purge)."""

    authentication_classes = KEY_OR_TOKEN_AUTH
    permission_classes = [HasAPIKey]

    @extend_schema(
        request=DeleteByDatetimeSerializer,
        responses={202: DeleteResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="dataset_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="STAC collection / dataset id",
            ),
            _DELETE_OBJECT_PARAM,
        ],
        tags=["ingest"],
        description="""
        Delete a STAC item by **datetime** (and dataset cadence), or by optional **item_id** in the body.

        Uses the same temporal fields as ingest. The service searches STAC for items in the
        resolved interval; exactly one item must match (otherwise 404 or 409).

        - **Catalog only**: omit `delete_object` or `delete_object=false`
        - **STAC + MinIO**: `?delete_object=true`
        """,
    )
    def delete(self, request, dataset_id: str):
        dataset = _get_dataset(dataset_id)
        if not dataset:
            return Response(
                {"detail": f"Unknown dataset_id '{dataset_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DeleteByDatetimeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = _json_safe(serializer.validated_data)

        if not payload.get("item_id"):
            err = validate_payload_for_cadence(dataset.cadence, payload)
            if err:
                return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        try:
            item_ids = resolve_item_ids_for_delete(dataset.dataset_id, dataset.cadence, payload)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"STAC lookup failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not item_ids:
            return Response(
                {"detail": "No STAC item found for the given temporal criteria"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if len(item_ids) > 1:
            return Response(
                {
                    "detail": "Multiple STAC items match; delete by explicit item_id instead",
                    "item_ids": item_ids,
                },
                status=status.HTTP_409_CONFLICT,
            )

        item_id = item_ids[0]
        delete_object = _delete_object_from_request(request)
        run = _enqueue_deletion(dataset, item_id, payload, delete_object)
        return Response(
            {
                "run_id": run.id,
                "status": run.status,
                "item_id": item_id,
                "delete_object": delete_object,
            },
            status=status.HTTP_202_ACCEPTED,
        )
