const getBadgeStyle = (statusLabel) => {
  const s = String(statusLabel || "").toLowerCase();
  if (s.includes("isolé") || s.includes("nouveau")) return "bg-gray-100 text-gray-800 border border-gray-200";
  if (s.includes("commune") || s.includes("incompatible")) return "bg-purple-100 text-purple-800 border border-purple-200 font-semibold";
  if (s.includes("identique")) return "bg-blue-100 text-blue-800 border border-blue-200 font-semibold";
  if (s.includes("erreur") || s === "—" || s === "") return "bg-red-100 text-red-800 border border-red-200";
  return "bg-gray-100 text-gray-800"; 
};

export default function GroupeBadge({ statut, groupe }) {
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
