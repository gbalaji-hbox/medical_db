import type { Module } from "@/api/types";

function formatDateDDMMYYYY(d: Date): string {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = String(d.getFullYear());
  return `${dd}${mm}${yyyy}`;
}

export function consolidatedDownloadFilename(
  module: Module,
  unixSeconds?: number | null
): string {
  const date = unixSeconds ? new Date(unixSeconds * 1000) : new Date();
  return `${module}_consolidated_${formatDateDDMMYYYY(date)}.xlsx`;
}
