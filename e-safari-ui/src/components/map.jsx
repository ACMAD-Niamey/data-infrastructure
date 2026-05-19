import { useRef, useEffect } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "maplibre-gl-basemaps/lib/basemaps.css";
import BasemapsControl from "../map/basemapsControl.js";
import { useMap } from "./MapContext.jsx";
import { hasMapboxToken, mapboxBasemaps } from "../map/basemaps";
import "../styles/map.css";

/** Fallback when `VITE_MAPBOX_KEY` is not set — vector style, no basemap picker. */
const DEMO_STYLE_URL = "https://demotiles.maplibre.org/style.json";

export default function MapComponent() {
  const mapContainer = useRef(null);
  const { mapRef } = useMap();

  useEffect(() => {
    const el = mapContainer.current;
    if (!el) return;

    const useMapbox = hasMapboxToken();

    const map = new maplibregl.Map({
      container: el,
      style: useMapbox
        ? { version: 8, sources: {}, layers: [] }
        : DEMO_STYLE_URL,
      center: [12.7322, 0.4542],
      zoom: 1.8,
      minZoom: 0,
      maxZoom: 24,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
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

    return () => {
      ro.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, [mapRef]);

  return (
    <div className="map-wrap">
      <div ref={mapContainer} className="map" />
    </div>
  );
}
