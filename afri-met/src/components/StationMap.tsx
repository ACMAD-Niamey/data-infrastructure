import BasemapsControl from "maplibre-gl-basemaps";
import "maplibre-gl-basemaps/lib/basemaps.css";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { SpatialExtent } from "../api/types";
import { hasMapboxToken, mapboxBasemaps } from "../map/basemaps";
import { getTipgBaseUrl } from "../config";

/** Fallback when `VITE_MAPBOX_KEY` is not set — vector style, no basemap picker. */
const DEMO_STYLE_URL = "https://demotiles.maplibre.org/style.json";
const STATIONS_OBS_SOURCE_ID = "stations_obs_source";
const STATIONS_NO_OBS_SOURCE_ID = "stations_no_obs_source";
const STATIONS_OBS_LAYER_ID = "stations-obs";
const STATIONS_NO_OBS_LAYER_ID = "stations-no-obs";
const STATIONS_SOURCE_LAYER = "default";
const BASE_STATIONS_TILE_URL = `${getTipgBaseUrl()}/collections/public.stations/tiles/WebMercatorQuad/{z}/{x}/{y}`;
const OBSERVED_COLOR = "#22c55e";
const NO_OBS_COLOR = "#64748b";
const OBSERVED_RADIUS = 6;
const NO_OBS_RADIUS = 4;
const FULL_OPACITY = 1;
const HIDDEN_OPACITY = 0;
const DIM_OPACITY = 0.15;
const DEFAULT_AFRICA_EXTENT: SpatialExtent = {
  west: -25,
  south: -40,
  east: 60,
  north: 40,
};
const FIT_PADDING = { top: 48, bottom: 48, left: 48, right: 48 };
export type StationLegendMode = "hide" | "dim";
type StationLayerConfig = {
  sourceId: string;
  layerId: string;
  tileUrl: string;
  color: string;
  radius: number;
  active: boolean;
  dimmed: boolean;
};

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

function buildStationLayerTileUrl(hasObservations: boolean, countryCode: string | null): string {
  const parts = [`has_observations=${hasObservations ? "true" : "false"}`];
  if (countryCode) parts.push(`canonical_code='${escapeTipgLiteral(countryCode)}'`);
  const expr = parts.join(" AND ");
  return `${BASE_STATIONS_TILE_URL}?filter=${encodeURIComponent(expr)}`;
}

function addOrUpdateStationLayer(map: maplibregl.Map, config: StationLayerConfig): void {
  const { sourceId, layerId, tileUrl, color, radius, active, dimmed } = config;
  const targetOpacity = active ? FULL_OPACITY : dimmed ? DIM_OPACITY : HIDDEN_OPACITY;
  const targetVisibility = active || dimmed ? "visible" : "none";

  const source = map.getSource(sourceId) as maplibregl.VectorTileSource | undefined;
  const currentTileUrl = source?.tiles?.[0];

  if (source && currentTileUrl === tileUrl) {
    // Tile URL unchanged — update paint/layout properties to avoid tile refetch/flicker
    if (map.getLayer(layerId)) {
      map.setPaintProperty(layerId, "circle-opacity", targetOpacity);
      map.setLayoutProperty(layerId, "visibility", targetVisibility);
      return;
    }
    // Source present but layer is missing — add layer only (reuses existing source)
  } else {
    // Tile URL changed or source doesn't exist yet — recreate source (and layer below)
    if (map.getLayer(layerId)) map.removeLayer(layerId);
    if (source) map.removeSource(sourceId);
    map.addSource(sourceId, {
      type: "vector",
      tiles: [tileUrl],
    });
  }

  map.addLayer({
    id: layerId,
    type: "circle",
    source: sourceId,
    "source-layer": STATIONS_SOURCE_LAYER,
    paint: {
      "circle-radius": radius,
      "circle-color": color,
      "circle-opacity": targetOpacity,
      "circle-stroke-width": 1,
      "circle-stroke-color": "#0f172a",
    },
    layout: {
      visibility: targetVisibility,
    },
  });
}

function applyStationLayers(
  map: maplibregl.Map,
  countryCode: string | null,
  showObserved: boolean,
  showNoObservation: boolean,
  legendMode: StationLegendMode,
): void {
  const dimmed = legendMode === "dim";

  addOrUpdateStationLayer(map, {
    sourceId: STATIONS_NO_OBS_SOURCE_ID,
    layerId: STATIONS_NO_OBS_LAYER_ID,
    tileUrl: buildStationLayerTileUrl(false, countryCode),
    color: NO_OBS_COLOR,
    radius: NO_OBS_RADIUS,
    active: showNoObservation,
    dimmed,
  });
  addOrUpdateStationLayer(map, {
    sourceId: STATIONS_OBS_SOURCE_ID,
    layerId: STATIONS_OBS_LAYER_ID,
    tileUrl: buildStationLayerTileUrl(true, countryCode),
    color: OBSERVED_COLOR,
    radius: OBSERVED_RADIUS,
    active: showObserved,
    dimmed,
  });
}

function bindLayerInteractions(
  map: maplibregl.Map,
  onStationClick: (e: maplibregl.MapLayerMouseEvent) => void,
): void {
  const layers = [STATIONS_OBS_LAYER_ID, STATIONS_NO_OBS_LAYER_ID];
  for (const layerId of layers) {
    if (!map.getLayer(layerId)) continue;
    map.on("click", layerId, onStationClick);
    map.on("mouseenter", layerId, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", layerId, () => {
      map.getCanvas().style.cursor = "";
    });
  }
}

function unbindLayerInteractions(
  map: maplibregl.Map,
  onStationClick: (e: maplibregl.MapLayerMouseEvent) => void,
): void {
  const layers = [STATIONS_OBS_LAYER_ID, STATIONS_NO_OBS_LAYER_ID];
  for (const layerId of layers) {
    if (!map.getLayer(layerId)) continue;
    map.off("click", layerId, onStationClick);
  }
}

type StationMapProps = {
  extent: SpatialExtent | null;
  countryCode: string | null;
  showObserved: boolean;
  showNoObservation: boolean;
  legendMode: StationLegendMode;
  onSelectStation: (stationCode: string) => void;
};

export function StationMap({
  extent,
  countryCode,
  showObserved,
  showNoObservation,
  legendMode,
  onSelectStation,
}: StationMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onSelectStationRef = useRef(onSelectStation);
  onSelectStationRef.current = onSelectStation;
  const onStationClickRef = useRef<(e: maplibregl.MapLayerMouseEvent) => void>(() => undefined);
  onStationClickRef.current = (e: maplibregl.MapLayerMouseEvent) => {
    const code = e.features?.[0]?.properties?.station_code as string | undefined;
    if (code) onSelectStationRef.current(code);
  };

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

    map.on("load", () => {
      applyStationLayers(map, countryCode, showObserved, showNoObservation, legendMode);
      zoomToExtent(map, extent);
      bindLayerInteractions(map, onStationClickRef.current);
    });

    return () => {
      ro.disconnect();
      unbindLayerInteractions(map, onStationClickRef.current);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const applyCountryAndZoom = () => {
      unbindLayerInteractions(map, onStationClickRef.current);
      applyStationLayers(map, countryCode, showObserved, showNoObservation, legendMode);
      zoomToExtent(map, extent);
      bindLayerInteractions(map, onStationClickRef.current);
    };
    if (map.isStyleLoaded()) {
      applyCountryAndZoom();
    } else {
      map.once("load", applyCountryAndZoom);
    }
  }, [countryCode, extent]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    unbindLayerInteractions(map, onStationClickRef.current);
    applyStationLayers(map, countryCode, showObserved, showNoObservation, legendMode);
    bindLayerInteractions(map, onStationClickRef.current);
  }, [showObserved, showNoObservation, legendMode]);

  return <div ref={containerRef} className="h-full min-h-0 w-full min-w-0 flex-1" />;
}
