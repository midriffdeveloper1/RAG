import { SUGGESTED_QUESTIONS } from "../../utils/constants.js";

export default function SuggestedQuestions({ onSelect, disabled }) {
  return (
    <div className="suggested-questions">
      {SUGGESTED_QUESTIONS.map((question) => (
        <button
          key={question}
          type="button"
          className="suggested-questions__chip"
          onClick={() => onSelect(question)}
          disabled={disabled}
        >
          {question}
        </button>
      ))}
    </div>
  );
}
