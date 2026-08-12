export type Selection =
  | { type: 'overview' }
  | { type: 'builder' }
  | { type: 'operation'; operationId: string };
