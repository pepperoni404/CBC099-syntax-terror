import React from 'react';
import { formatLocalDateTime } from '../utils/formatters';

const STAGES = [
  { id: 'Pending', label: 'Pending', desc: 'Request submitted and queued for scheduling' },
  { id: 'Scheduled', label: 'Scheduled', desc: 'Courier agent assigned to pickup' },
  { id: 'En route', label: 'En route', desc: 'Courier is heading to pickup address' },
  { id: 'Picked up', label: 'Picked up', desc: 'Package collected from customer' },
  { id: 'Delivered to hub', label: 'Delivered to Hub', desc: 'Package arrived at central sorting hub' },
];

export function TrackingTimeline({ history = [], currentStatus = 'Pending' }) {
  const historyMap = {};
  if (Array.isArray(history)) {
    history.forEach((item) => {
      if (item && item.status) {
        historyMap[item.status] = item.timestamp;
      }
    });
  }

  const isCancelled = currentStatus === 'Cancelled';
  const isUnassigned = currentStatus === 'Unassigned';

  const currentIndex = STAGES.findIndex(
    (s) => s.id === currentStatus || (s.id === 'Delivered to hub' && currentStatus === 'Delivered')
  );

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-gray-100 pb-3">
        <h3 className="text-sm font-semibold text-gray-900">Pickup Progress</h3>
        <span
          className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
            isCancelled
              ? 'bg-gray-100 text-gray-700'
              : isUnassigned
              ? 'bg-red-100 text-red-700'
              : currentStatus === 'Delivered to hub' || currentStatus === 'Delivered'
              ? 'bg-green-100 text-green-800'
              : 'bg-blue-100 text-blue-800'
          }`}
        >
          {currentStatus}
        </span>
      </div>

      {isCancelled && (
        <div className="p-3 rounded-md bg-gray-50 border border-gray-200 text-xs text-gray-700">
          <strong>Request Cancelled:</strong> This pickup request has been cancelled.
        </div>
      )}

      {isUnassigned && (
        <div className="p-3 rounded-md bg-red-50 border border-red-200 text-xs text-red-800">
          <strong>Unassigned:</strong> No courier agent was available within the requested window. A suggested slot is available.
        </div>
      )}

      {/* Vertical Steps */}
      <div className="relative pl-6 space-y-5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200">
        {STAGES.map((stage, idx) => {
          const isPassed = !isCancelled && !isUnassigned && currentIndex >= 0 && idx <= currentIndex;
          const isCurrent = !isCancelled && !isUnassigned && idx === currentIndex;
          const timestamp = historyMap[stage.id];

          return (
            <div key={stage.id} className="relative">
              {/* Dot */}
              <div
                className={`absolute -left-[27px] top-1 w-3.5 h-3.5 rounded-full border-2 ${
                  isPassed
                    ? 'bg-blue-600 border-blue-600'
                    : 'bg-white border-gray-300'
                }`}
              />

              <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
                <div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-xs font-semibold ${
                        isPassed ? 'text-gray-900' : 'text-gray-500'
                      }`}
                    >
                      {stage.label}
                    </span>
                    {isCurrent && (
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        Current
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{stage.desc}</p>
                </div>

                <div className="text-[11px] text-gray-500 font-mono sm:text-right shrink-0">
                  {timestamp ? formatLocalDateTime(timestamp) : '—'}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TrackingTimeline;
