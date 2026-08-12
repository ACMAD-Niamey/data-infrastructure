import { catalogBaseUrl } from "../config/api";

export function visualizationEndpointUrl(datasetId: string, cadence: string, date: string): string {
  return `${catalogBaseUrl}/api/catalog/datasets/${datasetId}/visualization/?date=${date}&cadence=${cadence}`;
}

export function availabilityEndpointUrl(datasetId: string, cadence: string): string {
  return `${catalogBaseUrl}/api/catalog/datasets/${datasetId}/availability/?cadence=${cadence}`;
}

export function stacCollectionUrl(stacCollection: string): string {
  return `${catalogBaseUrl}/stac/collections/${stacCollection}`;
}

export function notebookUrl(datasetId: string): string {
  return `${catalogBaseUrl}/api/catalog/datasets/${datasetId}/notebook/`;
}
