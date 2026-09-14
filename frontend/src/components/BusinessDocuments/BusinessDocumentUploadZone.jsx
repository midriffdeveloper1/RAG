import { useRef, useState } from "react";
import { uploadBusinessDocuments } from "../../services/adminApi.js";
import { getDocumentTypeConfig } from "../../config/businessDocumentTypes.js";
import { AlertCircle, CheckCircle2, FileText, UploadCloud, XCircle } from "../common/Icons.jsx";
import { Spinner } from "../common/Spinner.jsx";
import BusinessDocumentStatusBadge from "./BusinessDocumentStatusBadge.jsx";
import ConfidenceMeter from "./ConfidenceMeter.jsx";
import { formatFileSize, getHeadline } from "../../utils/businessDocuments.js";

const ACCEPTED_EXTENSIONS = ".pdf,.jpg,.jpeg,.png,.webp,.docx,.doc";
const MAX_FILES = 15;

export default function BusinessDocumentUploadZone({ documentTypeHint, onUploaded }) {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]); // BusinessDocumentOut[] from the last batch

  async function handleFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    if (files.length > MAX_FILES) {
      setError(`Upload at most ${MAX_FILES} files at a time.`);
      return;
    }

    setIsUploading(true);
    setError(null);
    setResults([]);

    try {
      const documents = await uploadBusinessDocuments(files, documentTypeHint);
      setResults(documents);
      onUploaded?.(documents);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div className="document-upload">
      <label
        className={`document-upload__dropzone ${isUploading ? "document-upload__dropzone--busy" : ""} ${
          isDragging ? "document-upload__dropzone--drag" : ""
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          disabled={isUploading}
          hidden
        />
        <span className="document-upload__icon" aria-hidden="true">
          <UploadCloud size={22} />
        </span>
        <span className="document-upload__label">
          {isUploading
            ? "Reading and extracting your documents…"
            : "Click to upload, or drag and drop multiple files"}
        </span>
        <span className="document-upload__hint">
          PDF, JPG, PNG, or Word — up to {MAX_FILES} files at once. Each file&apos;s type is
          detected automatically and its data is stored as structured records, never sent to the
          knowledge base.
        </span>
      </label>

      {error && (
        <p className="document-upload__error">
          <AlertCircle size={14} />
          {error}
        </p>
      )}

      {isUploading && (
        <div className="upload-batch-progress">
          <Spinner size={16} />
          <span>Processing your batch — this can take a moment per file…</span>
        </div>
      )}

      {results.length > 0 && (
        <div className="upload-batch-results">
          <p className="upload-batch-results__title">
            Last batch — {results.length} file{results.length === 1 ? "" : "s"}
          </p>
          <ul className="upload-batch-results__list">
            {results.map((doc) => {
              const typeConfig = getDocumentTypeConfig(doc.document_type);
              const headline = getHeadline(doc.document_type, doc.extracted_data);
              return (
                <li key={doc.id} className="upload-batch-results__item">
                  <div className="upload-batch-results__icon">
                    {doc.status === "failed" ? (
                      <XCircle size={18} className="upload-batch-results__icon--failed" />
                    ) : doc.is_valid ? (
                      <CheckCircle2 size={18} className="upload-batch-results__icon--ok" />
                    ) : (
                      <FileText size={18} />
                    )}
                  </div>
                  <div className="upload-batch-results__body">
                    <div className="upload-batch-results__row">
                      <span className="upload-batch-results__filename">{doc.original_filename}</span>
                      <span className="upload-batch-results__size">
                        {formatFileSize(doc.file_size_bytes)}
                      </span>
                    </div>
                    <div className="upload-batch-results__row upload-batch-results__row--meta">
                      <BusinessDocumentStatusBadge status={doc.status} />
                      <span className="upload-batch-results__type">
                        {typeConfig ? typeConfig.label : "Unrecognized type"}
                      </span>
                      {doc.confidence_score !== null && doc.confidence_score !== undefined && (
                        <ConfidenceMeter value={doc.confidence_score} size="sm" />
                      )}
                    </div>
                    {headline && <p className="upload-batch-results__headline">{headline}</p>}
                    {doc.error_message && (
                      <p className="upload-batch-results__error">{doc.error_message}</p>
                    )}
                    {!doc.is_valid && doc.status === "needs_review" && (
                      <p className="upload-batch-results__warning">
                        {doc.missing_fields?.length
                          ? `Missing: ${doc.missing_fields.join(", ")}`
                          : "Some extracted fields need a quick review."}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}