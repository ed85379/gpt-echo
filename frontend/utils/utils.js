// Generates a canonical message_id using SHA-256
export async function assignMessageId({ timestamp, role, source, message }) {
  const base = [timestamp, role, source, message].join('|');
  const encoder = new TextEncoder();
  const data = encoder.encode(base);
  const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
}