// import { useRef, useState } from "react";
// import { uploadDocument } from "../../services/adminApi.js";

// const ACCEPTED_EXTENSIONS = ".pdf,.docx,.doc";

// export default function DocumentUpload({ onUploaded }) {
//   const fileInputRef = useRef(null);
//   const [isUploading, setIsUploading] = useState(false);
//   const [progress, setProgress] = useState(0);
//   const [error, setError] = useState(null);

//   async function handleFileChange(e) {
//     const file = e.target.files?.[0];
//     if (!file) return;

//     setIsUploading(true);
//     setProgress(0);
//     setError(null);

//     try {
//       const document = await uploadDocument(file, (evt) => {
//         if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100));
//       });
//       onUploaded?.(document);
//     } catch (err) {
//       setError(err.response?.data?.detail || "Upload failed. Please try again.");
//     } finally {
//       setIsUploading(false);
//       if (fileInputRef.current) fileInputRef.current.value = "";
//     }
//   }

//   return (
//     <div className="document-upload">
//       <label className="document-upload__dropzone">
//         <input
//           ref={fileInputRef}
//           type="file"
//           accept={ACCEPTED_EXTENSIONS}
//           onChange={handleFileChange}
//           disabled={isUploading}
//           hidden
//         />
//         <span className="document-upload__icon" aria-hidden="true">
//           ↑
//         </span>
//         <span>
//           {isUploading
//             ? `Uploading… ${progress}%`
//             : "Click to upload a PDF or Word document"}
//         </span>
//         <span className="document-upload__hint">
//           The knowledge base is re-embedded automatically after upload.
//         </span>
//       </label>

//       {error && <p className="document-upload__error">{error}</p>}
//     </div>
//   );
// }

import { useRef, useState } from "react";
import { uploadDocument } from "../../services/adminApi.js";
import { AlertCircle, UploadCloud } from "../common/Icons.jsx";

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.doc";

export default function DocumentUpload({ onUploaded }) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setProgress(0);
    setError(null);

    try {
      const document = await uploadDocument(file, (evt) => {
        if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100));
      });
      onUploaded?.(document);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="document-upload">
      <label className={`document-upload__dropzone ${isUploading ? "document-upload__dropzone--busy" : ""}`}>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          onChange={handleFileChange}
          disabled={isUploading}
          hidden
        />
        <span className="document-upload__icon" aria-hidden="true">
          <UploadCloud size={22} />
        </span>
        <span className="document-upload__label">
          {isUploading ? `Uploading… ${progress}%` : "Click to upload a PDF or Word document"}
        </span>

        {isUploading && (
          <span className="document-upload__progress-track" aria-hidden="true">
            <span className="document-upload__progress-fill" style={{ width: `${progress}%` }} />
          </span>
        )}

        <span className="document-upload__hint">
          The knowledge base is re-embedded automatically after upload.
        </span>
      </label>

      {error && (
        <p className="document-upload__error">
          <AlertCircle size={14} />
          {error}
        </p>
      )}
    </div>
  );
}