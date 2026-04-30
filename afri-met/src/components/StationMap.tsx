import BasemapsControl from "maplibre-gl-basemaps";
import "maplibre-gl-basemaps/lib/basemaps.css";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { SpatialExtent } from "../api/types";
import { hasMapboxToken, mapboxBasemaps } from "../map/basemaps";
import { getTipgBaseUrl } from "../config";

/** Fallback when `VITE_MAPBOX_KEY` is not set — vector style, no basemap picker. */
const DEMO_STYLE_URL = "https://demotiles.maplibre.org/style.json";
const STATIONS_SOURCE_ID = "stations";
const STATIONS_LAYER_ID = "stations-circles";
const STATIONS_SOURCE_LAYER = "default";
const BASE_STATIONS_TILE_URL = `${getTipgBaseUrl()}/collections/public.stations/tiles/WebMercatorQuad/{z}/{x}/{y}`;
const STATION_COLOR = "#22c55e";
const STATION_RADIUS = 6;
const FULL_OPACITY = 1;
const DEFAULT_AFRICA_EXTENT: SpatialExtent = {
  west: -25,
  south: -40,
  east: 60,
  north: 40,
};
const FIT_PADDING = { top: 48, bottom: 48, left: 48, right: 48 };

function fitMapToExtent(map: maplibregl.Map, extent: SpatialExtent): void {
  const west = Number(extent.west);
  const south = Number(extent.south);
  const east = Number(extent.east);
  const north = Number(extent.north);
  if (![west, south, east, north].every(Number.isFinite)) return;
  if (west === east || south === north) return;
  map.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    { padding: FIT_PADDING, maxZoom: 10, duration: 800 },
  );
}

function zoomToExtent(map: maplibregl.Map, extent: SpatialExtent | null): void {
  const nextExtent = extent ?? DEFAULT_AFRICA_EXTENT;
  map.stop();
  map.resize();
  fitMapToExtent(map, nextExtent);
}

function escapeTipgLiteral(value: string): string {
  return value.replaceAll("'", "''");
}

function buildStationsTileUrl(countryCode: string | null): string {
  if (!countryCode) return BASE_STATIONS_TILE_URL;
  const expr = `canonical_code='${escapeTipgLiteral(countryCode)}'`;
  return `${BASE_STATIONS_TILE_URL}?filter=${encodeURIComponent(expr)}`;
}

function addOrReplaceStationsLayer(map: maplibregl.Map, countryCode: string | null): void {
  if (map.getLayer(STATIONS_LAYER_ID)) {
    map.removeLayer(STATIONS_LAYER_ID);
  }
  if (map.getSource(STATIONS_SOURCE_ID)) {
    map.removeSource(STATIONS_SOURCE_ID);
  }
  map.addSource(STATIONS_SOURCE_ID, {
    type: "vector",
    tiles: [buildStationsTileUrl(countryCode)],
  });
  map.addLayer({
    id: STATIONS_LAYER_ID,
    type: "circle",
    source: STATIONS_SOURCE_ID,
    "source-layer": STATIONS_SOURCE_LAYER,
    paint: { "circle-radius": STATION_RADIUS, "circle-color": STATION_COLOR, "circle-opacity": FULL_OPACITY, "circle-stroke-width": 1, "circle-stroke-color": "#0f172a" },
  });
}

type StationMapProps = {
  extent: SpatialExtent | null;
  countryCode: string | null;
  onSelectStation: (stationCode: string) => void;
};

export function StationMap({
  extent,
  countryCode,
  onSelectStation,
}: StationMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onSelectStationRef = useRef(onSelectStation);
  onSelectStationRef.current = onSelectStation;

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
      if (code) onSelectStationRef.current(code);
    };

    map.on("load", () => {
      addOrReplaceStationsLayer(map, countryCode);
      zoomToExtent(map, extent);

      map.on("click", STATIONS_LAYER_ID, onStationClick);
      map.on("mouseenter", STATIONS_LAYER_ID, () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", STATIONS_LAYER_ID, () => {
        map.getCanvas().style.cursor = "";
      });
    });

    return () => {
      ro.disconnect();
      map.off("click", STATIONS_LAYER_ID, onStationClick);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const applyLayerAndZoom = () => {
      addOrReplaceStationsLayer(map, countryCode);
      zoomToExtent(map, extent);
    };
    if (map.isStyleLoaded()) {
      applyLayerAndZoom();
    } else {
      map.once("load", applyLayerAndZoom);
    }
  }, [countryCode, extent]);

  return <div ref={containerRef} className="h-full min-h-0 w-full min-w-0 flex-1" />;
}
