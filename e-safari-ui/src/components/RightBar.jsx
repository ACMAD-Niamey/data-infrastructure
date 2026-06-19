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
                return <Legend/>;
            case "Analysis":
                return (
                    <div style={{ padding: '24px 16px', textAlign: 'center', color: '#9ca3af', fontSize: '13px' }}>
                        {language === 'fr' ? 'En cours de développement' : 'Coming soon'}
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
