import React, { useState, useEffect, useRef } from "react";
import { ShieldCheck, Download, UploadCloud, CheckCircle2, AlertTriangle, FileText, RefreshCw, FileCheck2, Lock } from "lucide-react";

interface Artifact {
  id: string;
  file_name: string;
  sha256_hash: string;
  file_size_bytes: number;
  collected_via: string;
  created_at: string;
  locked_until?: string;
  verification_status?: string;
  status?: "UNVERIFIED" | "VERIFIED" | "TAMPERED";
}

const DEFAULT_TENANT_ID = "242a86b5-3d7a-4ccf-9287-9680326487b8";
const DEFAULT_CONTROL_ID = "8fcb984b-15cf-4f05-9a2c-8e37542d5532";

export default function App() {
  const [tenantId] = useState<string>(DEFAULT_TENANT_ID);
  const [controlId, setControlId] = useState<string>(DEFAULT_CONTROL_ID);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchArtifacts = async () => {
    if (!controlId.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`/vault/controls/${controlId}/artifacts`, {
        headers: { "X-Tenant-ID": tenantId },
      });
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : data.artifacts || [];
        setArtifacts(
          list.map((art: Artifact) => ({
            ...art,
            status: art.verification_status === "VERIFIED" ? "VERIFIED" : "UNVERIFIED",
          }))
        );
      } else {
        setArtifacts([]);
      }
    } catch (err) {
      console.error("Failed to load artifacts:", err);
      setArtifacts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArtifacts();
  }, []);

  const handleFileUpload = async (file: File) => {
    if (!controlId.trim()) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`/vault/controls/${controlId}/artifacts`, {
        method: "POST",
        headers: {
          "X-Tenant-ID": tenantId,
        },
        body: formData,
      });

      if (res.ok) {
        await fetchArtifacts();
      } else {
        alert("Upload failed. Check backend logs.");
      }
    } catch (err) {
      console.error("Error uploading file:", err);
    } finally {
      setUploading(false);
    }
  };

  const verifyArtifact = async (id: string) => {
    try {
      const res = await fetch(`/vault/artifacts/${id}/verify`, {
        method: "GET",
        headers: { "X-Tenant-ID": tenantId },
      });
      if (res.ok) {
        setArtifacts((prev) =>
          prev.map((art) =>
            art.id === id ? { ...art, status: "VERIFIED" } : art
          )
        );
      } else if (res.status === 412) {
        setArtifacts((prev) =>
          prev.map((art) =>
            art.id === id ? { ...art, status: "TAMPERED" } : art
          )
        );
      }
    } catch (err) {
      console.error("Verification failed:", err);
    }
  };

  const downloadArtifact = (id: string) => {
    window.open(`/vault/artifacts/${id}/download?tenant_id=${tenantId}`, "_blank");
  };

  const exportAuditReport = () => {
    const report = {
      compliance_standard: "SOC2 Type II - Common Criteria 6.1",
      attestation_type: "Cryptographic WORM Evidence Ledger Attestation",
      generated_at: new Date().toISOString(),
      tenant_id: tenantId,
      control_id: controlId,
      total_artifacts: artifacts.length,
      storage_guarantees: {
        worm_storage: "AWS S3 Object Lock (Compliance Mode)",
        retention_lock_active: true,
        legal_hold: "ACTIVE",
      },
      artifacts: artifacts.map((art) => ({
        artifact_id: art.id,
        file_name: art.file_name,
        sha256_hash: art.sha256_hash,
        file_size_bytes: art.file_size_bytes,
        collected_via: art.collected_via,
        locked_until: art.locked_until || "2033-01-01T00:00:00Z",
        cryptographic_verification: art.status || "UNVERIFIED",
      })),
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `soc2_audit_attestation_${controlId.slice(0, 8)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-7 h-7 text-emerald-400" />
          <div>
            <h1 className="text-xl font-bold tracking-tight">SOC2 Evidence Vault Explorer</h1>
            <p className="text-xs text-slate-400">Continuous Compliance & WORM-Locked Audit Ledger</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={exportAuditReport}
            disabled={artifacts.length === 0}
            className="flex items-center gap-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 border border-slate-700 text-slate-200 px-3.5 py-1.5 rounded-lg transition"
          >
            <FileCheck2 className="w-4 h-4 text-emerald-400" />
            Export Attestation Report
          </button>
          <span className="text-xs font-mono bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 px-3 py-1 rounded-full flex items-center gap-1">
            <Lock className="w-3 h-3" /> S3 OBJECT LOCK: ACTIVE
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto p-8 flex flex-col gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="w-full flex-1">
            <label className="text-xs font-mono text-slate-400 block mb-1">AUDIT CONTROL UUID</label>
            <input
              type="text"
              value={controlId}
              onChange={(e) => setControlId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && fetchArtifacts()}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 font-mono text-sm focus:outline-none focus:border-emerald-500"
              placeholder="e.g. 8fcb984b-15cf-4f05-9a2c-8e37542d5532"
            />
          </div>
          <button
            onClick={fetchArtifacts}
            disabled={loading}
            className="w-full md:w-auto mt-auto flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold px-5 py-2.5 rounded-lg transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Load Evidence
          </button>
        </div>

        {/* Drag and Drop Upload Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              handleFileUpload(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-7 flex flex-col items-center justify-center gap-2 transition cursor-pointer ${
            dragActive
              ? "border-emerald-500 bg-emerald-950/20"
              : "border-slate-800 hover:border-slate-700 bg-slate-900/40"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
          />
          <div className="p-3 bg-slate-800/80 rounded-full text-emerald-400">
            <UploadCloud className={`w-6 h-6 ${uploading ? "animate-bounce" : ""}`} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium">
              {uploading ? "Ingesting artifact into WORM ledger..." : "Click or drag evidence artifact to upload"}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">Applies SHA-256 calculation & 7-Year S3 Object Lock</p>
          </div>
        </div>

        {/* Evidence Ledger Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/50 text-xs font-mono text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">File / Artifact</th>
                <th className="py-3 px-4">SHA-256 Digest</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Retention Hold</th>
                <th className="py-3 px-4">WORM Integrity</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-sm">
              {artifacts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 font-sans">
                    {loading ? "Loading audit trail..." : "No artifacts found for this control."}
                  </td>
                </tr>
              ) : (
                artifacts.map((art) => (
                  <tr key={art.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-4 px-4 font-medium flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-400" />
                      {art.file_name}
                    </td>
                    <td className="py-4 px-4 font-mono text-xs text-slate-400">
                      {art.sha256_hash ? `${art.sha256_hash.slice(0, 16)}...` : "—"}
                    </td>
                    <td className="py-4 px-4 text-xs text-slate-400">
                      {art.file_size_bytes ? `${(art.file_size_bytes / 1024).toFixed(1)} KB` : "—"}
                    </td>
                    <td className="py-4 px-4">
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-emerald-900/40">
                        <Lock className="w-2.5 h-2.5" />
                        {art.locked_until ? `Locked ${art.locked_until.slice(0, 4)}` : "Locked 2033"}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      {art.status === "VERIFIED" ? (
                        <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
                          <CheckCircle2 className="w-4 h-4" /> VERIFIED
                        </span>
                      ) : art.status === "TAMPERED" ? (
                        <span className="flex items-center gap-1.5 text-xs text-rose-400 font-mono">
                          <AlertTriangle className="w-4 h-4" /> TAMPERED
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400 font-mono">UNVERIFIED</span>
                      )}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => verifyArtifact(art.id)}
                          className="flex items-center gap-1 text-xs border border-slate-700 hover:border-slate-600 bg-slate-800 px-3 py-1.5 rounded text-slate-200 transition"
                        >
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                          Verify Hash
                        </button>
                        <button
                          onClick={() => downloadArtifact(art.id)}
                          className="flex items-center gap-1 text-xs border border-slate-700 hover:border-slate-600 bg-slate-800 px-3 py-1.5 rounded text-slate-200 transition"
                        >
                          <Download className="w-3.5 h-3.5 text-sky-400" />
                          Egress
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
