import React from 'react';

const STATUS_TRANSITIONS = {
  Scheduled: {
    nextStatus: 'En route',
    label: 'Mark En route',
    btnClass: 'bg-indigo-600 hover:bg-indigo-700 text-white',
  },
  'En route': {
    nextStatus: 'Picked up',
    label: 'Mark Picked up',
    btnClass: 'bg-emerald-600 hover:bg-emerald-700 text-white',
  },
  'Picked up': {
    nextStatus: 'Delivered to hub',
    label: 'Deliver to Hub',
    btnClass: 'bg-green-700 hover:bg-green-800 text-white',
  },
};

export function StatusButton({ currentStatus, onUpdate, disabled = false, compact = false }) {
  const transition = STATUS_TRANSITIONS[currentStatus];
  if (!transition) return null;

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        onUpdate(transition.nextStatus);
      }}
      className={`inline-flex items-center justify-center font-medium rounded-md shadow-sm transition-colors text-xs disabled:opacity-50 disabled:cursor-not-allowed ${
        transition.btnClass
      } ${compact ? 'px-2.5 py-1 text-[11px]' : 'px-3 py-1.5'}`}
    >
      <span>{transition.label}</span>
    </button>
  );
}

export default StatusButton;
