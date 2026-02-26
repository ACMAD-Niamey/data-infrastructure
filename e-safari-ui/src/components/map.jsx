
import { useRef, useEffect } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useMap } from "./MapContext.jsx"; 
import BasemapsControl from "maplibre-gl-basemaps";
import "maplibre-gl-basemaps/lib/basemaps.css";
import { basemaps } from "./Common";
import { add_image_layer, remove_image_layer } from "./Maputils";
import "../styles/map.css";

/**
 * @typedef {{ minx: number; miny: number; maxx: number; maxy: number }} Bounds
 * @typedef {{ url: string; layerName?: string; bounds?: Bounds | null; fitToBounds?: boolean }} SatelliteRaster
 * @param {{ satelliteRaster?: SatelliteRaster | null }} props
 */
export default function MapComponent({ satelliteRaster = null }) {
  const mapContainer = useRef(null);
  const { mapRef } = useMap(); 

  useEffect(() => {
    if (mapRef.current) return;

    mapRef.current = new maplibregl.Map({
      container: mapContainer.current,
      style: { version: 8, sources: {}, layers: [] },
      center: [12.7322, 0.4542],
      zoom: 1.8,
      minZoom: 0,
      maxZoom: 24,
    });

    

   

    mapRef.current.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current.addControl(
      new BasemapsControl({
        basemaps: basemaps,
        initialBasemap: "mapbox_light",
        expandDirection: "left",
      }),
      "bottom-right"
    );
  }, []); 

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const layerName = "satellite-imagery-overlay";
    if (!satelliteRaster?.url) {
      remove_image_layer(map, layerName);
      return;
    }

    add_image_layer(
      map,
      satelliteRaster.url,
      layerName,
      true,
      satelliteRaster.bounds ?? null,
      satelliteRaster.fitToBounds ?? false,
    );
  }, [mapRef, satelliteRaster]);

  return (
    <div className="map-wrap">
      <div ref={mapContainer} className="map" />
    </div>
  );
}
