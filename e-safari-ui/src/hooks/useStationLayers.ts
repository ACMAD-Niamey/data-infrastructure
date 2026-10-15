import { useEffect, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import type { CatalogLayer } from "../types/catalogLayer";
import {
  fetchStationLocations,
  stationTileUrl,
} from "../services/stationsApi";
import type { StationLocation } from "../services/stationsApi";
import type { BoundsObject } from "../services/layersApi";

// TiPG names the vector-tile layer "default" for every collection.
const SOURCE_LAYER = "default";
// Sun/shade is the campaign's core comparison, so exposure drives the colour.
const EXPOSURE_COLOR = ["match", ["get", "exposure"], "sun", "#f59e0b", "shade", "#2563eb", "#6b7280"];

const sourceId = (layerId: string) => `stations-${layerId}`;
const circleId = (layerId: string) => `stations-${layerId}-circles`;
const ringId = (layerId: string) => `stations-${layerId}-selected`;

type Params = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mapRef: MutableRefObject<any>;
  activeLayers: CatalogLayer[];
  opacities: Record<string, number>;
  /** Site name of the location currently open in the Analysis tab. */
  selectedSite: string | null;
  onSelect: (layerId: string, station: StationLocation) => void;
  onBounds: (layerId: string, bounds: BoundsObject | null) => void;
};

/**
 * Draws each active `station_timeseries` layer as TiPG vector tiles and loads its
 * (small) location list so a click can be paired with the sun/shade twin.
 */
export function useStationLayers({
  mapRef, activeLayers, opacities, selectedSite, onSelect, onBounds,
}: Params) {
  const [locations, setLocations] = useState<Record<string, StationLocation[]>>({});
  const fetchedRef = useRef<Set<string>>(new Set());
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const stationLayers = activeLayers.filter((l) => l.dataset.dataset_type === "station_timeseries" && l.station_timeseries);

  // Load the location list once per layer; also yields bounds for "zoom to layer".
  useEffect(() => {
    stationLayers.forEach((layer) => {
      const cfg = layer.station_timeseries!;
      if (fetchedRef.current.has(layer.id)) return;
      fetchedRef.current.add(layer.id);
      fetchStationLocations(cfg.tipg_collection, cfg.dataset_code)
        .then((items) => {
          setLocations((prev) => ({ ...prev, [layer.id]: items }));
          if (!items.length) return;
          onBounds(layer.id, {
            minx: Math.min(...items.map((i) => i.lng)),
            miny: Math.min(...items.map((i) => i.lat)),
            maxx: Math.max(...items.map((i) => i.lng)),
            maxy: Math.max(...items.map((i) => i.lat)),
          });
        })
        .catch(() => fetchedRef.current.delete(layer.id));
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayers]);

  // Add / remove map layers to match the active set.
  useEffect(() => {
    const map = mapRef?.current;
    if (!map) return;

    const apply = () => {
      const activeIds = new Set(stationLayers.map((l) => l.id));
      // Remove layers that were switched off. Station layer ids are unknown here,
      // so scan the style for our own prefix.
      (map.getStyle()?.layers ?? [])
        .filter((l: { id: string }) => l.id.startsWith("stations-") && l.id.endsWith("-circles"))
        .forEach((l: { id: string }) => {
          const layerId = l.id.slice("stations-".length, -"-circles".length);
          if (activeIds.has(layerId)) return;
          [ringId(layerId), circleId(layerId)].forEach((id) => map.getLayer(id) && map.removeLayer(id));
          map.getSource(sourceId(layerId)) && map.removeSource(sourceId(layerId));
        });

      stationLayers.forEach((layer) => {
        if (map.getSource(sourceId(layer.id))) return;
        const cfg = layer.station_timeseries!;
        map.addSource(sourceId(layer.id), {
          type: "vector",
          tiles: [stationTileUrl(cfg.tipg_collection, cfg.dataset_code)],
          minzoom: 0,
          maxzoom: 14,
        });
        map.addLayer({
          id: circleId(layer.id),
          type: "circle",
          source: sourceId(layer.id),
          "source-layer": SOURCE_LAYER,
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 5, 14, 9],
            "circle-color": EXPOSURE_COLOR,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.5,
            "circle-opacity": (opacities[layer.id] ?? layer.ui?.opacity ?? 85) / 100,
          },
        });
        // Ring around the open location: both sensors of a site share one ring.
        map.addLayer({
          id: ringId(layer.id),
          type: "circle",
          source: sourceId(layer.id),
          "source-layer": SOURCE_LAYER,
          filter: ["==", ["get", "site"], ""],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 9, 14, 14],
            "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": "#111827",
            "circle-stroke-width": 2,
          },
        });
      });
    };

    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
    return () => map.off("load", apply);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayers, mapRef]);

  // Click / hover handlers (re-bound when the active set changes).
  useEffect(() => {
    const map = mapRef?.current;
    if (!map || stationLayers.length === 0) return;

    const handlers = stationLayers.map((layer) => {
      const id = circleId(layer.id);
      const onClick = (e: { features?: Array<{ properties: Record<string, string> }> }) => {
        const props = e.features?.[0]?.properties;
        if (!props?.station_code) return;
        const known = locations[layer.id]?.find((s) => s.code === props.station_code);
        onSelectRef.current(layer.id, known ?? {
          code: props.station_code, name: props.name, site: props.site ?? null,
          exposure: (props.exposure as StationLocation["exposure"]) ?? null,
          commune: props.commune ?? null, lng: 0, lat: 0,
        });
      };
      const enter = () => { map.getCanvas().style.cursor = "pointer"; };
      const leave = () => { map.getCanvas().style.cursor = ""; };
      if (map.getLayer(id)) {
        map.on("click", id, onClick);
        map.on("mouseenter", id, enter);
        map.on("mouseleave", id, leave);
      }
      return { id, onClick, enter, leave };
    });

    return () => handlers.forEach(({ id, onClick, enter, leave }) => {
      map.off("click", id, onClick);
      map.off("mouseenter", id, enter);
      map.off("mouseleave", id, leave);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayers, locations, mapRef]);

  // Highlight ring follows the open location.
  useEffect(() => {
    const map = mapRef?.current;
    if (!map) return;
    stationLayers.forEach((layer) => {
      if (map.getLayer(ringId(layer.id))) {
        map.setFilter(ringId(layer.id), ["==", ["get", "site"], selectedSite ?? ""]);
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSite, activeLayers, mapRef]);

  return { locations };
}

export function setStationOpacity(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  map: any, layerId: string, percent: number,
) {
  if (map?.getLayer(circleId(layerId))) {
    map.setPaintProperty(circleId(layerId), "circle-opacity", percent / 100);
  }
}
