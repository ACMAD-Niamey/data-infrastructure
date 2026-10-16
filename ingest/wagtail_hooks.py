from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .forms import StationTimeseriesUploadForm
from .station_timeseries.uploads import queue_station_timeseries_run


def station_timeseries_upload(request):
    """CMS entry point: pick a station time-series dataset page and upload its CSVs."""
    form = StationTimeseriesUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        run = queue_station_timeseries_run(
            form.cleaned_data["dataset"],
            form.cleaned_data["files"],
            group=form.cleaned_data["group"],
            commune=form.cleaned_data["commune"],
        )
        messages.success(
            request,
            f"Ingestion run #{run.id} queued for {len(form.cleaned_data['files'])} file(s). "
            "Check Ingestion runs for the per-file result.",
        )
        return redirect("station_timeseries_upload")
    return render(request, "ingest/station_upload.html", {"form": form})


@hooks.register("register_admin_urls")
def register_station_upload_url():
    return [
        path("station-timeseries-upload/", station_timeseries_upload, name="station_timeseries_upload"),
    ]


@hooks.register("register_admin_menu_item")
def register_station_upload_menu_item():
    return MenuItem(
        "Station data upload",
        reverse("station_timeseries_upload"),
        icon_name="upload",
        order=900,
    )
