import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Menu, Mail } from 'lucide-react';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import acmadLogo from './images/acmadLogo.svg';
import norcapLogo from './images/norcap_logo.svg';

const navLinks = [
  { label: 'HOME', to: '/' },
  { label: 'GEOPORTAL', to: '/geoportal' },
  { label: 'DATA SERVICES', to: '/data-services' },
  { label: 'DATA PLATFORMS', to: '/data-platforms' },
  { label: 'BULLETINS', to: '/bulletins' },
  { label: 'ABOUT', to: '/about' },
  { label: 'PARTNERS', to: '/partners' },
  { label: 'FEEDBACK', to: '/feedback' },
];

function NavLinks({ onClick }: { onClick?: () => void }) {
  return (
    <>
      {navLinks.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.to === '/'}
          onClick={onClick}
          className={({ isActive }) =>
            `text-sm font-medium tracking-wide whitespace-nowrap pb-0.5 transition-colors hover:text-hub-400 ${
              isActive
                ? 'text-white border-b-2 border-hub-400'
                : 'text-gray-300'
            }`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </>
  );
}

export default function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="bg-hub-800 text-white shadow-md flex-shrink-0">
      <div className="px-4 py-3 flex items-center gap-4">
        {/* Logo + wordmark */}
        <div className="flex items-center gap-3 shrink-0">
          <img src={acmadLogo} alt="ACMAD" className="w-10 h-10" />
          <div className="leading-tight">
            <div className="text-base font-bold tracking-tight">Multi-Hazard Hub</div>
            <div className="text-xs text-gray-300">Monitoring and Advisory</div>
          </div>
        </div>

        {/* Desktop nav */}
        <nav className="hidden lg:flex items-center gap-6 flex-1 justify-center">
          <NavLinks />
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-3 ml-auto shrink-0">
          <button className="hidden sm:flex items-center gap-1.5 border border-hub-400 text-hub-400 text-xs font-semibold px-3 py-1.5 rounded hover:bg-hub-400 hover:text-white transition-colors">
            <Mail className="size-3.5" />
            SUBSCRIBE
          </button>
          <img src={norcapLogo} alt="NORCAP" className="h-8 hidden sm:block" />

          {/* Mobile hamburger */}
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button className="lg:hidden p-1 text-gray-300 hover:text-white">
                <Menu className="size-6" />
              </button>
            </SheetTrigger>
            <SheetContent side="left" className="bg-hub-800 text-white border-hub-700 w-64">
              <nav className="flex flex-col gap-5 mt-8">
                <NavLinks onClick={() => setOpen(false)} />
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
