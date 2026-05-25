/**
 * BasemapsControl from maplibre-gl-basemaps with setup when style is already loaded
 * (avoids missing basemap layers if `load` fired before onAdd).
 */
export default class BasemapsControl {
  constructor(options) {
    this._options = options;
    this._container = document.createElement("div");
    this._container.classList.add("maplibregl-ctrl", "maplibregl-ctrl-basemaps", "closed");

    switch (this._options.expandDirection || "right") {
      case "top":
        this._container.classList.add("reverse");
        break;
      case "down":
        this._container.classList.add("column");
        break;
      case "left":
        this._container.classList.add("reverse");
        break;
      case "right":
        this._container.classList.add("row");
        break;
      default:
        break;
    }

    this._container.addEventListener("mouseenter", () => {
      this._container.classList.remove("closed");
    });
    this._container.addEventListener("mouseleave", () => {
      this._container.classList.add("closed");
    });
  }

  onAdd(map) {
    this._map = map;

    const setup = () => {
      if (this._setupDone) return;
      this._setupDone = true;

      this._options.basemaps.forEach(
        ({ id, tiles, sourceExtraParams = {}, layerExtraParams = {} }) => {
          if (!map.getSource(id)) {
            map.addSource(id, {
              ...sourceExtraParams,
              type: "raster",
              tiles,
            });
          }
          if (!map.getLayer(id)) {
            map.addLayer({
              ...layerExtraParams,
              id,
              source: id,
              type: "raster",
            });
          }

          const thumb = document.createElement("img");
          thumb.src = tiles[0]
            .replace("{x}", "0")
            .replace("{y}", "0")
            .replace("{z}", String(sourceExtraParams.minzoom ?? 0));
          thumb.classList.add("basemap");
          thumb.dataset.id = id;
          thumb.alt = id;
          thumb.addEventListener("click", (event) => {
            event.stopPropagation();
            this._activateBasemap(id);
          });

          this._container.appendChild(thumb);

          if (this._options.initialBasemap === id) {
            map.setLayoutProperty(id, "visibility", "visible");
            thumb.classList.add("active");
            this._activeId = id;
          } else {
            map.setLayoutProperty(id, "visibility", "none");
          }
        },
      );
    };

    if (map.isStyleLoaded()) {
      setup();
    } else {
      map.once("load", setup);
    }

    return this._container;
  }

  _activateBasemap(id) {
    const map = this._map;
    if (!map || !map.getLayer(id) || this._activeId === id) {
      return;
    }

    if (this._activeId && map.getLayer(this._activeId)) {
      map.setLayoutProperty(this._activeId, "visibility", "none");
    }
    map.setLayoutProperty(id, "visibility", "visible");
    this._activeId = id;

    const activeThumb = this._container.querySelector(".active");
    if (activeThumb) {
      activeThumb.classList.remove("active");
    }
    const thumb = this._container.querySelector(`[data-id="${id}"]`);
    if (thumb) {
      thumb.classList.add("active");
    }
  }

  onRemove() {
    this._container.parentNode?.removeChild(this._container);
  }
}
