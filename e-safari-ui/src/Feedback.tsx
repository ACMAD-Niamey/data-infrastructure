import { useEffect, useState } from 'react';
import {
  MessageSquare, HelpCircle, ChevronDown, ChevronUp,
  Send, Lock, Mail, ExternalLink, CheckCircle, Headphones,
} from 'lucide-react';
import type { Language } from './types';
import type { CountryOption } from './components/SubHeader';
import { getProjectSlug } from './services/catalogLayersApi';

interface FeedbackProps {
  language: Language;
}

interface FeedbackField {
  label: string;
  field_type: 'text' | 'email' | 'textarea' | 'country_select' | 'topic_select';
  required: boolean;
  placeholder: string;
  choices: string[];
}

interface FAQ {
  question: string;
  answer: string;
}

const translations = {
  en: {
    sendFeedback: 'Send feedback',
    submit: 'Submit feedback',
    submitting: 'Submitting…',
    successTitle: 'Thank you for your feedback!',
    successSub: 'Your message has been received and will help us improve e-SAFARI.',
    faqTitle: 'FAQ',
    faqSub: 'Frequently asked questions',
    privacyNote: 'We value your privacy. Your feedback will only be used to improve e-SAFARI.',
    supportTitle: 'Need direct support?',
    supportSub: 'Our team is ready to help with technical questions or data access.',
    contactFallback: 'Contact us',
    required: '*',
    selectDefault: '— Select —',
    submitError: 'Submission failed. Please try again.',
  },
  fr: {
    sendFeedback: 'Envoyer des commentaires',
    submit: 'Soumettre',
    submitting: 'Envoi…',
    successTitle: 'Merci pour vos commentaires !',
    successSub: 'Votre message a été reçu et nous aidera à améliorer e-SAFARI.',
    faqTitle: 'FAQ',
    faqSub: 'Questions fréquemment posées',
    privacyNote: 'Nous respectons votre vie privée. Vos commentaires seront uniquement utilisés pour améliorer e-SAFARI.',
    supportTitle: 'Besoin d\'aide directe ?',
    supportSub: 'Notre équipe est prête à vous aider pour toute question technique ou accès aux données.',
    contactFallback: 'Nous contacter',
    required: '*',
    selectDefault: '— Sélectionner —',
    submitError: 'Échec de l\'envoi. Veuillez réessayer.',
  },
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '9px 12px',
  borderRadius: 6,
  border: '1px solid #d1d5db',
  fontSize: 13,
  color: '#111827',
  outline: 'none',
  boxSizing: 'border-box',
  backgroundColor: 'white',
};

export function Feedback({ language }: FeedbackProps) {
  const t = translations[language];
  const slug = getProjectSlug();

  const [feedbackTitle, setFeedbackTitle]       = useState('');
  const [feedbackIntro, setFeedbackIntro]       = useState('');
  const [feedbackDesc, setFeedbackDesc]         = useState('');
  const [formFields, setFormFields]             = useState<FeedbackField[]>([]);
  const [faqs, setFaqs]                         = useState<FAQ[]>([]);
  const [ctaLabel, setCtaLabel]                 = useState('');
  const [ctaUrl, setCtaUrl]                     = useState('');
  const [countries, setCountries]               = useState<CountryOption[]>([]);

  const [formValues, setFormValues]   = useState<Record<string, string>>({});
  const [formErrors, setFormErrors]   = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting]   = useState(false);
  const [submitted, setSubmitted]     = useState(false);
  const [openFaq, setOpenFaq]         = useState<number | null>(null);

  useEffect(() => {
    fetch(`/api/catalog/projects/${slug}/config/`)
      .then((r) => r.json())
      .then((data) => {
        setFeedbackTitle(data.feedback_title ?? '');
        setFeedbackIntro(data.feedback_intro ?? '');
        setFeedbackDesc(data.feedback_description ?? '');
        setCtaLabel(data.partners_cta_label ?? '');
        setCtaUrl(data.partners_cta_url ?? '');
        setFaqs(data.faqs ?? []);
        const fields: FeedbackField[] = data.feedback_form_fields ?? [];
        setFormFields(fields);
        const initial: Record<string, string> = {};
        fields.forEach((f) => { initial[f.label] = ''; });
        setFormValues(initial);
      })
      .catch(() => {});

    fetch(`/api/catalog/projects/${slug}/countries/`)
      .then((r) => r.json())
      .then((data: CountryOption[]) => setCountries(data))
      .catch(() => {});
  }, [slug]);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormErrors({});
    setSubmitError('');
    setSubmitting(true);
    try {
      const res = await fetch(`/api/catalog/projects/${slug}/feedback/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formValues),
      });
      const data = await res.json();
      if (res.ok) {
        setSubmitted(true);
      } else if (data.errors) {
        setFormErrors(data.errors);
      } else {
        setSubmitError(data.detail ?? t.submitError);
      }
    } catch {
      setSubmitError(t.submitError);
    }
    setSubmitting(false);
  }

  function handleChange(label: string, value: string) {
    setFormValues((prev) => ({ ...prev, [label]: value }));
    if (formErrors[label]) {
      setFormErrors((prev) => { const n = { ...prev }; delete n[label]; return n; });
    }
  }

  function renderField(f: FeedbackField) {
    const base = inputStyle;
    const error = formErrors[f.label];

    if (f.field_type === 'textarea') {
      return (
        <textarea
          rows={4}
          placeholder={f.placeholder}
          value={formValues[f.label] ?? ''}
          onChange={(e) => handleChange(f.label, e.target.value)}
          style={{ ...base, resize: 'vertical' }}
        />
      );
    }

    if (f.field_type === 'country_select') {
      return (
        <select
          value={formValues[f.label] ?? ''}
          onChange={(e) => handleChange(f.label, e.target.value)}
          style={base}
        >
          <option value="">{t.selectDefault}</option>
          {countries.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      );
    }

    if (f.field_type === 'topic_select') {
      return (
        <select
          value={formValues[f.label] ?? ''}
          onChange={(e) => handleChange(f.label, e.target.value)}
          style={base}
        >
          <option value="">{t.selectDefault}</option>
          {f.choices.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      );
    }

    return (
      <input
        type={f.field_type}
        placeholder={f.placeholder}
        value={formValues[f.label] ?? ''}
        onChange={(e) => handleChange(f.label, e.target.value)}
        style={{ ...base, borderColor: error ? '#f87171' : '#d1d5db' }}
      />
    );
  }

  // Group into rows: pair consecutive text/email fields, keep others full-width
  function buildRows(fields: FeedbackField[]): Array<FeedbackField[]> {
    const rows: Array<FeedbackField[]> = [];
    let i = 0;
    while (i < fields.length) {
      const f = fields[i];
      const next = fields[i + 1];
      const isInlineable = (x: FeedbackField) => x.field_type === 'text' || x.field_type === 'email';
      if (isInlineable(f) && next && isInlineable(next)) {
        rows.push([f, next]);
        i += 2;
      } else {
        rows.push([f]);
        i += 1;
      }
    }
    return rows;
  }

  const rows = buildRows(formFields);
  const hasFaqs = faqs.length > 0;

  return (
    <div style={{ overflowY: 'auto', height: '100%', backgroundColor: '#f9fafb' }}>

      {/* ── Page header ── */}
      <div style={{ backgroundColor: 'white', padding: '40px 48px', borderBottom: '1px solid #e5e7eb' }}>
        {feedbackTitle && (
          <>
            <h1 style={{ fontSize: 'clamp(1.6rem, 3vw, 2rem)', fontWeight: 800, color: '#111827', marginBottom: 10 }}>
              {feedbackTitle}
            </h1>
            <div style={{ width: 44, height: 3, backgroundColor: '#16803d', borderRadius: 2, marginBottom: 16 }} />
          </>
        )}
        {feedbackIntro && (
          <p style={{ fontSize: 15, fontWeight: 700, color: '#111827', marginBottom: 6 }}>{feedbackIntro}</p>
        )}
        {feedbackDesc && (
          <p style={{ fontSize: 13, color: '#6b7280', margin: 0 }}>{feedbackDesc}</p>
        )}
      </div>

      {/* ── Two-column main ── */}
      <div style={{ display: 'grid', gridTemplateColumns: hasFaqs ? '1fr 1fr' : '1fr', gap: 24, padding: '32px 48px' }}>

        {/* Left: feedback form */}
        <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: 12, padding: '28px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
            <MessageSquare style={{ width: 20, height: 20, color: '#16803d' }} />
            <h2 style={{ fontSize: 15, fontWeight: 700, color: '#111827', margin: 0 }}>{t.sendFeedback}</h2>
          </div>

          {submitted ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: '32px 0', textAlign: 'center' }}>
              <CheckCircle style={{ width: 48, height: 48, color: '#16803d' }} />
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#111827', margin: 0 }}>{t.successTitle}</h3>
              <p style={{ fontSize: 13, color: '#6b7280', margin: 0, maxWidth: 340 }}>{t.successSub}</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              {rows.map((row, ri) => (
                <div
                  key={ri}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: row.length === 2 ? '1fr 1fr' : '1fr',
                    gap: 16,
                    marginBottom: 16,
                  }}
                >
                  {row.map((f) => (
                    <div key={f.label}>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 5 }}>
                        {f.label}
                        {f.required && <span style={{ color: '#ef4444', marginLeft: 2 }}>{t.required}</span>}
                      </label>
                      {renderField(f)}
                      {formErrors[f.label] && (
                        <p style={{ fontSize: 11, color: '#ef4444', margin: '4px 0 0' }}>{formErrors[f.label]}</p>
                      )}
                    </div>
                  ))}
                </div>
              ))}

              <button
                type="submit"
                disabled={submitting}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: 8,
                  border: 'none',
                  backgroundColor: '#16803d',
                  color: 'white',
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: submitting ? 'wait' : 'pointer',
                  opacity: submitting ? 0.75 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  marginTop: 8,
                }}
              >
                <Send style={{ width: 15, height: 15 }} />
                {submitting ? t.submitting : t.submit}
              </button>

              {submitError && (
                <p style={{ fontSize: 12, color: '#dc2626', marginTop: 10, padding: '8px 12px', background: '#fef2f2', borderRadius: 6 }}>
                  {submitError}
                </p>
              )}

              <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Lock style={{ width: 11, height: 11 }} />
                {t.privacyNote}
              </p>
            </form>
          )}
        </div>

        {/* Right: FAQ accordion */}
        {hasFaqs && (
          <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: 12, padding: '28px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <HelpCircle style={{ width: 20, height: 20, color: '#16803d' }} />
              <h2 style={{ fontSize: 15, fontWeight: 700, color: '#111827', margin: 0 }}>{t.faqTitle}</h2>
            </div>
            <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 20 }}>{t.faqSub}</p>

            {faqs.map((faq, i) => (
              <div key={i} style={{ borderTop: i === 0 ? '1px solid #e5e7eb' : 'none' }}>
                <button
                  type="button"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 0',
                    background: 'none',
                    border: 'none',
                    borderBottom: '1px solid #e5e7eb',
                    cursor: 'pointer',
                    textAlign: 'left',
                    gap: 8,
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: openFaq === i ? 700 : 500, color: openFaq === i ? '#16803d' : '#111827' }}>
                    {faq.question}
                  </span>
                  {openFaq === i
                    ? <ChevronUp style={{ width: 16, height: 16, color: '#16803d', flexShrink: 0 }} />
                    : <ChevronDown style={{ width: 16, height: 16, color: '#6b7280', flexShrink: 0 }} />
                  }
                </button>
                {openFaq === i && (
                  <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.65, padding: '12px 0 16px', margin: 0, borderBottom: '1px solid #e5e7eb' }}>
                    {faq.answer}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Support bar ── */}
      <div style={{ margin: '0 48px 40px', backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: 12, padding: '24px 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 44, height: 44, borderRadius: '50%', backgroundColor: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Headphones style={{ width: 22, height: 22, color: '#16803d' }} />
          </div>
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: '#111827', marginBottom: 4 }}>{t.supportTitle}</h3>
            <p style={{ fontSize: 13, color: '#6b7280', margin: 0 }}>{t.supportSub}</p>
          </div>
        </div>
        {ctaUrl && (
          <a
            href={ctaUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '10px 20px', borderRadius: 8,
              border: '1.5px solid #16803d', color: '#16803d',
              fontSize: 13, fontWeight: 700, textDecoration: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            <Mail style={{ width: 14, height: 14 }} />
            {ctaLabel || t.contactFallback}
            <ExternalLink style={{ width: 13, height: 13 }} />
          </a>
        )}
      </div>

    </div>
  );
}
