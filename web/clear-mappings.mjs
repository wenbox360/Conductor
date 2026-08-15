#!/usr/bin/env node

import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const mappingsPath = join(scriptDirectory, '..', 'registry-server', 'mappings.json');

try {
  writeFileSync(mappingsPath, '[]', 'utf8');
  console.log('✅ Cleared mappings.json for fresh start');
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.warn('⚠️  Could not clear mappings.json:', message);
}
