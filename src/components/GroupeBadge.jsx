const getBadgeStyle = (statusLabel) => {
  const s = String(statusLabel || "").toLowerCase();
  if (s.includes("isolé") || s.includes("nouveau")) return "bg-gray-100 text-gray-800 border border-gray-200";
  if (s.includes("commune") || s.includes("incompatible")) return "bg-purple-100 text-purple-800 border border-purple-200 font-semibold";
  if (s.includes("identique")) return "bg-blue-100 text-blue-800 border border-blue-200 font-semibold";
  if (s.includes("erreur") || s === "—" || s === "") return "bg-red-100 text-red-800 border border-red-200";
  return "bg-gray-100 text-gray-800"; 
};

export default function GroupeBadge({ statut, groupe, isPending }) {
  if (isPending) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs bg-slate-100 text-slate-500 border border-slate-200 animate-pulse">
        <svg className="animate-spin h-3 w-3 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        En cours...
      </span>
    )
  }

  const label = statut || (groupe ? groupe.type : "Non classé");
  const style = getBadgeStyle(label);
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs ${style}`}
    >
      {label}
    </span>
  )
}
