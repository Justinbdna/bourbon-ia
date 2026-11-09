import React from 'react';

const GROUP_COLORS = {
  // Groupes politiques officiels XVIIe & XVIe Législature (Assemblée nationale)
  'EPR': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-purple-200 dark:border-purple-800',
  'RE': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-purple-200 dark:border-purple-800',
  'RN': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800',
  'LFI-NFP': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200 dark:border-red-800',
  'LFI': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200 dark:border-red-800',
  'SOC': 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300 border-pink-200 dark:border-pink-800',
  'DR': 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-200 border-blue-100 dark:border-blue-900',
  'LR': 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-200 border-blue-100 dark:border-blue-900',
  'ECOS': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-200 dark:border-green-800',
  'ECO': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-200 dark:border-green-800',
  'DEM': 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 border-orange-200 dark:border-orange-800',
  'HOR': 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800',
  'LIOT': 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300 border-teal-200 dark:border-teal-800',
  'GDR': 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-200 border-red-100 dark:border-red-900',
  'UDR': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
  'NI': 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700',
  
  // Sénat (branche feature/legistique-an-senat)
  'SER': 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300 border-pink-200 dark:border-pink-800',
  'CRCE': 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-200 border-red-100 dark:border-red-900',
  'UC': 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 border-amber-200 dark:border-amber-800',
  'RDPI': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-purple-200 dark:border-purple-800',
  'RDSE': 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300 border-teal-200 dark:border-teal-800',
  'GEST': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-200 dark:border-green-800',
  'LIRT': 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',

  // Institutionnel / Gouvernement
  'GOUVERNEMENT': 'bg-slate-900 text-amber-200 dark:bg-slate-950 dark:text-amber-300 border-slate-700 dark:border-slate-800 font-semibold shadow-xs',
  'GOUV': 'bg-slate-900 text-amber-200 dark:bg-slate-950 dark:text-amber-300 border-slate-700 dark:border-slate-800 font-semibold shadow-xs',

  // Fallback générique
  'DEFAULT': 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700'
};

export default function PoliticalGroupTag({ group, groupRef }) {
  if (!group && !groupRef) return null;

  const displayGroup = group || groupRef || 'Inconnu';
  const upper = displayGroup.toUpperCase();
  
  // Recherche simple pour attribuer une couleur si le nom/ref contient le sigle
  const foundKey = Object.keys(GROUP_COLORS).find(key => 
    key !== 'DEFAULT' && upper.includes(key)
  );
  
  const colorClasses = GROUP_COLORS[foundKey] || GROUP_COLORS.DEFAULT;
  const isGouv = upper.includes('GOUV');

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${colorClasses}`}>
      {isGouv && <span className="text-[10px]" aria-hidden="true">🏛️</span>}
      {isGouv ? 'Gouvernement' : displayGroup}
    </span>
  );
}
