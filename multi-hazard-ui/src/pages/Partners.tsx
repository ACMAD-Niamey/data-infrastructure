import { useEffect, useState } from 'react';
import {
  Globe, Building2, Cloud, Layers, Handshake, Mail, ExternalLink, CheckCircle,
} from 'lucide-react';
import NavBar from '../components/NavBar';
import {
  fetchProjectConfig, getProjectSlug, submitProjectContact,
  type ContactFormField, type Partner,
} from '../services/catalogLayersApi';

const contributions = [
  { title: 'Hazard & climate data', desc: 'Providing satellite, model, and station-derived data feeding the hub.', icon: Cloud },
  { title: 'High-resolution layers', desc: 'Generating and sharing high-quality spatial data and forecasts.', icon: Layers },
  { title: 'Early warning support', desc: 'Supporting advisories and evidence-based decision-making.', icon: Building2 },
  { title: 'Implementation support', desc: 'Helping translate data into action across the region.', icon: Handshake },
];

const inputClass =
  'w-full px-3 py-2.5 rounded-md border border-white/30 bg-white/10 text-white text-sm outline-none placeholder:text-white/50 focus:border-white/60';

export default function Partners() {
  const slug = getProjectSlug();

  const [partnersTitle, setPartnersTitle] = useState('');
  const [partnersIntro, setPartnersIntro] = useState('');
  const [partnersDesc, setPartnersDesc] = useState('');
  const [partnersImageUrl, setPartnersImageUrl] = useState<string | null>(null);
  const [ctaLabel, setCtaLabel] = useState('');
  const [ctaUrl, setCtaUrl] = useState('');
  const [partners, setPartners] = useState<Partner[]>([]);
  const [formFields, setFormFields] = useState<ContactFormField[]>([]);

  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    fetchProjectConfig(slug)
      .then((data) => {
        setPartnersTitle(data.partners_title ?? '');
        setPartnersIntro(data.partners_intro ?? '');
        setPartnersDesc(data.partners_description ?? '');
        setPartnersImageUrl(data.partners_image_url ?? null);
        setCtaLabel(data.partners_cta_label ?? '');
        setCtaUrl(data.partners_cta_url ?? '');
        setPartners(data.partners ?? []);
        const fields = data.contact_form_fields ?? [];
        setFormFields(fields);
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
    const result = await submitProjectContact(slug, formValues);
    if (result.ok) {
      setSubmitted(true);
    } else {
      setFormErrors(result.errors ?? {});
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
    <div className="min-h-screen flex flex-col bg-white">
      <NavBar />

      {/* Hero */}
      <div className="grid md:grid-cols-2 min-h-[320px]">
        <div className="px-6 md:px-12 py-12 flex flex-col justify-center">
          {partnersTitle && (
            <>
              <h1 className="text-2xl md:text-3xl font-extrabold text-hub-800 mb-2.5">{partnersTitle}</h1>
              <div className="w-11 h-[3px] bg-hub-400 rounded mb-5" />
            </>
          )}
          {partnersIntro && (
            <p className="text-base font-semibold text-hub-700 mb-3.5 leading-relaxed">{partnersIntro}</p>
          )}
          {partnersDesc && (
            <p className="text-sm text-gray-700 leading-relaxed max-w-md">{partnersDesc}</p>
          )}
        </div>
        <div className="min-h-[260px] overflow-hidden">
          {partnersImageUrl ? (
            <img src={partnersImageUrl} alt="" className="w-full h-full object-cover block" />
          ) : (
            <div className="w-full h-full bg-hub-100 flex items-center justify-center">
              <Globe className="size-16 text-hub-400/40" />
            </div>
          )}
        </div>
      </div>

      {/* Partner network */}
      {partners.length > 0 && (
        <div className="px-6 md:px-12 py-10 border-t border-gray-200">
          <h2 className="text-lg font-bold text-gray-900 mb-6">Partner network</h2>
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
            {partners.map((p, i) => (
              <div key={i} className="border border-gray-200 rounded-xl px-5 py-5 flex flex-col items-center text-center gap-2">
                {p.role && <span className="text-xs font-semibold text-hub-700">{p.role}</span>}
                <div className="h-15 flex items-center justify-center mb-1">
                  {p.logo_url ? (
                    <img src={p.logo_url} alt={p.name} className="max-h-15 max-w-[140px] object-contain" />
                  ) : (
                    <Building2 className="size-10 text-gray-300" />
                  )}
                </div>
                <span className="text-[15px] font-bold text-gray-900">{p.name}</span>
                {p.description && (
                  <p className="text-[13px] text-gray-500 leading-relaxed">{p.description}</p>
                )}
                {p.website_url && (
                  <a
                    href={p.website_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-hub-700 flex items-center gap-1 mt-1"
                  >
                    <ExternalLink className="size-3" />
                    Visit website
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* How partners contribute */}
      <div className="bg-gray-50 px-6 md:px-12 py-10 border-t border-gray-200">
        <h2 className="text-lg font-bold text-gray-900 mb-6">How partners contribute</h2>
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          {contributions.map(({ title, desc, icon: Icon }) => (
            <div key={title} className="bg-white border border-gray-200 rounded-xl px-4 py-4.5 flex gap-3 items-start">
              <div className="size-10 rounded-full bg-hub-100 flex items-center justify-center shrink-0">
                <Icon className="size-5 text-hub-400" />
              </div>
              <div>
                <h3 className="text-[13px] font-bold text-gray-900 mb-1">{title}</h3>
                <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA bar */}
      <div className="bg-hub-900 px-6 md:px-12 py-10 border-t border-gray-200">
        <div className="flex gap-12 flex-wrap items-start">
          {/* Left text */}
          <div className="flex-1 min-w-[280px]">
            <h3 className="text-base font-bold text-white mb-2">Interested in collaborating?</h3>
            <p className="text-[13px] text-white/75 leading-relaxed">
              Join our partner network and help strengthen climate hazard monitoring and early warning across Africa.
            </p>

            {ctaUrl && formFields.length > 0 && (
              <a
                href={ctaUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 mt-3.5 text-[13px] text-white/70 underline"
              >
                <ExternalLink className="size-3.5" />
                {ctaLabel || 'Contact us'}
              </a>
            )}

            {ctaUrl && formFields.length === 0 && (
              <a
                href={ctaUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 mt-5 px-6 py-2.5 rounded-lg bg-white text-hub-900 text-sm font-bold"
              >
                <Mail className="size-3.5" />
                {ctaLabel || 'Contact us'}
                <ExternalLink className="size-3.5" />
              </a>
            )}
          </div>

          {/* Right: inline form */}
          {formFields.length > 0 && (
            <div className="flex-1 min-w-[340px]">
              {submitted ? (
                <div className="flex flex-col items-center gap-3 py-5 text-center">
                  <CheckCircle className="size-11 text-hub-400" />
                  <h4 className="text-[15px] font-bold text-white">Message sent!</h4>
                  <p className="text-[13px] text-white/75">Thanks for reaching out — we'll be in touch soon.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-3">
                  {formFields.map((f) => (
                    <div key={f.label}>
                      <label className="block text-xs font-semibold text-white/85 mb-1">
                        {f.label}
                        {f.required && <span className="text-hub-400 ml-1">*</span>}
                      </label>
                      {f.field_type === 'textarea' ? (
                        <textarea
                          rows={3}
                          placeholder={f.placeholder}
                          value={formValues[f.label] ?? ''}
                          onChange={(e) => handleChange(f.label, e.target.value)}
                          className={`${inputClass} resize-y`}
                        />
                      ) : (
                        <input
                          type={f.field_type}
                          placeholder={f.placeholder}
                          value={formValues[f.label] ?? ''}
                          onChange={(e) => handleChange(f.label, e.target.value)}
                          className={inputClass}
                        />
                      )}
                      {formErrors[f.label] && (
                        <p className="text-[11px] text-red-300 mt-1">{formErrors[f.label]}</p>
                      )}
                    </div>
                  ))}
                  <button
                    type="submit"
                    disabled={submitting}
                    className="self-start px-6 py-2.5 rounded-lg bg-white text-hub-900 text-sm font-bold disabled:opacity-75 disabled:cursor-wait"
                  >
                    {submitting ? 'Sending…' : 'Send message'}
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
