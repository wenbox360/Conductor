#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Path to mappings file
const mappingsPath = path.join(__dirname, '..', 'registry-server', 'mappings.json');

try {
  // Clear mappings to empty array
  fs.writeFileSync(mappingsPath, '[]', 'utf8');
  console.log('✅ Cleared mappings.json for fresh start');
} catch (error) {
  console.warn('⚠️  Could not clear mappings.json:', error.message);
}
