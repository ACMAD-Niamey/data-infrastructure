import { useEffect, useState } from 'react'
import Legend from './Legend';
import { DataPanel } from './DataPanel';
import "../styles/rightbar.css"

const RightBar = ({ activeLayer, language, selectedFeature, activeTab, onTabChange, opacity, onOpacityChange }) => {
    const [active_tab, setActive_tab] = useState(activeTab || "Legend");

    useEffect(() => {
      if (activeTab) {
        setActive_tab(activeTab);
      }
    }, [activeTab]);

    const handleTabChange = (tab) => {
      setActive_tab(tab);
      if (onTabChange) {
        onTabChange(tab);
      }
    };

    const getContent = () => {
        switch (active_tab) {
            case "Legend":
                return (
                    <div>
                      <Legend/>
                      {activeLayer && (
                        <div style={{ padding: '8px 12px', borderTop: '1px solid #eee' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#15803d', marginBottom: '4px' }}>
                            <span>Opacity</span>
                            <span>{Math.round(opacity)}%</span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={100}
                            value={opacity}
                            onChange={(e) => onOpacityChange(Number(e.target.value))}
                            style={{ width: '100%', cursor: 'pointer', accentColor: '#15803d' }}
                          />
                        </div>
                      )}
                    </div>
                );
            case "Analysis":
                return (
                    <div>
                  <DataPanel
                    activeLayer={activeLayer}
                    language={language}
                    selectedFeature={selectedFeature}
                  />
                    </div>
                );
            default:
                return null;
        }
    }

  return (
    <div className="containter RightBarContainer">
    <div id="tabContainer">
      <div
        onClick={() => handleTabChange("Legend")}
        style={{
          cursor: "pointer",
          backgroundColor: active_tab === "Legend" ? "lightgray" : "",
        }}
      >
        LEGEND
      </div>
      <div
        onClick={() => handleTabChange("Analysis")}
        style={{
          cursor: "pointer",
          backgroundColor: active_tab === "Analysis" ? "lightgray" : "",
        }}
      >
        ANALYSIS
      </div>
    </div>
    <div id="contentContainer">{getContent()}</div>
  </div>
  )
}

export default RightBar
