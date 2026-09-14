import { confidenceTier, formatConfidencePct } from "../../utils/businessDocuments.js";

export default function ConfidenceMeter({ value, size = "md" }) {
  const pct = formatConfidencePct(value);
  if (pct === null) {
    return <span className="confidence-meter confidence-meter--unknown">—</span>;
  }
  const tier = confidenceTier(value);

  return (
    <span className={`confidence-meter confidence-meter--${tier} confidence-meter--${size}`}>
      <span className="confidence-meter__track">
        <span className="confidence-meter__fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="confidence-meter__value">{pct}%</span>
    </span>
  );
}