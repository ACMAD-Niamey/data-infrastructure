import type { CatalogLayer } from "../types/catalogLayer";

export function inferCategory(layer: CatalogLayer): string {
  const t = layer.title.toLowerCase();
  if (layer.hazard_category) return layer.hazard_category;
  if (t.includes('drought') || t.includes('soil moisture') || t.includes('sma') || t.includes('cdi') || t.includes('spi')) return 'drought';
  if (t.includes('flood') || t.includes('river')) return 'flood';
  if (t.includes('rain') || t.includes('weather') || t.includes('precipitation') || t.includes('forecast')) return 'weather';
  if (t.includes('heat') || t.includes('temperature') || t.includes('lst')) return 'heat';
  if (t.includes('vegetation') || t.includes('ndvi') || t.includes('crop') || t.includes('agriculture')) return 'agriculture';
  if (t.includes('boundary') || t.includes('admin') || t.includes('country')) return 'boundary';
  return 'other';
}
