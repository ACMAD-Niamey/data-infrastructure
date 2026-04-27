
import { useRef, useEffect } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useMap } from "./MapContext.jsx"; 
import BasemapsControl from "maplibre-gl-basemaps";
import "maplibre-gl-basemaps/lib/basemaps.css";
import { basemaps } from "./Common";
import "../styles/map.css";

export default function MapComponent() {
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

  return (
    <div className="map-wrap">
      <div ref={mapContainer} className="map" />
    </div>
  );
}
