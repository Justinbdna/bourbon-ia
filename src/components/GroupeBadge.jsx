const getBadgeStyle = (statusLabel) => {
  const s = String(statusLabel || "").toLowerCase();
  if (s.includes("isolé") || s.includes("nouveau")) return "bg-gray-100 dark:bg-neutral-800 text-gray-700 dark:text-neutral-300 border border-gray-200 dark:border-neutral-700";
  if (s.includes("doublon")) return "bg-rose-100 dark:bg-rose-950/50 text-rose-800 dark:text-rose-200 border border-rose-200 dark:border-rose-500/30 font-medium";
  if (s.includes("commune") || s.includes("incompatible")) return "bg-purple-100 dark:bg-purple-950/50 text-purple-800 dark:text-purple-200 border border-purple-200 dark:border-purple-500/30 font-medium";
  if (s.includes("identique")) return "bg-blue-100 dark:bg-blue-950/50 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-500/30 font-medium";
  if (s.includes("erreur") || s === "—" || s === "") return "bg-red-100 dark:bg-red-950/50 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-500/30 font-medium";
  return "bg-gray-100 dark:bg-neutral-800 text-gray-700 dark:text-neutral-300 border border-gray-200 dark:border-neutral-700"; 
};

export default function GroupeBadge({ statut, groupe, isPending }) {
  if (isPending) {
    return (
      <span className="text-[11px] px-2.5 py-0.5 rounded-full inline-flex items-center gap-1.5 font-medium whitespace-nowrap bg-slate-100 dark:bg-neutral-800 text-slate-500 border border-slate-200 dark:border-neutral-700 animate-pulse">
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
      className={`text-[11px] px-2.5 py-0.5 rounded-full inline-flex items-center justify-center gap-1.5 font-medium whitespace-nowrap ${style}`}
    >
      {label}
    </span>
  )
}
