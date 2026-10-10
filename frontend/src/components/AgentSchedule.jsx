import React from 'react';
import { formatLocalTime, formatDuration } from '../utils/formatters';
import StatusButton from './StatusButton';

export function AgentSchedule({
  schedule = [],
  totalTravelTime = null,
  isEstimatedTimes = false,
  onStatusUpdate,
  selectedPickupId = null,
  onSelectPickup,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900 flex items-center space-x-2">
            <span>Shift Pickup Itinerary</span>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
              {schedule.length} {schedule.length === 1 ? 'Stop' : 'Stops'}
            </span>
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Ordered sequence of pickups assigned to your shift
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs">
          {totalTravelTime != null && (
            <div className="px-2.5 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-700">
              <span className="text-gray-500">Total Travel:</span>{' '}
              <span className="font-semibold">{formatDuration(totalTravelTime)}</span>
            </div>
          )}

          {isEstimatedTimes && (
            <span className="px-2 py-1 rounded-md bg-amber-50 border border-amber-200 text-amber-800 font-medium">
              Estimated travel times
            </span>
          )}
        </div>
      </div>

      {schedule.length === 0 ? (
        <div className="py-12 text-center text-gray-500 text-xs">
          No pickups currently scheduled for this agent.
        </div>
      ) : (
        <div className="space-y-3">
          {schedule.map((item, index) => {
            const reqId = item.request_id || item.id;
            const isSelected = selectedPickupId === reqId;
            const isFinished = item.status === 'Delivered to hub' || item.status === 'Delivered';

            return (
              <div
                key={reqId || index}
                onClick={() => onSelectPickup && onSelectPickup(item)}
                className={`p-4 rounded-lg border transition-colors cursor-pointer ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50/40 ring-1 ring-blue-500/20'
                    : 'border-gray-200 bg-white hover:bg-gray-50/60'
                } ${isFinished ? 'opacity-60' : ''}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start space-x-3">
                    <div className="w-6 h-6 rounded-full bg-gray-100 text-gray-700 flex items-center justify-center font-semibold text-xs shrink-0 mt-0.5">
                      {index + 1}
                    </div>

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-semibold text-gray-900">
                          {item.customer_name || 'Customer'}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                            item.status === 'En route'
                              ? 'bg-purple-100 text-purple-800'
                              : item.status === 'Picked up'
                              ? 'bg-green-100 text-green-800'
                              : item.status === 'Delivered to hub' || item.status === 'Delivered'
                              ? 'bg-gray-100 text-gray-700'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>

                      <p className="text-xs text-gray-600 mt-1">
                        {item.address}
                      </p>

                      <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-gray-500 font-mono">
                        {item.scheduled_time && (
                          <span>
                            Time: <strong className="font-sans text-gray-800">{formatLocalTime(item.scheduled_time)}</strong>
                          </span>
                        )}
                        {item.estimated_travel_time_seconds != null && (
                          <span>
                            Travel: <strong className="font-sans text-gray-800">{formatDuration(item.estimated_travel_time_seconds)}</strong>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="sm:self-center shrink-0">
                    <StatusButton
                      currentStatus={item.status}
                      onUpdate={(nextStatus) => onStatusUpdate && onStatusUpdate(reqId, nextStatus)}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default AgentSchedule;
