import {useState} from 'react'
import Legend from './Legend';
import "../styles/rightbar.css"

const RightBar = () => {
    const [active_tab, setActive_tab] = useState("Legend");

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
                        
                        <p>... Coming soon </p>
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
        onClick={() => setActive_tab("Legend")}
        style={{
          cursor: "pointer",
          backgroundColor: active_tab === "Legend" ? "lightgray" : "",
        }}
      >
        LEGEND
      </div>
      <div
        onClick={() => setActive_tab("Analysis")}
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
