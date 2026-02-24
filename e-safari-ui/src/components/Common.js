const MAPBOX_KEY = import.meta.env.VITE_MAPBOX_KEY;

export const basemaps = [
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
  ]

  export const base_url_ada = "https://ada.acmad.org";

  export const maplibre_str =
  "bbox={bbox-epsg-3857}&format=image/png&service=WMS&version=1.1.1&request=GetMap&srs=EPSG:3857&width=256&height=256&layers=";

  export const base_url = "https://climatehub.acmad.org"


