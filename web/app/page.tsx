"use client";

import { useMemo, useState } from "react";

type Extracted = {
  patient_name: string;
  payer_name: string;
  provider_name: string;
  date_of_service: string;
  claim_id: string;
  procedure_code: string;
  denial_code: string;
  denial_reason: string;
  amount_billed: string;
  amount_denied: string;
};

type ApiResponse = {
  extracted: Extracted;
  narrative: string;
  appeal_text: string;
  pdf_available?: boolean;
};

const EMPTY_EXTRACTED: Extracted = {
  patient_name: "",
  payer_name: "",
  provider_name: "",
  date_of_service: "",
  claim_id: "",
  procedure_code: "",
  denial_code: "",
  denial_reason: "",
  amount_billed: "",
  amount_denied: "",
};

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [useAi, setUseAi] = useState(false);
  const [loading, setLoading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [pdfAvailable, setPdfAvailable] = useState(false);
  const [clinicId, setClinicId] = useState("");

  const apiBase = useMemo(() => {
    return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  }, []);

  const canSubmit = file && !loading;

  const handleSubmit = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setData(null);

    const form = new FormData();
    form.append("file", file);
    form.append("use_ai", useAi ? "true" : "false");
    if (clinicId.trim()) {
      form.append("clinic_id", clinicId.trim());
    }

    try {
      const response = await fetch(`${apiBase}/api/appeals`, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Upload failed");
      }

      const json = (await response.json()) as ApiResponse;
      setData(json);
      setPdfAvailable(Boolean(json.pdf_available));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unexpected error";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const downloadText = () => {
    if (!data) return;
    const blob = new Blob([data.appeal_text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "appeal_packet.txt";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const downloadPdf = async () => {
    if (!file || !pdfAvailable) return;
    setDownloadingPdf(true);
    setError(null);

    const form = new FormData();
    form.append("file", file);
    form.append("use_ai", useAi ? "true" : "false");
    if (clinicId.trim()) {
      form.append("clinic_id", clinicId.trim());
    }

    try {
      const response = await fetch(`${apiBase}/api/appeals/pdf`, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "PDF generation failed");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "appeal_packet.pdf";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unexpected error";
      setError(message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const extracted = data?.extracted ?? EMPTY_EXTRACTED;

  return (
    <main className="relative min-h-screen overflow-hidden px-6 pb-24 pt-16 text-ink sm:px-10">
      <div className="pointer-events-none absolute -top-24 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-copper/20 blur-3xl" />
      <div className="pointer-events-none absolute right-10 top-32 h-64 w-64 rounded-full bg-ocean/20 blur-3xl" />

      <section className="mx-auto flex w-full max-w-5xl flex-col items-center gap-4 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-line bg-parchment px-4 py-1 text-xs font-medium uppercase tracking-[0.2em] text-haze">
          Active payer
          <span className="h-1.5 w-1.5 rounded-full bg-copper" />
          Delta Dental PPO
        </div>
        <h1 className="text-balance font-serif text-4xl sm:text-5xl lg:text-6xl">
          USDENT Appeal Builder
        </h1>
        <p className="max-w-2xl text-balance text-base text-haze sm:text-lg">
          Upload an EOB, confirm extracted data, and deliver a ready-to-send appeal packet in minutes.
        </p>
      </section>

      <section className="mx-auto mt-12 w-full max-w-5xl rounded-3xl border border-line bg-parchment p-6 shadow-card sm:p-10">
        <div className="grid gap-6">
          <label className="flex flex-col gap-4 rounded-2xl border border-dashed border-copper/70 bg-white/90 p-6 text-sm text-haze">
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-copper">EOB Upload</span>
            <span className="text-lg font-medium text-ink">
              Drag a file here or browse to select.
            </span>
            <span className="text-xs">PDF, JPG, PNG, or TXT accepted.</span>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              className="text-sm"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>

          <div className="flex flex-wrap items-center gap-4">
            <label className="flex flex-col gap-2 text-xs uppercase tracking-[0.2em] text-haze">
              Clinic ID (optional)
              <input
                type="text"
                value={clinicId}
                onChange={(event) => setClinicId(event.target.value)}
                placeholder="e.g. clinic_alpha"
                className="rounded-full border border-line bg-white px-4 py-2 text-sm normal-case tracking-normal text-ink"
              />
            </label>
            <label className="flex items-center gap-3 rounded-full border border-line bg-white px-4 py-2 text-sm">
              <span className="text-haze">AI narrative</span>
              <input
                type="checkbox"
                checked={useAi}
                onChange={(event) => setUseAi(event.target.checked)}
                className="h-4 w-4 accent-copper"
              />
            </label>
            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="rounded-full bg-copper px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-copper/20 transition hover:-translate-y-0.5 disabled:opacity-60"
            >
              {loading ? "Processing..." : "Generate Appeal"}
            </button>
            <button
              className="rounded-full border border-ocean px-6 py-3 text-sm font-semibold text-ocean transition hover:-translate-y-0.5 disabled:opacity-60"
              onClick={downloadText}
              disabled={!data}
            >
              Download Appeal
            </button>
            <button
              className="rounded-full border border-line bg-white px-6 py-3 text-sm font-semibold text-ink transition hover:-translate-y-0.5 disabled:opacity-60"
              onClick={downloadPdf}
              disabled={!file || !pdfAvailable || downloadingPdf}
            >
              {downloadingPdf ? "Preparing PDF..." : "Download ADA PDF"}
            </button>
          </div>

          {!pdfAvailable && data ? (
            <div className="text-xs text-haze">
              ADA template not configured. Set USDENT_ADA_TEMPLATE to enable PDF output.
            </div>
          ) : null}

          {error ? <div className="text-sm text-red-600">Error: {error}</div> : null}
          {loading ? (
            <div className="text-sm text-haze">Extracting fields and building narrative...</div>
          ) : null}
        </div>
      </section>

      <section className="mx-auto mt-10 w-full max-w-5xl rounded-3xl border border-line bg-white p-6 shadow-card sm:p-10">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="font-serif text-2xl">Extracted Fields</h2>
          <span className="text-xs uppercase tracking-[0.2em] text-haze">Preview</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { label: "Patient", value: extracted.patient_name },
            { label: "Payer", value: extracted.payer_name },
            { label: "Provider", value: extracted.provider_name },
            { label: "Date of Service", value: extracted.date_of_service },
            { label: "Claim ID", value: extracted.claim_id },
            { label: "Procedure", value: extracted.procedure_code },
            { label: "Denial Code", value: extracted.denial_code },
            { label: "Denial Reason", value: extracted.denial_reason },
            { label: "Amount Billed", value: extracted.amount_billed },
            { label: "Amount Denied", value: extracted.amount_denied },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-line bg-parchment p-4"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-haze">
                {item.label}
              </p>
              <p className="mt-2 text-base font-medium text-ink">{item.value || "-"}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto mt-10 w-full max-w-5xl rounded-3xl border border-line bg-parchment p-6 shadow-card sm:p-10">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="font-serif text-2xl">Narrative Preview</h2>
          <button className="text-sm text-ocean underline-offset-4 hover:underline">Edit</button>
        </div>
        <div className="rounded-2xl bg-white p-6 text-sm leading-relaxed text-ink">
          {data?.narrative || "Generate an appeal to see the narrative here."}
        </div>
      </section>

      <div className="mx-auto mt-12 max-w-5xl text-center text-xs text-haze">
        Prototype UI for internal MVP testing. PHI should not be stored outside approved systems.
      </div>
    </main>
  );
}
