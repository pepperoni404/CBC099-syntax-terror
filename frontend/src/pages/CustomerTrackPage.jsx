import React, { useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import LeafletMap from '../components/Map/LeafletMap';
import TrackingTimeline from '../components/TrackingTimeline';
import { usePolling } from '../hooks/usePolling';
import { api, ApiError } from '../api/client';
import { formatLocalDateTime, formatLocalTime } from '../utils/formatters';

const HUB_COORDINATES = { latitude: 12.9716, longitude: 77.5946 };

export function CustomerTrackPage() {
  const { id } = useParams();

  const [request, setRequest] = useState(null);
  const [routeGeometry, setRouteGeometry] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelMessage, setCancelMessage] = useState(null);
  const [cancelError, setCancelError] = useState(null);

  // Poll GET /requests/{id} every 30 seconds (30000ms)
  const fetchRequestDetails = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api.getRequest(id);
      setRequest(data);
      setError(null);

      // Fetch followable road route from pickup to hub
      if (data && data.latitude != null && data.longitude != null) {
        try {
          const coords = [
            [data.latitude, data.longitude],
            [HUB_COORDINATES.latitude, HUB_COORDINATES.longitude],
          ];
          const geom = await api.fetchRoute(coords);
          if (Array.isArray(geom) && geom.length >= 2) {
            setRouteGeometry(geom);
          } else {
            setRouteGeometry(coords);
          }
        } catch {
          // Straight-line fallback on error / timeout
          setRouteGeometry([
            [data.latitude, data.longitude],
            [HUB_COORDINATES.latitude, HUB_COORDINATES.longitude],
          ]);
        }
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === 'REQUEST_NOT_FOUND') {
        setError(`Pickup request "${id}" was not found.`);
      } else {
        setError(err.message || 'Failed to fetch request details.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [id]);


  usePolling(fetchRequestDetails, 30000, Boolean(id));

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel this pickup request?')) {
      return;
    }

    setIsCancelling(true);
    setCancelError(null);
    setCancelMessage(null);

    try {
      const res = await api.cancelRequest(id);
      setCancelMessage(res.message || 'Request cancelled successfully');
      await fetchRequestDetails();
    } catch (err) {
      setCancelError(err.message || 'Unable to cancel pickup request');
    } finally {
      setIsCancelling(false);
    }
  };

  const canCancel =
    request && ['Pending', 'Scheduled', 'Unassigned'].includes(request.status);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-gray-200">
          <div>
            <div className="text-xs text-gray-500 mb-0.5">
              <Link to="/" className="text-blue-600 hover:underline">
                &larr; Back to Requests
              </Link>
            </div>
            <h1 className="text-xl font-bold text-gray-900">
              Pickup Request Tracking
            </h1>
          </div>

          {canCancel && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={isCancelling}
              className="px-3.5 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-md text-xs font-medium shadow-sm transition-colors disabled:opacity-50"
            >
              {isCancelling ? 'Cancelling...' : 'Cancel Request'}
            </button>
          )}
        </div>

        {cancelMessage && (
          <div className="p-3 rounded-md bg-green-50 border border-green-200 text-xs text-green-800">
            ✓ {cancelMessage}
          </div>
        )}

        {cancelError && (
          <div className="p-3 rounded-md bg-red-50 border border-red-200 text-xs text-red-800">
            ⚠️ {cancelError}
          </div>
        )}

        {isLoading && !request ? (
          <div className="py-20 text-center text-xs text-gray-500">
            Loading request details...
          </div>
        ) : error ? (
          <div className="bg-white border border-gray-200 rounded-lg p-6 text-center space-y-3">
            <h3 className="text-sm font-semibold text-gray-900">Unable to Load Request</h3>
            <p className="text-xs text-gray-600">{error}</p>
            <Link
              to="/"
              className="inline-block px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-md text-xs font-medium"
            >
              Back to Request Form
            </Link>
          </div>
        ) : request ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Details & Timeline */}
            <div className="lg:col-span-2 space-y-6">
              {/* Request Details Card */}
              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                  <div>
                    <h2 className="text-sm font-semibold text-gray-900">
                      Request Details
                    </h2>
                    <span className="text-[11px] font-mono text-gray-500">
                      ID: {request.id}
                    </span>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      request.status === 'Cancelled'
                        ? 'bg-gray-100 text-gray-700'
                        : request.status === 'Unassigned'
                        ? 'bg-red-100 text-red-700'
                        : request.status === 'Delivered to hub' || request.status === 'Delivered'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {request.status}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                    <span className="text-gray-500 block text-[10px] uppercase font-semibold">Customer</span>
                    <span className="text-gray-900 font-medium">{request.customer_name}</span>
                    <span className="text-gray-500 block mt-0.5">{request.phone}</span>
                  </div>

                  <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                    <span className="text-gray-500 block text-[10px] uppercase font-semibold">Requested Window</span>
                    <span className="text-gray-900 font-medium">{formatLocalDateTime(request.window_start)}</span>
                    <span className="text-gray-500 block mt-0.5">to {formatLocalTime(request.window_end)}</span>
                  </div>

                  <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                    <span className="text-gray-500 block text-[10px] uppercase font-semibold">Priority</span>
                    <span className="text-gray-900 capitalize font-medium">{request.priority}</span>
                    {request.scheduled_time && (
                      <span className="text-blue-700 block mt-0.5">
                        Scheduled: {formatLocalTime(request.scheduled_time)}
                      </span>
                    )}
                  </div>

                  <div className="p-3 bg-gray-50 rounded-md border border-gray-100">
                    <span className="text-gray-500 block text-[10px] uppercase font-semibold">Pickup Address</span>
                    <span className="text-gray-900 font-medium block truncate">{request.address}</span>
                    <span className="text-gray-500 font-mono text-[10px] block mt-0.5">
                      {request.latitude?.toFixed(4)}, {request.longitude?.toFixed(4)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Status Timeline */}
              <TrackingTimeline
                history={request.status_history || []}
                currentStatus={request.status}
              />
            </div>

            {/* Right Column: Mini Map showing pickup -> hub route (green polyline) */}
            <div className="space-y-4">
              <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm flex flex-col h-full">
                <div className="border-b border-gray-100 pb-2 mb-3">
                  <h3 className="text-xs font-semibold text-gray-900">
                    Route Map (Pickup to Hub)
                  </h3>
                  <p className="text-[11px] text-gray-500">
                    Pickup pin connected to central sorting hub
                  </p>
                </div>

                <div className="relative flex-1 min-h-[300px] rounded-md overflow-hidden border border-gray-200">
                  <LeafletMap
                    center={[request.latitude || HUB_COORDINATES.latitude, request.longitude || HUB_COORDINATES.longitude]}
                    zoom={13}
                    geometry={
                      routeGeometry || (
                        request.latitude && request.longitude
                          ? [
                              [request.latitude, request.longitude],
                              [HUB_COORDINATES.latitude, HUB_COORDINATES.longitude],
                            ]
                          : null
                      )
                    }
                    routeColor="#16a34a"
                    routeWeight={4}
                    routeOpacity={0.8}
                    markers={[

                      {
                        id: 'pickup-coord',
                        lat: request.latitude,
                        lng: request.longitude,
                        color: '#16a34a', // Green pickup marker
                        popupContent: (
                          <div className="text-xs">
                            <strong>{request.customer_name}</strong>
                            <p>{request.address}</p>
                          </div>
                        ),
                      },
                      {
                        id: 'central-hub-coord',
                        lat: HUB_COORDINATES.latitude,
                        lng: HUB_COORDINATES.longitude,
                        type: 'Hub',
                        popupContent: <div className="text-xs"><strong>Central Hub</strong></div>,
                      },
                    ]}
                  />
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}

export default CustomerTrackPage;
