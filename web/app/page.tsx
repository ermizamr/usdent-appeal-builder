"use client";

import { useEffect, useMemo, useState } from "react";

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

// Front-desk clinic identity. Entered once, saved in the browser (never sent to
// any account/server to store), and attached to each ADA form request so the
// clinic name, IDs, and a "received" stamp land on the finished form.
type ClinicProfile = {
  clinic_name: string;
  treating_dentist: string;
  clinic_address: string;
  clinic_city_state_zip: string;
  clinic_phone: string;
  clinic_npi: string;
  clinic_license: string;
};

const EMPTY_CLINIC: ClinicProfile = {
  clinic_name: "",
  treating_dentist: "",
  clinic_address: "",
  clinic_city_state_zip: "",
  clinic_phone: "",
  clinic_npi: "",
  clinic_license: "",
};

const CLINIC_STORAGE_KEY = "usdent_clinic_profile";

const CLINIC_FIELDS: { key: keyof ClinicProfile; label: string; placeholder: string }[] = [
  { key: "clinic_name", label: "Practice name", placeholder: "Bright Smile Dental" },
  { key: "treating_dentist", label: "Treating dentist", placeholder: "Dr. Jane Roe, DDS" },
  { key: "clinic_address", label: "Street address", placeholder: "123 Main St" },
  { key: "clinic_city_state_zip", label: "City, State ZIP", placeholder: "Austin, TX 78701" },
  { key: "clinic_phone", label: "Phone", placeholder: "512-555-0100" },
  { key: "clinic_npi", label: "NPI", placeholder: "1234567890" },
  { key: "clinic_license", label: "License #", placeholder: "TX-45678" },
];

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [useAi, setUseAi] = useState(false);
  const [loading, setLoading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [pdfAvailable, setPdfAvailable] = useState(false);
  const [clinicId, setClinicId] = useState("");
  const [clinic, setClinic] = useState<ClinicProfile>(EMPTY_CLINIC);
  const [showClinicForm, setShowClinicForm] = useState(false);

  const apiBase = useMemo(() => {
    return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  }, []);

  // Load the saved clinic profile once, after mount (avoids SSR/localStorage
  // hydration mismatch). Open the form automatically if nothing is saved yet.
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(CLINIC_STORAGE_KEY);
      if (raw) {
        setClinic({ ...EMPTY_CLINIC, ...(JSON.parse(raw) as Partial<ClinicProfile>) });
      } else {
        setShowClinicForm(true);
      }
    } catch {
      setShowClinicForm(true);
    }
  }, []);

  const updateClinic = (key: keyof ClinicProfile, value: string) => {
    setClinic((prev) => {
      const next = { ...prev, [key]: value };
      try {
        window.localStorage.setItem(CLINIC_STORAGE_KEY, JSON.stringify(next));
      } catch {
        // Ignore storage failures (e.g. private mode); the value still applies
        // for this session.
      }
      return next;
    });
  };

  const clinicConfigured = Object.values(clinic).some((value) => value.trim() !== "");

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
    // Attach the saved clinic identity so the ADA form is filled and stamped.
    (Object.keys(clinic) as (keyof ClinicProfile)[]).forEach((key) => {
      const value = clinic[key].trim();
      if (value) form.append(key, value);
    });

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
        <div className="inline-flex items-center gap-2 rounded-full border border-copper/40 bg-copper/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-copper">
          <span className="h-1.5 w-1.5 rounded-full bg-copper" />
          100% Free · No sign-up
        </div>
        <h1 className="text-balance font-serif text-4xl sm:text-5xl lg:text-6xl">
          Free Dental Claim Appeal Builder
        </h1>
        <p className="max-w-2xl text-balance text-base text-haze sm:text-lg">
          Upload an EOB and instantly get a ready-to-send appeal packet plus a filled
          ADA-style claim form — free, with no account or credit card required.
        </p>
        <p className="max-w-2xl text-balance text-sm text-haze/80">
          Built to help dental teams fight denials without paying for expensive billing software.
          Nothing to install, no per-claim fees.
        </p>
      </section>

      <section className="mx-auto mt-10 w-full max-w-5xl rounded-3xl border border-line bg-white p-6 shadow-card sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-serif text-xl">
              Your Clinic
              <span className="ml-2 align-middle text-xs font-medium uppercase tracking-[0.2em] text-copper">
                One-time setup
              </span>
            </h2>
            <p className="mt-1 text-sm text-haze">
              Saved on this device only — filled into the billing boxes and stamped on every form.{" "}
              {clinicConfigured ? (
                <span className="font-medium text-green-700">
                  ✓ {clinic.clinic_name.trim() || "Clinic details saved"}
                </span>
              ) : (
                <span className="font-medium text-copper">Not set up yet.</span>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowClinicForm((prev) => !prev)}
            className="rounded-full border border-line bg-parchment px-5 py-2 text-sm font-semibold text-ink transition hover:-translate-y-0.5"
          >
            {showClinicForm ? "Done" : clinicConfigured ? "Edit clinic" : "Set up clinic"}
          </button>
        </div>

        {showClinicForm ? (
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {CLINIC_FIELDS.map((field) => (
              <label key={field.key} className="flex flex-col gap-1 text-xs uppercase tracking-[0.15em] text-haze">
                {field.label}
                <input
                  type="text"
                  value={clinic[field.key]}
                  onChange={(event) => updateClinic(field.key, event.target.value)}
                  placeholder={field.placeholder}
                  className="rounded-xl border border-line bg-white px-4 py-2 text-sm normal-case tracking-normal text-ink"
                />
              </label>
            ))}
            <p className="sm:col-span-2 text-xs text-haze">
              Changes save automatically. The stamp shows your practice name, IDs, and today&apos;s
              date on the finished ADA form.
            </p>
          </div>
        ) : null}
      </section>

      <section className="mx-auto mt-8 w-full max-w-5xl rounded-3xl border border-line bg-parchment p-6 shadow-card sm:p-10">
        <div className="grid gap-6">
          <label className="flex flex-col gap-4 rounded-2xl border-2 border-dashed border-copper/50 bg-white/90 p-8 text-sm text-haze transition hover:border-copper/70 hover:bg-white cursor-pointer">
            <div className="flex items-center gap-3">
              <svg className="h-10 w-10 text-copper" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div>
                <span className="block text-xs font-semibold uppercase tracking-[0.2em] text-copper">
                  Step 1: Upload Your Messy EOB
                </span>
                <span className="mt-1 block text-lg font-medium text-ink">
                  Drop your paper EOB scan here or click to browse
                </span>
                <span className="mt-1 block text-xs text-haze">
                  Accepts scanned PDFs, photos (JPG/PNG), or text files
                </span>
              </div>
            </div>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              className="hidden"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            {file && (
              <div className="rounded-lg bg-copper/10 px-4 py-2 text-sm text-ink border border-copper/20">
                ✓ Selected: <span className="font-semibold">{file.name}</span>
              </div>
            )}
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
              className="rounded-full bg-copper px-8 py-3 text-base font-semibold text-white shadow-lg shadow-copper/20 transition hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "⏳ Processing..." : "✨ Generate Clean Appeal Form"}
            </button>
            <button
              className="rounded-full border border-ocean px-6 py-3 text-sm font-semibold text-ocean transition hover:-translate-y-0.5 disabled:opacity-60"
              onClick={downloadText}
              disabled={!data}
            >
              Download Appeal
            </button>
            <button
              className="rounded-full bg-ocean px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-ocean/20 transition hover:-translate-y-0.5 hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed"
              onClick={downloadPdf}
              disabled={!file || !pdfAvailable || downloadingPdf}
            >
              {downloadingPdf ? "📄 Preparing..." : "📄 Download Clean ADA Form"}
            </button>
          </div>

          {!pdfAvailable && data ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
              ⚠️ PDF form temporarily unavailable. You can still download the appeal text above.
            </div>
          ) : null}

          {pdfAvailable && data ? (
            <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-xs text-green-900">
              ✅ Your clean, filled ADA form is ready! Click "Download Clean ADA Form" above.
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
        Free to use — no account, no per-claim fees. Files are processed to generate your appeal and
        are not stored. Avoid uploading PHI you are not authorized to share.
      </div>
    </main>
  );
}
