from __future__ import annotations

from dataclasses import dataclass

from stations.models import Station


AFRICA_ISO3 = {
    "DZA", "AGO", "BEN", "BWA", "BFA", "BDI", "CPV", "CMR", "CAF", "TCD",
    "COM", "COD", "COG", "CIV", "DJI", "EGY", "GNQ", "ERI", "SWZ", "ETH",
    "GAB", "GMB", "GHA", "GIN", "GNB", "KEN", "LSO", "LBR", "LBY", "MDG",
    "MWI", "MLI", "MRT", "MUS", "MAR", "MOZ", "NAM", "NER", "NGA", "RWA",
    "STP", "SEN", "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN", "TZA", "TGO",
    "TUN", "UGA", "ZMB", "ZWE",
}


@dataclass
class AfricaFilterResult:
    is_candidate: bool
    reason: str


class AfricaFilterService:
    def from_topic(self, topic: str | None) -> AfricaFilterResult:
        if not topic:
            return AfricaFilterResult(False, "missing_topic")

        topic_l = topic.lower()
        african_keywords = ("africa", "afr", "nairobi", "dakar", "cairo")
        if any(keyword in topic_l for keyword in african_keywords):
            return AfricaFilterResult(True, "topic_keyword_match")

        return AfricaFilterResult(False, "topic_no_match")

    def from_station(self, station: Station | None) -> AfricaFilterResult:
        if not station:
            return AfricaFilterResult(False, "station_not_found")

        code = (station.country_code or "").upper()
        if code in AFRICA_ISO3:
            return AfricaFilterResult(True, "station_country_match")

        # Fallback: check if the station's coordinates fall within Africa's
        # geographic bounding box.  This handles BUFR/WIGOS stations that were
        # created without a country code (e.g. no classic WMO block number).
        # Longitude extends to 60° to cover Seychelles, Réunion, and Mauritius.
        if station.geom is not None:
            lat, lon = station.geom.y, station.geom.x
            if -35.0 <= lat <= 38.0 and -18.0 <= lon <= 60.0:
                return AfricaFilterResult(True, "station_coords_in_africa_bbox")

        return AfricaFilterResult(False, "station_not_in_africa")