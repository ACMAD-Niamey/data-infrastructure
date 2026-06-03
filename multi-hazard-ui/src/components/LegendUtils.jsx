
import { useLegendStore } from "./stores/useLegendStore";


export function renderLegend(colorMap, title = "") {
    return (
      <div className="legend-block is-size-7" key={title} title={title}>
        {title && (
          <div style={{ fontWeight: "bold", marginBottom: "0.5em" }}>{title}</div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.3em" }}>
          {Object.entries(colorMap).map(([label, color]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.5em" }}>
              <div style={{
                width: "20px",
                height: "20px",
                backgroundColor: color,
                border: "1px solid #999"
              }} />
              <span style={{ fontSize: "13px" }}>{label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  



export const addLegendOnce = (legend, title) => {
    const { legends, addLegend } = useLegendStore.getState();
    const exists = legends.some((lg) => lg.props?.title === title);
    if (!exists) addLegend(legend);
  };
  

export function toTitle(str) {
    return str
      .split("-") // Step 1: Break at dashes
      .map(word => word.charAt(0).toUpperCase() + word.slice(1)) 
      .join(" "); 
  }
  

 
  
  
