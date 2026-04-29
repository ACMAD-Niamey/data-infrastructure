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
const STATIONS_TILE_URL = `${getTipgBaseUrl()}/collections/public.stations/tiles/WebMercatorQuad/{z}/{x}/{y}`;
const OBSERVED_COLOR = "#22c55e";
const NO_OBS_COLOR = "#64748b";
const OBSERVED_RADIUS = 6;
const NO_OBS_RADIUS = 4;
const DIM_OPACITY = 0.15;
const HIDDEN_OPACITY = 0;
const FULL_OPACITY = 1;

export type StationLegendMode = "hide" | "dim";

function observedMembershipExpression(observedStationCodes: string[]) {
  return [
    "in",
    ["get", "station_code"],
    ["literal", observedStationCodes] as unknown as maplibregl.ExpressionInputType,
  ] as unknown as maplibregl.ExpressionSpecification;
}

function applyStationLayerStyle(
  map: maplibregl.Map,
  observedStationCodes: string[],
  showObserved: boolean,
  showNoObservation: boolean,
  mode: StationLegendMode,
) {
  if (!map.getLayer(STATIONS_LAYER_ID)) return;

  const observedMembership = observedMembershipExpression(observedStationCodes);
  const hiddenOpacity = mode === "hide" ? HIDDEN_OPACITY : DIM_OPACITY;

  map.setPaintProperty(STATIONS_LAYER_ID, "circle-color", [
    "case",
    observedMembership,
    OBSERVED_COLOR,
    NO_OBS_COLOR,
  ]);

  map.setPaintProperty(STATIONS_LAYER_ID, "circle-radius", [
    "case",
    observedMembership,
    OBSERVED_RADIUS,
    NO_OBS_RADIUS,
  ]);

  map.setPaintProperty(STATIONS_LAYER_ID, "circle-opacity", [
    "case",
    observedMembership,
    showObserved ? FULL_OPACITY : hiddenOpacity,
    showNoObservation ? FULL_OPACITY : hiddenOpacity,
  ]);

  if (mode === "hide") {
    if (showObserved && showNoObservation) {
      map.setFilter(STATIONS_LAYER_ID, null);
    } else if (showObserved) {
      map.setFilter(STATIONS_LAYER_ID, observedMembership);
    } else if (showNoObservation) {
      map.setFilter(STATIONS_LAYER_ID, ["!", observedMembership] as maplibregl.FilterSpecification);
    } else {
      map.setFilter(STATIONS_LAYER_ID, ["==", ["get", "station_code"], "__none__"]);
    }
  } else {
    map.setFilter(STATIONS_LAYER_ID, null);
  }
}

type StationMapProps = {
  extent: SpatialExtent | null;
  observedStationCodes: string[];
  showObserved: boolean;
  showNoObservation: boolean;
  legendMode: StationLegendMode;
  onSelectStation: (stationCode: string) => void;
};

export function StationMap({
  extent,
  observedStationCodes,
  showObserved,
  showNoObservation,
  legendMode,
  onSelectStation,
}: StationMapProps) {
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
      if (map.getSource(STATIONS_SOURCE_ID)) return;

      map.addSource(STATIONS_SOURCE_ID, {
        type: "vector",
        tiles: [STATIONS_TILE_URL],
      });
      map.addLayer({
        id: STATIONS_LAYER_ID,
        type: "circle",
        source: STATIONS_SOURCE_ID,
        "source-layer": STATIONS_SOURCE_LAYER,
        paint: { "circle-radius": OBSERVED_RADIUS, "circle-color": OBSERVED_COLOR, "circle-stroke-width": 1, "circle-stroke-color": "#0f172a" },
      });
      applyStationLayerStyle(map, observedStationCodes, showObserved, showNoObservation, legendMode);

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
  }, [onSelectStation]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    applyStationLayerStyle(map, observedStationCodes, showObserved, showNoObservation, legendMode);
  }, [observedStationCodes, showObserved, showNoObservation, legendMode]);

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
