from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection

from stations.models import CountryBoundary


class Command(BaseCommand):
    help = (
        "Populate stations.canonical_code by mapping each country_boundaries row "
        "(country_name -> country_code) onto stations whose country_name matches."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count candidates without writing.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing canonical_code values.",
        )
        parser.add_argument(
            "--country-name",
            type=str,
            default=None,
            help="Limit mapping to a single country name (case-insensitive).",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        force: bool = options["force"]
        only_country: str | None = options["country_name"]

        boundaries = (
            CountryBoundary.objects
            .exclude(country_name__isnull=True)
            .exclude(country_code__isnull=True)
            .exclude(country_name__exact="")
            .exclude(country_code__exact="")
        )
        if only_country:
            boundaries = boundaries.filter(country_name__iexact=only_country.strip())

        boundaries = list(boundaries.values("country_name", "country_code"))

        total_boundaries = CountryBoundary.objects.count()
        usable = len(boundaries)
        skipped = total_boundaries - usable

        self.stdout.write(
            f"Boundary mapping: total={total_boundaries} usable={usable} skipped={skipped}"
        )
        if not boundaries:
            self.stdout.write(self.style.WARNING("No usable boundaries; nothing to do."))
            return

        total_updated = 0
        with connection.cursor() as cur:
            for row in boundaries:
                name = (row["country_name"] or "").strip()
                code = (row["country_code"] or "").strip().upper()
                if not name or not code:
                    continue

                base_where = (
                    " WHERE TRIM(LOWER(country_name)) = LOWER(%s) "
                    "   AND country_name IS NOT NULL "
                )
                if not force:
                    base_where += " AND (canonical_code IS NULL OR TRIM(canonical_code) = '') "

                count_sql = "SELECT COUNT(*) FROM stations" + base_where
                cur.execute(count_sql, [name])
                candidate_count = int(cur.fetchone()[0] or 0)

                if dry_run:
                    self.stdout.write(
                        f"[DRY-RUN] {name} -> {code}: would update {candidate_count} stations"
                    )
                    total_updated += candidate_count
                    continue

                if candidate_count == 0:
                    continue

                update_sql = (
                    "UPDATE stations "
                    "SET canonical_code = %s, updated_at = NOW() "
                    + base_where
                )
                cur.execute(update_sql, [code, name])
                updated = int(cur.rowcount or 0)
                total_updated += updated
                self.stdout.write(f"{name} -> {code}: updated {updated} stations")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. dry_run={dry_run} force={force} total_updated={total_updated}"
            )
        )
