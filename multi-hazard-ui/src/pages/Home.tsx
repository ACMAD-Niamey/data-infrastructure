import { Link } from 'react-router-dom';
import { Map, Database, Network, FileText, Droplets, CloudRain, Waves, ArrowRight } from 'lucide-react';
import NavBar from '../components/NavBar';

const exploreCards = [
  {
    icon: <Map className="size-8 text-hub-400" />,
    title: 'Geoportal',
    description: 'Explore interactive maps, layers, and geospatial data.',
    to: '/geoportal',
  },
  {
    icon: <Database className="size-8 text-hub-400" />,
    title: 'Data Services',
    description: 'Access APIs, data downloads, and programmatic services.',
    to: '/data-services',
  },
  {
    icon: <Network className="size-8 text-hub-400" />,
    title: 'Data Platforms',
    description: 'Access thematic platforms and partner systems.',
    to: '/data-platforms',
  },
  {
    icon: <FileText className="size-8 text-hub-400" />,
    title: 'Bulletins',
    description: 'Read latest advisories and situation reports.',
    to: '/bulletins',
  },
];

const mockBulletins = [
  {
    icon: <Droplets className="size-6 text-amber-500" />,
    title: 'Drought Watch Advisory – 2nd Dekad of May 2026',
    issued: '26 May 2026',
    category: 'Drought',
    categoryColor: 'bg-amber-100 text-amber-700',
  },
  {
    icon: <CloudRain className="size-6 text-blue-500" />,
    title: 'Heavy Rainfall Outlook – 27 May to 2 Jun 2026',
    issued: '26 May 2026',
    category: 'Weather',
    categoryColor: 'bg-blue-100 text-blue-700',
  },
  {
    icon: <Waves className="size-6 text-hub-400" />,
    title: 'Flood Risk Outlook – 1st to 7th June 2026',
    issued: '25 May 2026',
    category: 'Flood',
    categoryColor: 'bg-hub-100 text-hub-700',
  },
];

const partners = ['JRC', 'NORCAP', 'AU', 'ICPAC', 'WMO'];

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      {/* Hero */}
      <section className="flex flex-col lg:flex-row min-h-[480px]">
        {/* Left: text */}
        <div className="bg-hub-800 text-white flex flex-col justify-center px-10 py-14 lg:w-[480px] shrink-0">
          <h1 className="text-4xl font-bold leading-tight mb-4">Multi-Hazard Hub</h1>
          <p className="text-gray-300 text-base leading-relaxed mb-8">
            Monitoring, advisory, and geospatial data access for climate and
            hazard risks across Africa.
          </p>
          <div className="flex flex-wrap gap-3 mb-8">
            <Link
              to="/geoportal"
              className="flex items-center gap-2 bg-hub-400 hover:bg-hub-700 text-white px-5 py-2.5 rounded font-semibold text-sm transition-colors"
            >
              <Map className="size-4" />
              Open Geoportal
            </Link>
            <Link
              to="/data-services"
              className="flex items-center gap-2 border border-white text-white hover:bg-white/10 px-5 py-2.5 rounded font-semibold text-sm transition-colors"
            >
              <Database className="size-4" />
              Explore Data Services
            </Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'Drought', icon: <Droplets className="size-4" /> },
              { label: 'Weather Forecast', icon: <CloudRain className="size-4" /> },
              { label: 'Flood Risk', icon: <Waves className="size-4" /> },
            ].map(({ label, icon }) => (
              <Link
                key={label}
                to="/geoportal"
                className="flex items-center gap-1.5 border border-white/30 text-white/80 hover:border-hub-400 hover:text-hub-400 px-3 py-1.5 rounded text-xs transition-colors"
              >
                {icon}
                {label}
                <ArrowRight className="size-3" />
              </Link>
            ))}
          </div>
        </div>

        {/* Right: Africa map placeholder */}
        <div className="flex-1 bg-[#cde8f0] relative overflow-hidden min-h-[300px]">
          <div className="absolute inset-0 flex items-center justify-center text-hub-700/30 text-sm font-medium">
            <Map className="size-20 opacity-20" />
          </div>
          {/* Subtle pattern */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#b8dce8] to-[#8ec8d8] opacity-60" />
        </div>
      </section>

      {/* Explore the Hub */}
      <section className="py-12 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-hub-800 mb-1">Explore the Hub</h2>
          <div className="w-12 h-1 bg-hub-400 mb-8 rounded" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {exploreCards.map((card) => (
              <Link
                key={card.title}
                to={card.to}
                className="border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-hub-400 transition-all group"
              >
                <div className="mb-3">{card.icon}</div>
                <h3 className="font-bold text-gray-800 mb-1 group-hover:text-hub-700">
                  {card.title}
                </h3>
                <p className="text-sm text-gray-500 mb-3">{card.description}</p>
                <ArrowRight className="size-4 text-hub-400" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Latest Updates */}
      <section className="py-12 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-2xl font-bold text-hub-800">Latest Updates</h2>
            <Link
              to="/bulletins"
              className="flex items-center gap-1 text-hub-400 hover:text-hub-700 text-sm font-medium"
            >
              View all bulletins <ArrowRight className="size-4" />
            </Link>
          </div>
          <div className="w-12 h-1 bg-hub-400 mb-8 rounded" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {mockBulletins.map((b) => (
              <div key={b.title} className="bg-white border border-gray-200 rounded-lg p-5 flex gap-4">
                <div className="shrink-0 mt-0.5">{b.icon}</div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-800 mb-1 leading-snug">{b.title}</p>
                  <p className="text-xs text-gray-400 mb-2">Issued on {b.issued}</p>
                  <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded ${b.categoryColor}`}>
                    {b.category}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Partners footer */}
      <footer className="bg-white border-t border-gray-200 py-6 px-6">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-6 flex-wrap">
            <span className="text-xs text-gray-400 font-medium uppercase tracking-wide">Our Partners</span>
            {partners.map((p) => (
              <span key={p} className="text-sm font-semibold text-gray-500 border border-gray-200 px-3 py-1 rounded">
                {p}
              </span>
            ))}
          </div>
          <p className="text-xs text-gray-400">
            © 2026 ACMAD &nbsp;|&nbsp; Last updated: 26 May 2026
          </p>
        </div>
      </footer>
    </div>
  );
}
