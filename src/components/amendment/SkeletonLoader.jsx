import React from 'react';

export default function SkeletonLoader({ type = 'badge', count = 1, className = '' }) {
  const renderSkeleton = (key) => {
    switch (type) {
      case 'badge':
        return (
          <div key={key} className={`animate-pulse bg-slate-200 dark:bg-slate-700 rounded-md h-8 w-32 ${className}`}></div>
        );
      case 'text':
        return (
          <div key={key} className={`animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-4 w-full mb-2 ${className}`}></div>
        );
      case 'title':
        return (
          <div key={key} className={`animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-6 w-3/4 mb-4 ${className}`}></div>
        );
      case 'card':
      default:
        return (
          <div key={key} className={`animate-pulse bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 h-full flex flex-col gap-3 ${className}`}>
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
            <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
            <div className="h-20 bg-slate-200 dark:bg-slate-700 rounded mt-4"></div>
          </div>
        );
    }
  };

  if (count === 1) {
    return renderSkeleton(0);
  }

  return (
    <>
      {Array.from({ length: count }).map((_, i) => renderSkeleton(i))}
    </>
  );
}
