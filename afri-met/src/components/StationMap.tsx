import type { FeatureCollection, Point } from "geojson";
import BasemapsControl from "maplibre-gl-basemaps";
import "maplibre-gl-basemaps/lib/basemaps.css";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { SpatialExtent, StationListItem } from "../api/types";
import { hasMapboxToken, mapboxBasemaps } from "../map/basemaps";

/** Fallback when `VITE_MAPBOX_KEY` is not set — vector style, no basemap picker. */
const DEMO_STYLE_URL = "https://demotiles.maplibre.org/style.json";

function buildGeoJSON(stations: StationListItem[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: stations
      .filter((s) => s.longitude != null && s.latitude != null)
      .map((s) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [s.longitude!, s.latitude!],
        },
        properties: {
          station_code: s.station_code,
          name: s.name ?? "",
          country_code: s.country_code ?? "",
        },
      })),
  };
}

type StationMapProps = {
  stations: StationListItem[];
  extent: SpatialExtent | null;
  onSelectStation: (stationCode: string) => void;
};

export function StationMap({ stations, extent, onSelectStation }: StationMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const useMapbox = hasMapboxToken();

    const map = new maplibregl.Map({
      container: el,
      style: useMapbox
        ? ({ version: 8, sources: {}, layers: [] } as maplibregl.StyleSpecification)
        : DEMO_STYLE_URL,
      center: [15, 5],
      zoom: 2.5,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
    if (useMapbox) {
      map.addControl(
        new BasemapsControl({
          basemaps: mapboxBasemaps,
          initialBasemap: "mapbox_light",
          expandDirection: "left",
        }),
        "bottom-right",
      );
    }

    mapRef.current = map;

    const resize = () => map.resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    const onStationClick = (e: maplibregl.MapLayerMouseEvent) => {
      const code = e.features?.[0]?.properties?.station_code as string | undefined;
      if (code) onSelectStation(code);
    };

    map.on("load", () => {
      map.resize();
      if (map.getSource("stations")) return;

      map.addSource("stations", {
        type: "geojson",
        data: buildGeoJSON([]),
      });
      map.addLayer({
        id: "stations-circles",
        type: "circle",
        source: "stations",
        paint: {
          "circle-radius": 6,
          "circle-color": "#22d3ee",
          "circle-stroke-width": 1,
          "circle-stroke-color": "#0f172a",
        },
      });

      map.on("click", "stations-circles", onStationClick);
      map.on("mouseenter", "stations-circles", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "stations-circles", () => {
        map.getCanvas().style.cursor = "";
      });
    });

    return () => {
      ro.disconnect();
      map.off("click", "stations-circles", onStationClick);
      map.remove();
      mapRef.current = null;
    };
  }, [onSelectStation]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const push = () => {
      const src = map.getSource("stations") as GeoJSONSource | undefined;
      if (src) src.setData(buildGeoJSON(stations));
    };

    if (map.isStyleLoaded()) push();
    else map.once("load", push);
  }, [stations]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !extent) return;

    const run = () => {
      map.resize();
      try {
        map.fitBounds(
          [
            [extent.west, extent.south],
            [extent.east, extent.north],
          ],
          { padding: { top: 48, bottom: 48, left: 48, right: 48 }, maxZoom: 10, duration: 800 },
        );
      } catch {
        /* invalid bounds */
      }
    };

    if (map.isStyleLoaded()) run();
    else map.once("load", run);
  }, [extent]);

  return <div ref={containerRef} className="h-full min-h-0 w-full min-w-0 flex-1" />;
}
