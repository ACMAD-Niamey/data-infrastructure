import axios from "axios";
import { catalogBaseUrl } from "../config/api";
import { deriveSelectors } from "../lib/cadenceSelectors";
import type { CatalogLayer } from "../types/catalogLayer";

export type UILayersResponse = {
  version: string;
  project: string;
  layers: Array<
    Omit<CatalogLayer, "selectors" | "labels"> & {
      description: { html: string; plain: string };
    }
  >;
};

const client = axios.create({
  baseURL: catalogBaseUrl,
  timeout: 15000,
});

function enrichLayer(raw: UILayersResponse["layers"][number]): CatalogLayer {
  const cadence = raw.dataset.cadence;
  return {
    ...raw,
    selectors: deriveSelectors(cadence, "en"),
    labels: {
      title: { en: raw.title, fr: raw.title },
      description: { en: raw.description.plain, fr: raw.description.plain },
    },
  };
}

export async function fetchProjectLayers(
  projectSlug: string,
  options: { requireIcon?: boolean } = {},
): Promise<CatalogLayer[]> {
  const { requireIcon = true } = options;
  const response = await client.get<UILayersResponse>("/api/catalog/ui/layers", {
    params: { project: projectSlug },
  });
  const layers = response.data.layers || [];
  return (requireIcon ? layers.filter((layer) => layer.icon?.url) : layers).map(enrichLayer);
}

export function getProjectSlug(): string {
  const viteEnv = import.meta.env as { VITE_PROJECT_SLUG?: string };
  return (viteEnv.VITE_PROJECT_SLUG || "multi-hazard").trim();
}

export type FeedbackFormField = {
  label: string;
  field_type: "text" | "email" | "textarea" | "country_select" | "topic_select";
  required: boolean;
  placeholder: string;
  choices: string[];
};

export type FAQ = {
  question: string;
  answer: string;
};

export type CountryOption = {
  value: string;
  label: string;
  bounds: { west: number; south: number; east: number; north: number };
};

export type ContactFormField = {
  label: string;
  field_type: "text" | "email" | "textarea";
  required: boolean;
  placeholder: string;
};

export type Partner = {
  role: string;
  logo_url: string | null;
  name: string;
  description: string;
  website_url: string;
};

export type ProjectConfig = {
  data_platforms_title: string;
  data_platforms_description: string;
  data_platforms_image_url: string | null;
  feedback_title: string;
  feedback_intro: string;
  feedback_description: string;
  recaptcha_site_key: string;
  feedback_form_fields: FeedbackFormField[];
  faqs: FAQ[];
  partners_title: string;
  partners_intro: string;
  partners_description: string;
  partners_image_url: string | null;
  partners_cta_label: string;
  partners_cta_url: string;
  partners: Partner[];
  contact_form_fields: ContactFormField[];
};

/** Project-level config (CMS-editable copy/images), same shape shared with e-safari-ui.
 * Only the Data Platforms, Feedback and Partners fields are typed here — the endpoint
 * also returns an "about" section that this app doesn't use yet. */
export async function fetchProjectConfig(projectSlug: string): Promise<ProjectConfig> {
  const response = await client.get<ProjectConfig>(`/api/catalog/projects/${projectSlug}/config/`);
  return response.data;
}

export async function fetchProjectCountries(projectSlug: string): Promise<CountryOption[]> {
  const response = await client.get<CountryOption[]>(`/api/catalog/projects/${projectSlug}/countries/`);
  return response.data;
}

type SubmitResult = { ok: true } | { ok: false; errors?: Record<string, string>; detail?: string };

async function postForm(path: string, payload: Record<string, string>): Promise<SubmitResult> {
  try {
    await client.post(path, payload);
    return { ok: true };
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      const data = err.response.data as { errors?: Record<string, string>; detail?: string };
      return { ok: false, errors: data.errors, detail: data.detail };
    }
    return { ok: false };
  }
}

export function submitProjectFeedback(projectSlug: string, payload: Record<string, string>): Promise<SubmitResult> {
  return postForm(`/api/catalog/projects/${projectSlug}/feedback/`, payload);
}

export function submitProjectContact(projectSlug: string, payload: Record<string, string>): Promise<SubmitResult> {
  return postForm(`/api/catalog/projects/${projectSlug}/contact/`, payload);
}
