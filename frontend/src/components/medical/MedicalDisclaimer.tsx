import { AlertCircle } from "lucide-react";

export function MedicalDisclaimer() {
  return (
    <div className="medical-disclaimer" role="note">
      <AlertCircle size={18} className="flex-shrink-0" aria-hidden="true" />
      <div>
        <strong>Medical Disclaimer:</strong> AI-generated summaries and abnormality flags are for informational assistance only and not a substitute for clinical judgment or a qualified healthcare professional. JohnnySummUP does not provide diagnoses or treatment recommendations.
      </div>
    </div>
  );
}
