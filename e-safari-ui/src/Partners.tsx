import { useEffect, useState } from 'react';
import {
  Globe, Building2, Cloud, Layers, Handshake, Mail, ExternalLink, CheckCircle,
} from 'lucide-react';
import type { Language } from './types';
import { getProjectSlug } from './services/catalogLayersApi';

interface PartnersProps {
  language: Language;
}

const translations = {
  en: {
    partnerNetwork: 'Partner network',
    howContribute: 'How partners contribute',
    interestedTitle: 'Interested in collaborating?',
    interestedSub: 'Join our partner network and help build climate-resilient and cooler cities across Africa.',
    contactFallback: 'Contact us',
    sendMessage: 'Send message',
    sending: 'Sending…',
    successTitle: 'Message sent!',
    successSub: "Thanks for reaching out — we'll be in touch soon.",
    required: 'required',
    visitWebsite: 'Visit website',
    contributions: [
      { title: 'Climate services',       desc: 'Providing climate data, forecasts and early warning for cities.' },
      { title: 'High-resolution data',   desc: 'Generating and sharing high-quality spatial data layers.' },
      { title: 'Urban planning insight', desc: 'Supporting evidence-based planning and cooling strategies.' },
      { title: 'Implementation support', desc: 'Helping cities translate evidence into action and impact.' },
    ],
  },
  fr: {
    partnerNetwork: 'Réseau de partenaires',
    howContribute: 'Comment les partenaires contribuent',
    interestedTitle: 'Vous souhaitez collaborer ?',
    interestedSub: 'Rejoignez notre réseau et contribuez à construire des villes plus résilientes en Afrique.',
    contactFallback: 'Nous contacter',
    sendMessage: 'Envoyer',
    sending: 'Envoi…',
    successTitle: 'Message envoyé !',
    successSub: 'Merci de nous avoir contactés — nous reviendrons vers vous rapidement.',
    required: 'obligatoire',
    visitWebsite: 'Visiter le site',
    contributions: [
      { title: 'Services climatiques',         desc: 'Fournir des données climatiques, des prévisions et des alertes pour les villes.' },
      { title: 'Données haute résolution',     desc: 'Générer et partager des couches de données spatiales de haute qualité.' },
      { title: 'Expertise en planification',   desc: "Soutenir la planification fondée sur des données probantes." },
      { title: 'Soutien à la mise en œuvre',  desc: 'Aider les villes à transformer les données en actions et en impact.' },
    ],
  },
};

const contributionIcons = [Cloud, Layers, Building2, Handshake];

interface Partner {
  role: string;
  logo_url: string | null;
  name: string;
  description: string;
  website_url: string;
}

interface ContactField {
  label: string;
  field_type: 'text' | 'email' | 'textarea';
  required: boolean;
  placeholder: string;
}

const inputBase: React.CSSProperties = {
  width: '100%',
  padding: '9px 12px',
  borderRadius: 6,
  border: '1px solid rgba(255,255,255,0.3)',
  backgroundColor: 'rgba(255,255,255,0.1)',
  color: 'white',
  fontSize: 13,
  outline: 'none',
  boxSizing: 'border-box',
};

export function Partners({ language }: PartnersProps) {
  const t = translations[language];
  const slug = getProjectSlug();

  const [partnersTitle, setPartnersTitle]       = useState('');
  const [partnersIntro, setPartnersIntro]       = useState('');
  const [partnersDesc, setPartnersDesc]         = useState('');
  const [partnersImageUrl, setPartnersImageUrl] = useState<string | null>(null);
  const [ctaLabel, setCtaLabel]                 = useState('');
  const [ctaUrl, setCtaUrl]                     = useState('');
  const [partners, setPartners]                 = useState<Partner[]>([]);
  const [formFields, setFormFields]             = useState<ContactField[]>([]);

  const [formValues, setFormValues]   = useState<Record<string, string>>({});
  const [formErrors, setFormErrors]   = useState<Record<string, string>>({});
  const [submitting, setSubmitting]   = useState(false);
  const [submitted, setSubmitted]     = useState(false);

  useEffect(() => {
    fetch(`/api/catalog/projects/${slug}/config/`)
      .then((r) => r.json())
      .then((data) => {
        setPartnersTitle(data.partners_title ?? '');
        setPartnersIntro(data.partners_intro ?? '');
        setPartnersDesc(data.partners_description ?? '');
        setPartnersImageUrl(data.partners_image_url ?? null);
        setCtaLabel(data.partners_cta_label ?? '');
        setCtaUrl(data.partners_cta_url ?? '');
        setPartners(data.partners ?? []);
        const fields: ContactField[] = data.contact_form_fields ?? [];
        setFormFields(fields);
        // pre-populate empty values
        const initial: Record<string, string> = {};
        fields.forEach((f) => { initial[f.label] = ''; });
        setFormValues(initial);
      })
      .catch(() => {});
  }, [slug]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormErrors({});
    setSubmitting(true);
    try {
      const res = await fetch(`/api/catalog/projects/${slug}/contact/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formValues),
      });
      const data = await res.json();
      if (res.ok) {
        setSubmitted(true);
      } else {
        setFormErrors(data.errors ?? {});
      }
    } catch {
      // network error — surface nothing, user can retry
    }
    setSubmitting(false);
  }

  function handleChange(label: string, value: string) {
    setFormValues((prev) => ({ ...prev, [label]: value }));
    if (formErrors[label]) {
      setFormErrors((prev) => { const n = { ...prev }; delete n[label]; return n; });
    }
  }

  return (
    <div style={{ overflowY: 'auto', height: '100%', backgroundColor: '#fff' }}>

      {/* ── Hero: two-column ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 340, backgroundColor: '#fff' }}>
        <div style={{ padding: '52px 48px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {partnersTitle && (
            <>
              <h1 style={{ fontSize: 'clamp(1.6rem, 3vw, 2.2rem)', fontWeight: 800, color: '#111827', marginBottom: 10 }}>
                {partnersTitle}
              </h1>
              <div style={{ width: 44, height: 3, backgroundColor: '#16803d', borderRadius: 2, marginBottom: 20 }} />
            </>
          )}
          {partnersIntro && (
            <p style={{ fontSize: 16, fontWeight: 600, color: '#16803d', marginBottom: 14, lineHeight: 1.5 }}>
              {partnersIntro}
            </p>
          )}
          {partnersDesc && (
            <p style={{ fontSize: 14, color: '#374151', lineHeight: 1.7, maxWidth: 440 }}>
              {partnersDesc}
            </p>
          )}
        </div>
        <div style={{ overflow: 'hidden', minHeight: 300 }}>
          {partnersImageUrl ? (
            <img src={partnersImageUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
          ) : (
            <div style={{ width: '100%', height: '100%', backgroundColor: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Globe style={{ width: 64, height: 64, color: '#bbf7d0' }} />
            </div>
          )}
        </div>
      </div>

      {/* ── Partner network ── */}
      {partners.length > 0 && (
        <div style={{ padding: '48px 48px', borderTop: '1px solid #e5e7eb' }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', marginBottom: 24 }}>{t.partnerNetwork}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            {partners.map((p, i) => (
              <div key={i} style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: '20px 18px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 8 }}>
                {p.role && (
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#16803d' }}>{p.role}</span>
                )}
                <div style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 4 }}>
                  {p.logo_url ? (
                    <img src={p.logo_url} alt={p.name} style={{ maxHeight: 60, maxWidth: 140, objectFit: 'contain' }} />
                  ) : (
                    <Building2 style={{ width: 40, height: 40, color: '#d1d5db' }} />
                  )}
                </div>
                <span style={{ fontSize: 15, fontWeight: 700, color: '#111827' }}>{p.name}</span>
                {p.description && (
                  <p style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.55, margin: 0 }}>{p.description}</p>
                )}
                {p.website_url && (
                  <a href={p.website_url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: 12, color: '#16803d', display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                    <ExternalLink style={{ width: 12, height: 12 }} />
                    {t.visitWebsite}
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── How partners contribute ── */}
      <div style={{ backgroundColor: '#f9fafb', padding: '48px 48px', borderTop: '1px solid #e5e7eb' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', marginBottom: 24 }}>{t.howContribute}</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          {t.contributions.map(({ title, desc }, i) => {
            const Icon = contributionIcons[i];
            return (
              <div key={i} style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: 12, padding: '18px 16px', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', backgroundColor: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon style={{ width: 20, height: 20, color: '#16803d' }} />
                </div>
                <div>
                  <h3 style={{ fontSize: 13, fontWeight: 700, color: '#111827', marginBottom: 4 }}>{title}</h3>
                  <p style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.55, margin: 0 }}>{desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── CTA bar ── */}
      <div style={{ backgroundColor: '#14532d', padding: '40px 48px', borderTop: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', gap: 48, flexWrap: 'wrap', alignItems: 'flex-start' }}>

          {/* Left text */}
          <div style={{ flex: '1 1 280px', minWidth: 0 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: 'white', marginBottom: 8 }}>{t.interestedTitle}</h3>
            <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)', margin: 0, lineHeight: 1.6 }}>{t.interestedSub}</p>

            {/* External link as secondary when form is also shown */}
            {ctaUrl && formFields.length > 0 && (
              <a href={ctaUrl} target="_blank" rel="noopener noreferrer"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 14, fontSize: 13, color: 'rgba(255,255,255,0.7)', textDecoration: 'underline' }}>
                <ExternalLink style={{ width: 13, height: 13 }} />
                {ctaLabel || t.contactFallback}
              </a>
            )}

            {/* Button only (no form) */}
            {ctaUrl && formFields.length === 0 && (
              <a href={ctaUrl} target="_blank" rel="noopener noreferrer"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 20, padding: '11px 24px', borderRadius: 8, backgroundColor: 'white', color: '#14532d', fontSize: 14, fontWeight: 700, textDecoration: 'none' }}>
                <Mail style={{ width: 15, height: 15 }} />
                {ctaLabel || t.contactFallback}
                <ExternalLink style={{ width: 13, height: 13 }} />
              </a>
            )}
          </div>

          {/* Right: inline form */}
          {formFields.length > 0 && (
            <div style={{ flex: '1 1 340px', minWidth: 0 }}>
              {submitted ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: '20px 0', textAlign: 'center' }}>
                  <CheckCircle style={{ width: 44, height: 44, color: '#4ade80' }} />
                  <h4 style={{ fontSize: 15, fontWeight: 700, color: 'white', margin: 0 }}>{t.successTitle}</h4>
                  <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)', margin: 0 }}>{t.successSub}</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {formFields.map((f) => (
                    <div key={f.label}>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.85)', marginBottom: 4 }}>
                        {f.label}
                        {f.required && <span style={{ color: '#86efac', marginLeft: 4 }}>*</span>}
                      </label>
                      {f.field_type === 'textarea' ? (
                        <textarea
                          rows={3}
                          placeholder={f.placeholder}
                          value={formValues[f.label] ?? ''}
                          onChange={(e) => handleChange(f.label, e.target.value)}
                          style={{ ...inputBase, resize: 'vertical' }}
                        />
                      ) : (
                        <input
                          type={f.field_type}
                          placeholder={f.placeholder}
                          value={formValues[f.label] ?? ''}
                          onChange={(e) => handleChange(f.label, e.target.value)}
                          style={inputBase}
                        />
                      )}
                      {formErrors[f.label] && (
                        <p style={{ fontSize: 11, color: '#fca5a5', margin: '4px 0 0' }}>{formErrors[f.label]}</p>
                      )}
                    </div>
                  ))}
                  <button
                    type="submit"
                    disabled={submitting}
                    style={{
                      alignSelf: 'flex-start',
                      padding: '10px 24px',
                      borderRadius: 8,
                      border: 'none',
                      backgroundColor: 'white',
                      color: '#14532d',
                      fontSize: 14,
                      fontWeight: 700,
                      cursor: submitting ? 'wait' : 'pointer',
                      opacity: submitting ? 0.75 : 1,
                    }}
                  >
                    {submitting ? t.sending : t.sendMessage}
                  </button>
                </form>
              )}
            </div>
          )}

        </div>
      </div>

    </div>
  );
}
