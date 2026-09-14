import BusinessDocumentUploadZone from "../../../components/BusinessDocuments/BusinessDocumentUploadZone.jsx";
import { BUSINESS_DOCUMENT_TYPES } from "../../../config/businessDocumentTypes.js";

export default function BusinessDocumentUploadPage() {
  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>Upload documents</h1>
          <p>
            Upload invoices, receipts, purchase orders, resumes, expense reports, application
            forms, or contracts. Each file&apos;s type is detected automatically, its fields are
            extracted and validated, and the structured result is saved as a record — this never
            touches the chatbot&apos;s knowledge base.
          </p>
        </div>
      </div>

      <BusinessDocumentUploadZone />

      <div className="business-doc-types-grid">
        {BUSINESS_DOCUMENT_TYPES.map((docType) => (
          <div key={docType.key} className="business-doc-type-card">
            <docType.icon size={18} className="business-doc-type-card__icon" />
            <div>
              <p className="business-doc-type-card__title">{docType.label}</p>
              <p className="business-doc-type-card__description">{docType.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}