from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from wagtail.models import Page

from catalog.models import DatasetPage, Layer, ProjectPage
from thredds_ingestion.models import DownloadWorkflow, DownloadWorkflowFile


def _dataset(dataset_id, *, cadence="monthly", multi=True):
    root = Page.get_first_root_node()
    project = root.add_child(instance=ProjectPage(title=f"P-{dataset_id}", slug=f"p-{dataset_id}"))
    ds = DatasetPage(
        title=dataset_id, slug=f"ds-{dataset_id}", dataset_id=dataset_id,
        dataset_type="raster", cadence=cadence, allow_multiple_layers=multi,
    )
    project.add_child(instance=ds)
    return ds


def _layer(ds, layer_id, *, collection=""):
    return Layer.objects.create(
        dataset=ds, title=layer_id, layer_id=layer_id, layer_type="raster",
        has_stac_collection=True, stac_collection_id=collection,
    )


def _run(**kwargs):
    out = StringIO()
    args = []
    for k, v in kwargs.items():
        flag = "--" + k.replace("_", "-")
        if isinstance(v, list):
            for item in v:
                args += [flag, item]
        elif v is True:
            args += [flag]
        else:
            args += [flag, str(v)]
    call_command("seed_obs_rain_anom_workflow", *args, stdout=out)
    return out.getvalue()


class SeedObsRainAnomWorkflowTests(TestCase):
    def setUp(self):
        self.ds = _dataset("pecipitation-tercile-monthly")
        self.l_cpc = _layer(self.ds, "pecipitation-tercile-cpc-uni-monthly", collection="pecipitation-tercile-cpc-uni-monthly")
        self.l_rfe = _layer(self.ds, "pecipitation-tercile-rfe2-monthly", collection="pecipitation-tercile-rfe2-monthly")

    def test_creates_workflow_and_one_file_per_layer(self):
        _run(
            dataset_id="pecipitation-tercile-monthly", variable="Tercile",
            layer=["CPC-UNI=pecipitation-tercile-cpc-uni-monthly", "RFE2=pecipitation-tercile-rfe2-monthly"],
            primary="CPC-UNI",
        )
        wf = DownloadWorkflow.objects.get(name="ACMAD OBS_RAIN_ANOM tercile monthly")
        self.assertEqual(wf.folder_pattern, "{month_abbr}/tif")
        self.assertEqual(wf.cadence, DownloadWorkflow.Cadence.MONTHLY)
        self.assertTrue(wf.source_base_url.endswith("/OBS_RAIN_ANOM/monthly"))

        files = {f.layer.layer_id: f for f in wf.files.all()}
        self.assertEqual(set(files), {
            "pecipitation-tercile-cpc-uni-monthly", "pecipitation-tercile-rfe2-monthly",
        })
        self.assertEqual(
            files["pecipitation-tercile-rfe2-monthly"].filename_pattern,
            "AFR_{month_abbr}_{run_date:%Y}_RFE2_Tercile.tif",
        )
        self.assertEqual(
            files["pecipitation-tercile-cpc-uni-monthly"].resolve_collection(),
            "pecipitation-tercile-cpc-uni-monthly",
        )

    def test_is_idempotent(self):
        args = dict(
            dataset_id="pecipitation-tercile-monthly", variable="Tercile",
            layer=["CPC-UNI=pecipitation-tercile-cpc-uni-monthly"],
        )
        _run(**args)
        _run(**args)
        self.assertEqual(DownloadWorkflow.objects.count(), 1)
        self.assertEqual(DownloadWorkflowFile.objects.count(), 1)

    def test_dry_run_writes_nothing(self):
        out = _run(
            dataset_id="pecipitation-tercile-monthly", variable="Tercile",
            layer=["CPC-UNI=pecipitation-tercile-cpc-uni-monthly"], dry_run=True,
        )
        self.assertIn("dry-run", out)
        self.assertEqual(DownloadWorkflow.objects.count(), 0)

    def test_errors_on_missing_dataset(self):
        with self.assertRaises(CommandError):
            _run(dataset_id="nope", variable="Tercile", layer=["RFE2=x"])

    def test_errors_on_missing_layer(self):
        with self.assertRaises(CommandError):
            _run(
                dataset_id="pecipitation-tercile-monthly", variable="Tercile",
                layer=["CAMSO-PI=does-not-exist"],
            )

    def test_errors_when_layer_belongs_to_another_dataset(self):
        other = _dataset("other-monthly")
        _layer(other, "other-layer")
        with self.assertRaises(CommandError):
            _run(
                dataset_id="pecipitation-tercile-monthly", variable="Tercile",
                layer=["RFE2=other-layer"],
            )

    def test_errors_when_multiple_layers_but_dataset_disallows(self):
        single = _dataset("single-monthly", multi=False)
        _layer(single, "single-monthly")
        with self.assertRaises(CommandError):
            _run(
                dataset_id="single-monthly", variable="Tercile",
                layer=["RFE2=single-monthly", "CPC-UNI=x"],
            )

    def test_rejects_unknown_variable(self):
        with self.assertRaises(CommandError):
            _run(
                dataset_id="pecipitation-tercile-monthly", variable="Bogus",
                layer=["RFE2=pecipitation-tercile-rfe2-monthly"],
            )

    def test_seasonal_uses_literal_season_folder_and_anchor_month(self):
        jja = _dataset("pecipitation-tercile-jja", cadence="seasonal")
        _layer(jja, "pecipitation-tercile-jja-cpc-uni")
        _run(
            dataset_id="pecipitation-tercile-jja", variable="Tercile",
            period="seasonal", season="JJA", anchor_month=6,
            layer=["CPC-UNI=pecipitation-tercile-jja-cpc-uni"],
        )
        wf = DownloadWorkflow.objects.get(name="ACMAD OBS_RAIN_ANOM tercile jja")
        self.assertEqual(wf.folder_pattern, "JJA/tif")
        self.assertEqual(wf.cadence, DownloadWorkflow.Cadence.SEASONAL)
        self.assertEqual(wf.anchor_month, 6)
        self.assertEqual(
            wf.files.get().filename_pattern, "AFR_JJA_{run_date:%Y}_CPC-UNI_Tercile.tif"
        )
