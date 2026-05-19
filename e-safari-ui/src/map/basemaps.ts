/** Mapbox raster basemaps (same as afri-met). Requires `VITE_MAPBOX_KEY`. */
const MAPBOX_KEY = import.meta.env.VITE_MAPBOX_KEY;

export const mapboxBasemaps = [
  {
    id: "satellite",
    tiles: [
      `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/256/{z}/{x}/{y}?access_token=${MAPBOX_KEY}`,
    ],
    sourceExtraParams: {
      tileSize: 256,
      attribution:
        "© <a href='https://www.mapbox.com/about/maps/'>Mapbox</a> © <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>",
      minzoom: 0,
      maxzoom: 22,
    },
  },
  {
    id: "mapbox_light",
    tiles: [
      `https://api.mapbox.com/styles/v1/mapbox/light-v11/tiles/256/{z}/{x}/{y}?access_token=${MAPBOX_KEY}`,
    ],
    sourceExtraParams: {
      tileSize: 256,
      attribution:
        "© <a href='https://www.mapbox.com/about/maps/'>Mapbox</a> © <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>",
      minzoom: 0,
      maxzoom: 22,
    },
  },
  {
    id: "mapbox_streets",
    tiles: [
      `https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/256/{z}/{x}/{y}?access_token=${MAPBOX_KEY}`,
    ],
    sourceExtraParams: {
      tileSize: 256,
      attribution:
        "© <a href='https://www.mapbox.com/about/maps/'>Mapbox</a> © <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>",
      minzoom: 0,
      maxzoom: 22,
    },
  },
];

export function hasMapboxToken(): boolean {
  return Boolean(MAPBOX_KEY && String(MAPBOX_KEY).trim().length > 0);
}
