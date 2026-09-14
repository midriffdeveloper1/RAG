import { Link, Navigate, useParams } from "react-router-dom";
import { BUSINESS_DOCUMENT_TYPES } from "../../../config/businessDocumentTypes.js";
import BusinessDocumentTable from "../../../components/BusinessDocuments/BusinessDocumentTable.jsx";
import { UploadCloud } from "../../../components/common/Icons.jsx";

export default function BusinessDocumentTypePage() {
  const { docPath } = useParams();
  const docType = BUSINESS_DOCUMENT_TYPES.find((t) => t.path === docPath);

  if (!docType) {
    return <Navigate to="/admin/business-management/upload" replace />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1>{docType.label}</h1>
          <p>{docType.description}</p>
        </div>
        <Link to="/admin/business-management/upload" className="catalog-section__add-btn">
          <UploadCloud size={15} />
          Upload {docType.singular}s
        </Link>
      </div>

      <BusinessDocumentTable
        documentType={docType.key}
        emptyDescription={`Upload a ${docType.singular} to see its extracted data here.`}
      />
    </div>
  );
}