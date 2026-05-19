import { useEffect, useState } from 'react'
import Legend from './Legend';
import { DataPanel } from './DataPanel';
import "../styles/rightbar.css"

const RightBar = ({ activeLayer, language, selectedFeature, activeTab, onTabChange }) => {
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
