import React from 'react';

export default function LegislativeContext({ title, dossierRef }) {
  if (!title) return null;

  return (
    <div className="group relative max-w-full">
      <div 
        className="text-xs text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded px-2 py-1 overflow-hidden"
        style={{
          display: '-webkit-box',
          WebkitLineClamp: '1',
          WebkitBoxOrient: 'vertical'
        }}
      >
        <span className="font-semibold text-slate-700 dark:text-slate-300 mr-1">
          {dossierRef || 'Texte'} :
        </span>
        {title}
      </div>
      
      {/* Tooltip au survol */}
      <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full left-0 mb-2 w-max max-w-xs bg-slate-900 text-white text-xs rounded shadow-lg p-2">
        {title}
        {/* Petite flèche en bas du tooltip */}
        <div className="absolute top-full left-4 -mt-[1px] border-4 border-transparent border-t-slate-900" />
      </div>
    </div>
  );
}
