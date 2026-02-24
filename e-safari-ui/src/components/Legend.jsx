
import { useLegendStore } from "./stores/useLegendStore"


const Legend = () => {
  const legends = useLegendStore((state) => state.legends);

  return (
    <div
    className="legend-container"
    style={{
      display: "flex",
      flexDirection: "column", 
      alignItems: "flex-start", // 
      gap: "1em", // 
    }}
  >
    {legends.length === 0 ? (
      <p>No legend</p>
    ) : (
      legends.map((legend, index) => (
        <div key={index}>{legend}</div>
      ))
    )}
  </div>
  
  );
};

export default Legend;
