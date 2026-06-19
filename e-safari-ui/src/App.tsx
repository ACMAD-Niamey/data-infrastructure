import { Route, Routes, BrowserRouter } from "react-router-dom";
import { useState } from 'react';
import Portal from './Portal';
import { Header } from './components/Header';
import { ComingSoon } from './ComingSoon';
import Unavailable from './Unavailable';
import { MapProvider } from "./components/MapContext.jsx";
import { Language } from './types';
import 'bulma/css/bulma.min.css';

function App() {
  const [language, setLanguage] = useState<Language>('en');

  return (
    <BrowserRouter>
      <MapProvider>
        <div className="h-screen overflow-hidden flex flex-col">
          <Header language={language} onLanguageChange={setLanguage} />
          <div className="flex-1 min-h-0 overflow-hidden">
            <Routes>
              <Route path="/"          element={<Portal language={language} />} />
              <Route path="/geoportal" element={<Portal language={language} />} />
              <Route path="/home"      element={<ComingSoon language={language} />} />
              <Route path="/about"     element={<ComingSoon language={language} />} />
              <Route path="/partners"  element={<ComingSoon language={language} />} />
              <Route path="/feedback"  element={<ComingSoon language={language} />} />
              <Route path="*"          element={<Unavailable />} />
            </Routes>
          </div>
        </div>
      </MapProvider>
    </BrowserRouter>
  );
}

export default App;