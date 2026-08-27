import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "./Icons.jsx";

/**
 * options: [{ value, label }]
 * selected: array of selected values
 * onChange: (newSelectedArray) => void
 */
export default function MultiSelectDropdown({
  options,
  selected,
  onChange,
  placeholder = "Select…",
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function toggleValue(value) {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  }

  const selectedLabels = options.filter((o) => selected.includes(o.value)).map((o) => o.label);
  const summary =
    selectedLabels.length === 0
      ? placeholder
      : selectedLabels.length <= 2
        ? selectedLabels.join(", ")
        : `${selectedLabels.length} selected`;

  return (
    <div className="multiselect" ref={containerRef}>
      <button
        type="button"
        className="multiselect__trigger"
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
      >
        <span className={selectedLabels.length === 0 ? "multiselect__placeholder" : ""}>
          {summary}
        </span>
        <ChevronDown size={16} />
      </button>

      {isOpen && (
        <div className="multiselect__panel">
          {options.length === 0 && <p className="multiselect__empty">No options available.</p>}
          {options.map((option) => {
            const isChecked = selected.includes(option.value);
            return (
              <label key={option.value} className="multiselect__option">
                <span className={`multiselect__checkbox ${isChecked ? "multiselect__checkbox--checked" : ""}`}>
                  {isChecked && <Check size={12} />}
                </span>
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleValue(option.value)}
                  hidden
                />
                {option.label}
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}