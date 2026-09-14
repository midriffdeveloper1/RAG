import {
  Briefcase,
  ClipboardList,
  FileSignature,
  FileSpreadsheet,
  FileText,
  Receipt,
  UserCog,
} from "../components/common/Icons.jsx";

// Single source of truth for the 7 document types the Business Management
// module understands — used to build the sidebar submenu, the routes, and
// each table page's header/empty-state copy.
export const BUSINESS_DOCUMENT_TYPES = [
  {
    key: "invoice",
    path: "invoices",
    label: "Invoices",
    singular: "invoice",
    icon: Receipt,
    description: "Vendor invoices — amounts, line items, and due dates extracted automatically.",
  },
  {
    key: "receipt",
    path: "receipts",
    label: "Receipts",
    singular: "receipt",
    icon: FileText,
    description: "Purchase receipts — merchant, items, and totals extracted automatically.",
  },
  {
    key: "purchase_order",
    path: "purchase-orders",
    label: "Purchase Orders",
    singular: "purchase order",
    icon: ClipboardList,
    description: "Purchase orders — vendor, line items, and delivery details extracted automatically.",
  },
  {
    key: "resume",
    path: "resumes",
    label: "Resumes",
    singular: "resume",
    icon: UserCog,
    description: "Candidate resumes — contact info, experience, and skills extracted automatically.",
  },
  {
    key: "expense_report",
    path: "expense-reports",
    label: "Expense Reports",
    singular: "expense report",
    icon: FileSpreadsheet,
    description: "Employee expense reports — line items and totals extracted automatically.",
  },
  {
    key: "application_form",
    path: "application-forms",
    label: "Application Forms",
    singular: "application form",
    icon: Briefcase,
    description: "Application forms — applicant details extracted automatically.",
  },
  {
    key: "contract",
    path: "contracts",
    label: "Contracts",
    singular: "contract",
    icon: FileSignature,
    description: "Contracts — parties, dates, and key terms extracted automatically.",
  },
];

export function getDocumentTypeConfig(key) {
  return BUSINESS_DOCUMENT_TYPES.find((t) => t.key === key);
}