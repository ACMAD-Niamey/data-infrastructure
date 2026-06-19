/**
 * @typedef {{ minx: number; miny: number; maxx: number; maxy: number }} Bounds
 */

/**
 * @param {import('maplibre-gl').Map | null | undefined} map
 * @param {string} url
 * @param {string} name
 * @param {boolean} [active]
 * @param {Bounds | null} [bounds]
 * @param {boolean} [fitToBounds]
 */
export const add_image_layer = (map, url, name, active = true, bounds = null, fitToBounds = false, opacity = 1) => {
  if (!map) return;

  if (active === false) {
    if (map.getLayer(name)) {
      map.removeLayer(name);
      map.removeSource(name);
    }
    return;
  }

  if (map.getLayer(name)) {
    map.removeLayer(name);
    map.removeSource(name);
  }

  map.addSource(name, {
    type: "raster",
    tiles: [url],
    tileSize: 256,
  });

  map.addLayer({
    id: name,
    type: "raster",
    source: name,
    paint: { 'raster-opacity': opacity },
  });

  map.moveLayer(name);

  if (fitToBounds && bounds) {
    const [minLng, minLat, maxLng, maxLat] = [
      bounds.minx,
      bounds.miny,
      bounds.maxx,
      bounds.maxy,
    ];
    map.fitBounds([[minLng, minLat], [maxLng, maxLat]], { padding: 20 });
  }
};

export const remove_image_layer = (map, name) => {
  if (!map) return;

  if (map.getLayer(name)) {
    map.removeLayer(name);
    map.removeSource(name);
  }
};

export const add_only_if_not_exists = (map, url, name) => {
  if (!map) return false;

  if (!map.getLayer(name)) {
    map.addSource(name, {
      type: "raster",
      tiles: [url],
      tileSize: 256,
    });

    map.addLayer({
      id: name,
      type: "raster",
      source: name,
    });

    return true;
  }

  return false;
};

export const add_vector = (mapRef, url, name, bounds, type = "raster") => {
  if (!mapRef?.current || !url || !bounds) {
    console.warn("Missing mapRef, URL, or bounds.");
    return;
  }

  const map = mapRef.current;

  const [minLng, minLat, maxLng, maxLat] = [
    bounds.minx,
    bounds.miny,
    bounds.maxx,
    bounds.maxy,
  ];

  try {
    map.fitBounds(
      [
        [minLng, minLat],
        [maxLng, maxLat],
      ],
      { padding: 20 }
    );
  } catch (e) {
    console.warn("fitBounds failed", e);
    map.setZoom(4);
  }

  if (map.getSource(name)) {
    map.removeLayer(name);
    map.removeSource(name);
  }

  map.addSource(name, {
    type,
    tiles: [url],
    tileSize: 256,
  });

  map.addLayer({
    id: name,
    type,
    source: name,
  });

  map.moveLayer(name);
};
