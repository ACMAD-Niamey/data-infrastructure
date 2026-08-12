import { useEffect, useRef, useState } from 'react';
import ReCAPTCHA from 'react-google-recaptcha';
import {
  MessageSquare, HelpCircle, ChevronDown, ChevronUp,
  Send, Lock, Mail, ExternalLink, CheckCircle, Headphones,
} from 'lucide-react';
import NavBar from '../components/NavBar';
import {
  fetchProjectConfig, fetchProjectCountries, getProjectSlug, submitProjectFeedback,
  type FeedbackFormField, type FAQ, type CountryOption,
} from '../services/catalogLayersApi';

const inputClass =
  'w-full px-3 py-2.5 rounded-md border border-gray-300 text-sm text-gray-900 outline-none bg-white focus:border-hub-400 focus:ring-1 focus:ring-hub-400';

export default function Feedback() {
  const slug = getProjectSlug();

  const [feedbackTitle, setFeedbackTitle] = useState('');
  const [feedbackIntro, setFeedbackIntro] = useState('');
  const [feedbackDesc, setFeedbackDesc] = useState('');
  const [formFields, setFormFields] = useState<FeedbackFormField[]>([]);
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [ctaLabel, setCtaLabel] = useState('');
  const [ctaUrl, setCtaUrl] = useState('');
  const [countries, setCountries] = useState<CountryOption[]>([]);

  const [recaptchaSiteKey, setRecaptchaSiteKey] = useState('');
  const recaptchaRef = useRef<ReCAPTCHA>(null);

  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [captchaError, setCaptchaError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  useEffect(() => {
    fetchProjectConfig(slug)
      .then((data) => {
        setFeedbackTitle(data.feedback_title ?? '');
        setFeedbackIntro(data.feedback_intro ?? '');
        setFeedbackDesc(data.feedback_description ?? '');
        setRecaptchaSiteKey(data.recaptcha_site_key ?? '');
        setCtaLabel(data.partners_cta_label ?? '');
        setCtaUrl(data.partners_cta_url ?? '');
        setFaqs(data.faqs ?? []);
        const fields = data.feedback_form_fields ?? [];
        setFormFields(fields);
        const initial: Record<string, string> = {};
        fields.forEach((f) => { initial[f.label] = ''; });
        setFormValues(initial);
      })
      .catch(() => {});

    fetchProjectCountries(slug)
      .then(setCountries)
      .catch(() => {});
  }, [slug]);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormErrors({});
    setSubmitError('');
    setCaptchaError('');

    if (recaptchaSiteKey && !recaptchaRef.current?.getValue()) {
      setCaptchaError('Please complete the CAPTCHA before submitting.');
      return;
    }

    setSubmitting(true);
    const payload = {
      ...formValues,
      ...(recaptchaSiteKey ? { recaptcha_token: recaptchaRef.current?.getValue() ?? '' } : {}),
    };
    const result = await submitProjectFeedback(slug, payload);
    if (result.ok) {
      setSubmitted(true);
      recaptchaRef.current?.reset();
    } else if (result.errors) {
      setFormErrors(result.errors);
      recaptchaRef.current?.reset();
    } else {
      setSubmitError(result.detail ?? 'Submission failed. Please try again.');
      recaptchaRef.current?.reset();
    }
    setSubmitting(false);
  }

  function handleChange(label: string, value: string) {
    setFormValues((prev) => ({ ...prev, [label]: value }));
    if (formErrors[label]) {
      setFormErrors((prev) => { const n = { ...prev }; delete n[label]; return n; });
    }
  }

  function renderField(f: FeedbackFormField) {
    const error = formErrors[f.label];

    if (f.field_type === 'textarea') {
      return (
        <textarea
          rows={4}
          placeholder={f.placeholder}
          value={formValues[f.label] ?? ''}
          onChange={(e) => handleChange(f.label, e.target.value)}
          className={`${inputClass} resize-y`}
        />
      );
    }

    if (f.field_type === 'country_select') {
      return (
        <select
          value={formValues[f.label] ?? ''}
          onChange={(e) => handleChange(f.label, e.target.value)}
          className={inputClass}
        >
          <option value="">— Select —</option>
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
          className={inputClass}
        >
          <option value="">— Select —</option>
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
        className={`${inputClass} ${error ? 'border-red-400' : ''}`}
      />
    );
  }

  // Group into rows: pair consecutive text/email fields, keep others full-width
  function buildRows(fields: FeedbackFormField[]): Array<FeedbackFormField[]> {
    const rows: Array<FeedbackFormField[]> = [];
    let i = 0;
    while (i < fields.length) {
      const f = fields[i];
      const next = fields[i + 1];
      const isInlineable = (x: FeedbackFormField) => x.field_type === 'text' || x.field_type === 'email';
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
  const hasForm = formFields.length > 0;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <NavBar />

      {/* Page header */}
      <div className="bg-white border-b border-gray-200 px-6 md:px-12 py-10">
        {feedbackTitle && (
          <>
            <h1 className="text-2xl md:text-3xl font-extrabold text-hub-800 mb-2.5">{feedbackTitle}</h1>
            <div className="w-11 h-[3px] bg-hub-400 rounded mb-4" />
          </>
        )}
        {feedbackIntro && <p className="text-sm font-bold text-gray-900 mb-1.5">{feedbackIntro}</p>}
        {feedbackDesc && <p className="text-sm text-gray-500">{feedbackDesc}</p>}
      </div>

      <div className={`grid gap-6 px-6 md:px-12 py-8 ${hasFaqs ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
        {/* Feedback form */}
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-6">
            <MessageSquare className="size-5 text-hub-400" />
            <h2 className="text-sm font-bold text-gray-900">Send feedback</h2>
          </div>

          {!hasForm ? (
            <p className="text-sm text-gray-400">No feedback form is configured for this project yet.</p>
          ) : submitted ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <CheckCircle className="size-12 text-hub-400" />
              <h3 className="text-sm font-bold text-gray-900">Thank you for your feedback!</h3>
              <p className="text-sm text-gray-500 max-w-xs">
                Your message has been received and will help us improve the Multi-Hazard Hub.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              {rows.map((row, ri) => (
                <div
                  key={ri}
                  className={`grid gap-4 mb-4 ${row.length === 2 ? 'grid-cols-2' : 'grid-cols-1'}`}
                >
                  {row.map((f) => (
                    <div key={f.label}>
                      <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                        {f.label}
                        {f.required && <span className="text-red-500 ml-0.5">*</span>}
                      </label>
                      {renderField(f)}
                      {formErrors[f.label] && (
                        <p className="text-[11px] text-red-500 mt-1">{formErrors[f.label]}</p>
                      )}
                    </div>
                  ))}
                </div>
              ))}

              {recaptchaSiteKey && (
                <div className="mb-3">
                  <ReCAPTCHA ref={recaptchaRef} sitekey={recaptchaSiteKey} theme="light" />
                  {captchaError && <p className="text-red-600 text-xs mt-1.5">{captchaError}</p>}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-bold text-white bg-hub-800 hover:bg-hub-700 transition-colors disabled:opacity-75 disabled:cursor-wait mt-2"
              >
                <Send className="size-3.5" />
                {submitting ? 'Submitting…' : 'Submit feedback'}
              </button>

              {submitError && (
                <p className="text-xs text-red-600 mt-2.5 px-3 py-2 bg-red-50 rounded-md">{submitError}</p>
              )}

              <p className="text-[11px] text-gray-400 mt-3 flex items-center gap-1.5">
                <Lock className="size-3" />
                We value your privacy. Your feedback will only be used to improve the Multi-Hazard Hub.
              </p>
            </form>
          )}
        </div>

        {/* FAQ accordion */}
        {hasFaqs && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-1.5">
              <HelpCircle className="size-5 text-hub-400" />
              <h2 className="text-sm font-bold text-gray-900">FAQ</h2>
            </div>
            <p className="text-xs text-gray-500 mb-5">Frequently asked questions</p>

            {faqs.map((faq, i) => (
              <div key={i} className={i === 0 ? 'border-t border-gray-200' : ''}>
                <button
                  type="button"
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between gap-2 py-3.5 border-b border-gray-200 text-left"
                >
                  <span className={`text-[13px] ${openFaq === i ? 'font-bold text-hub-700' : 'font-medium text-gray-900'}`}>
                    {faq.question}
                  </span>
                  {openFaq === i
                    ? <ChevronUp className="size-4 text-hub-400 shrink-0" />
                    : <ChevronDown className="size-4 text-gray-400 shrink-0" />}
                </button>
                {openFaq === i && (
                  <p className="text-[13px] text-gray-700 leading-relaxed py-3 border-b border-gray-200">
                    {faq.answer}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Support bar */}
      <div className="mx-6 md:mx-12 mb-10 bg-white border border-gray-200 rounded-xl px-7 py-6 flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-4">
          <div className="size-11 rounded-full bg-hub-100 flex items-center justify-center shrink-0">
            <Headphones className="size-5.5 text-hub-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-900 mb-1">Need direct support?</h3>
            <p className="text-[13px] text-gray-500">
              Our team is ready to help with technical questions or data access.
            </p>
          </div>
        </div>
        {ctaUrl && (
          <a
            href={ctaUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border-[1.5px] border-hub-400 text-hub-700 text-[13px] font-bold whitespace-nowrap hover:bg-hub-100 transition-colors"
          >
            <Mail className="size-3.5" />
            {ctaLabel || 'Contact us'}
            <ExternalLink className="size-3.5" />
          </a>
        )}
      </div>
    </div>
  );
}
