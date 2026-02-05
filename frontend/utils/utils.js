// Generates a canonical message_id using SHA-256
export async function assignMessageId({ timestamp, role, source, message }) {
  const base = [timestamp, role, source, message].join('|');
  const encoder = new TextEncoder();
  const data = encoder.encode(base);
  const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
}

export function toPythonIsoString(date = new Date()) {
  // Pad milliseconds if needed
  const pad = (n, width = 2) => n.toString().padStart(width, '0');
  const yyyy = date.getUTCFullYear();
  const mm = pad(date.getUTCMonth() + 1);
  const dd = pad(date.getUTCDate());
  const hh = pad(date.getUTCHours());
  const min = pad(date.getUTCMinutes());
  const ss = pad(date.getUTCSeconds());
  const ms = pad(date.getUTCMilliseconds(), 3);

  // If you want microseconds, append '000' or use a polyfill
  return `${yyyy}-${mm}-${dd}T${hh}:${min}:${ss}.${ms}000+00:00`;
}

export async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () =>
      resolve(reader.result.split(',')[1]); // Strips the data:...;base64, prefix
    reader.onerror = error => reject(error);
    reader.readAsDataURL(file);
  });
}

export function trimMessages(arr, limit) {
  return arr.slice(-limit);
}

// This function does not appear to be in use //
export function Paragraph({ children }) {
  // If the child is a <pre>, render it directly, don't wrap in <p>
  if (
    children &&
    React.Children.count(children) === 1 &&
    children[0]?.type === "pre"
  ) {
    return children[0];
  }
  return <p>{children}</p>;
}

// Helper for pretty file sizes //
export function humanFileSize(bytes) {
  const thresh = 1024;
  if (Math.abs(bytes) < thresh) return bytes + " B";
  const units = ["KB", "MB", "GB", "TB"];
  let u = -1;
  do {
    bytes /= thresh;
    ++u;
  } while (Math.abs(bytes) >= thresh && u < units.length - 1);
  return bytes.toFixed(1) + " " + units[u];
}

export function getMonthRange(date) {
  // Current month and year
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth();

  // Previous month (handle January rollover)
  const prevMonth = month === 0 ? 11 : month - 1;
  const prevYear = month === 0 ? year - 1 : year;

  // Start: first of previous month
  const start = `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-01`;

  // End: last of current month
  const firstOfNextMonth = new Date(Date.UTC(year, month + 1, 1));
  const lastOfMonth = new Date(firstOfNextMonth.getTime() - 24 * 3600 * 1000);
  const end = `${lastOfMonth.getUTCFullYear()}-${String(lastOfMonth.getUTCMonth() + 1).padStart(2, '0')}-${String(lastOfMonth.getUTCDate()).padStart(2, '0')}`;

  return { start, end };
}