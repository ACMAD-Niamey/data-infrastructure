export type OpenApiParamLocation = 'path' | 'query' | 'header' | 'cookie';

export type OpenApiParameter = {
  name: string;
  in: OpenApiParamLocation;
  required: boolean;
  description?: string;
  schema?: { type?: string; format?: string; enum?: string[] };
};

export type OpenApiOperation = {
  operationId: string;
  method: string;
  path: string;
  summary?: string;
  description?: string;
  tags: string[];
  parameters: OpenApiParameter[];
};

export type OpenApiSubgroup = {
  key: string;
  label: string;
  operations: OpenApiOperation[];
};

export type OpenApiGroup = {
  key: string;
  label: string;
  subgroups: OpenApiSubgroup[];
};

/** Minimal shape of the parts of the raw OpenAPI 3 document this app reads. */
export type RawOpenApiParameter = {
  name: string;
  in: OpenApiParamLocation;
  required?: boolean;
  description?: string;
  schema?: { type?: string; format?: string; enum?: string[] };
};

export type RawOpenApiOperation = {
  operationId?: string;
  summary?: string;
  description?: string;
  tags?: string[];
  parameters?: RawOpenApiParameter[];
};

export type RawOpenApiPathItem = {
  parameters?: RawOpenApiParameter[];
} & Partial<Record<'get' | 'post' | 'put' | 'patch' | 'delete', RawOpenApiOperation>>;

export type RawOpenApiSchema = {
  paths: Record<string, RawOpenApiPathItem>;
};
