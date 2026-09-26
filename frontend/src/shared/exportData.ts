function downloadBlob(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function downloadAsJson(filename: string, data: unknown): void {
  downloadBlob(filename, JSON.stringify(data, null, 2), "application/json");
}

export function downloadAsCsv<T extends Record<string, unknown>>(filename: string, rows: T[]): void {
  if (rows.length === 0) {
    downloadBlob(filename, "", "text/csv");
    return;
  }

  const headers = Object.keys(rows[0]);
  const escapeCell = (value: unknown): string => {
    const text = Array.isArray(value) ? value.join("; ") : String(value ?? "");
    return `"${text.replace(/"/g, '""')}"`;
  };

  const lines = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => escapeCell(row[header])).join(",")),
  ];

  downloadBlob(filename, lines.join("\n"), "text/csv");
}
