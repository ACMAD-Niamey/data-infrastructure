import { Language } from './types';

export function ComingSoon({ language }: { language: Language }) {
  return (
    <div className="h-full flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-gray-700 mb-2">
          {language === 'fr' ? 'Bientôt disponible' : 'Coming Soon'}
        </h2>
        <p className="text-gray-400 text-sm">
          {language === 'fr'
            ? 'Cette section est en cours de développement.'
            : 'This section is under development.'}
        </p>
      </div>
    </div>
  );
}
