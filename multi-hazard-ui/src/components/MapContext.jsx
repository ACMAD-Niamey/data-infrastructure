import { createContext, useContext, useRef } from "react";

const MapContext = createContext(null);

export const MapProvider = ({ children }) => {
  const mapRef = useRef(null);

  return (
    <MapContext.Provider value={{ mapRef }}>
      {children}
    </MapContext.Provider>
  );
};

export const useMap = () => useContext(MapContext);
