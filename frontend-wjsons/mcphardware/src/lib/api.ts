export async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
const res = await fetch(url, { ...init, headers: { 'content-type': 'application/json', ...(init?.headers||{}) } });
if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
return res.json();
}


export type Tool = {
name: string;
description?: string;
input_schema?: any;
scopes?: string[];
};