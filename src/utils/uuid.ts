/**
 * @file uuid.ts
 * Minimal UUID v4 generator with zero npm dependencies.
 * Uses Node's crypto.randomUUID() (available since Node 14.17 / 16+,
 * which VS Code ships with) with a Math.random() fallback.
 */

import * as crypto from 'crypto';

/**
 * Generate a RFC 4122 version 4 UUID.
 * @returns A string like "550e8400-e29b-41d4-a716-446655440000"
 */
export function generateUUID(): string {
  // Node 14.17+ / 16+ has crypto.randomUUID()
  if (typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  // Fallback: manual UUID v4 from random bytes
  const bytes = crypto.randomBytes(16);

  // Set version (4) and variant (RFC 4122)
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10

  const hex = bytes.toString('hex');
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20, 32),
  ].join('-');
}
