export async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { ...init, headers: { 'content-type': 'application/json', ...(init?.headers || {}) } });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}${body ? `: ${body}` : ''}`);
  }
  return res.json();
}

export type SchemaValue = string | number | boolean;

export type ToolInputProperty = {
  title?: string;
  type?: string;
  enum?: Array<string | number>;
  default?: SchemaValue;
  minimum?: number;
  maximum?: number;
};

export type ToolInputSchema = {
  properties?: Record<string, ToolInputProperty>;
  required?: string[];
};

export type Tool = {
  name: string;
  description?: string;
  input_schema?: ToolInputSchema;
  scopes?: string[];
};
