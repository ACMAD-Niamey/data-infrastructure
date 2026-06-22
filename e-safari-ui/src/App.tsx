import { Route, Routes, BrowserRouter, Navigate } from "react-router-dom";
import { useState } from 'react';
import Portal from './Portal';
import { Home } from './Home';
import { About } from './About';
import { Partners } from './Partners';
import { Feedback } from './Feedback';
import { Header } from './components/Header';
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
              <Route path="/"          element={<Navigate to="/home" replace />} />
              <Route path="/geoportal" element={<Portal language={language} />} />
              <Route path="/home"      element={<Home language={language} />} />
              <Route path="/about"     element={<About language={language} />} />
              <Route path="/partners"  element={<Partners language={language} />} />
              <Route path="/feedback"  element={<Feedback language={language} />} />
              <Route path="*"          element={<Unavailable />} />
            </Routes>
          </div>
        </div>
      </MapProvider>
    </BrowserRouter>
  );
}

export default App;