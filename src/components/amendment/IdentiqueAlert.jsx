import React from 'react';

export default function IdentiqueAlert({ isIdentical, discussionId }) {
  if (!isIdentical) return null;

  return (
    <div className="flex items-center gap-2 p-3 my-2 rounded-md bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800">
      {/* Icône d'alerte */}
      <svg className="w-5 h-5 text-orange-600 dark:text-orange-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div className="flex flex-col">
        <span className="text-sm font-bold text-orange-800 dark:text-orange-300">
          Doublon Officiel AN
        </span>
        {discussionId && (
          <span className="text-xs text-orange-700 dark:text-orange-400">
            Discussion identique : <span className="font-mono bg-orange-100 dark:bg-orange-900/50 px-1 rounded">{discussionId}</span>
          </span>
        )}
      </div>
    </div>
  );
}
