export function formatDurationHMS(startTs: number | null | undefined, endTs: number | null | undefined): string {
  if (!startTs || !endTs) return "—";
  const totalSeconds = Math.max(0, Math.floor(endTs - startTs));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const hh = String(hours).padStart(2, "0");
  const mm = String(minutes).padStart(2, "0");
  const ss = String(seconds).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function toNumber(raw: string): number {
  return Number(raw.replace(/,/g, ""));
}

export function extractJobRecordCounts(log: string): { recordsIn: number | null; recordsOut: number | null } {
  if (!log) return { recordsIn: null, recordsOut: null };

  const filtered = log.match(/Filtered\s+from\s+(\d[\d,]*)\s+to\s+(\d[\d,]*)\s+rows/i);
  if (filtered) {
    return {
      recordsIn: toNumber(filtered[1]),
      recordsOut: toNumber(filtered[2]),
    };
  }

  const fileCounts = Array.from(log.matchAll(/[A-Za-z ]+file:?\s*(\d[\d,]*)/gi)).map((m) => toNumber(m[1]));
  const processedRows = Array.from(log.matchAll(/Processed\s+(\d[\d,]*)\s+rows/gi)).map((m) => toNumber(m[1]));

  const labeledCounts = Array.from(
    log.matchAll(/([A-Za-z][A-Za-z ]+):\s*(\d[\d,]*)\s*(records|rows)/gi)
  ).map((m) => ({
    label: m[1].toLowerCase(),
    value: toNumber(m[2]),
  }));

  const outCandidate = labeledCounts
    .filter((c) => /(final|template|consolidated|output|result|combined|cleaned|merged)/i.test(c.label))
    .at(-1)?.value;

  const genericLastCount = labeledCounts.at(-1)?.value ?? null;

  const recordsIn =
    fileCounts.length > 0
      ? Math.max(...fileCounts)
      : processedRows.length > 0
      ? processedRows[0]
      : labeledCounts.length > 0
      ? labeledCounts[0].value
      : null;

  const processedOut = processedRows.length > 0 ? processedRows[processedRows.length - 1] : null;

  const recordsOut =
    outCandidate ??
    processedOut ??
    genericLastCount;

  return { recordsIn, recordsOut };
}
