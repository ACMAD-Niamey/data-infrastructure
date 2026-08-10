import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { MapProvider } from './components/MapContext.jsx';
import Home from './pages/Home';
import Geoportal from './pages/Geoportal';
import StubPage from './pages/StubPage';
import DataPlatforms from './pages/DataPlatforms';
import DataPlatformDetail from './pages/DataPlatformDetail';

function App() {
  return (
    <BrowserRouter>
      <MapProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/geoportal" element={<Geoportal />} />
          <Route path="/data-services" element={<StubPage title="Data Services" />} />
          <Route path="/data-platforms" element={<DataPlatforms />} />
          <Route path="/data-platforms/:datasetId" element={<DataPlatformDetail />} />
          <Route path="/bulletins" element={<StubPage title="Bulletins" />} />
          <Route path="/about" element={<StubPage title="About" />} />
          <Route path="/partners" element={<StubPage title="Partners" />} />
          <Route path="/contact" element={<StubPage title="Contact" />} />
          <Route path="*" element={<StubPage title="Page Not Found" />} />
        </Routes>
      </MapProvider>
    </BrowserRouter>
  );
}

export default App;
