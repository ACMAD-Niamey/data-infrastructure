from django import forms

from catalog.models import DatasetPage


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Django's FileField takes one file; field loggers produce one CSV per sensor."""

    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)]


class StationTimeseriesUploadForm(forms.Form):
    dataset = forms.ModelChoiceField(
        queryset=DatasetPage.objects.none(),
        help_text="Only station time-series datasets are listed; the dataset's page decides which project it belongs to.",
    )
    files = MultipleFileField(
        help_text="Logger CSV files named like 'Capteur 002 Soleil.CSV' (the sensor number is the station id).",
    )
    group = forms.CharField(required=False, help_text="Optional, e.g. 'Groupe 1'.")
    commune = forms.CharField(required=False, help_text="Optional, e.g. 'Commune 5'.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dataset"].queryset = DatasetPage.objects.filter(
            dataset_type="station_timeseries"
        ).order_by("title")

    def clean_files(self):
        files = self.cleaned_data["files"]
        bad = [f.name for f in files if not f.name.lower().endswith(".csv")]
        if bad:
            raise forms.ValidationError(f"Only .csv files are accepted: {', '.join(bad)}")
        return files
