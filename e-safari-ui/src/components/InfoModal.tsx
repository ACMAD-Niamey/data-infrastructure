import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import type { Language } from '../types';
import { Dialog, DialogClose, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Info, ArrowRight } from 'lucide-react';
import { Button } from './ui/button';
import { getProjectSlug } from '../services/catalogLayersApi';

interface InfoModalProps {
  language: Language;
}

const translations = {
  en: { title: 'About e-SAFARI', learnMore: 'Learn more' },
  fr: { title: 'À propos d\'e-SAFARI', learnMore: 'En savoir plus' },
};

export function InfoModal({ language }: InfoModalProps) {
  const t = translations[language];
  const slug = getProjectSlug();
  const [intro, setIntro] = useState('');

  useEffect(() => {
    fetch(`/api/catalog/projects/${slug}/config/`)
      .then((r) => r.json())
      .then((data) => setIntro(data.subtitle ?? data.about_intro ?? ''))
      .catch(() => {});
  }, [slug]);

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-white hover:bg-white/10">
          <Info className="size-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t.title}</DialogTitle>
        </DialogHeader>
        {intro && (
          <p className="text-sm text-gray-600 leading-relaxed mt-1">{intro}</p>
        )}
        <div className="mt-4 flex justify-end">
          <DialogClose asChild>
            <Link
              to="/about"
              className="inline-flex items-center gap-1.5 rounded-md bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800 transition-colors"
            >
              {t.learnMore}
              <ArrowRight className="size-4" />
            </Link>
          </DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  );
}
