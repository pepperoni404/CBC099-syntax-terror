import React, { useState, useCallback, useMemo } from 'react';
import Navbar from '../components/Navbar';
import LeafletMap, { isValidCoord } from '../components/Map/LeafletMap';
import AgentSchedule from '../components/AgentSchedule';
import StatusButton from '../components/StatusButton';
import { useAuth } from '../hooks/useAuth';
import { usePolling } from '../hooks/usePolling';
import { api, ApiError } from '../api/client';
import { formatLocalTime, formatDuration } from '../utils/formatters';

const HUB_LOCATION = { latitude: 12.9716, longitude: 77.5946 };

export function AgentPage() {
  const { isAuthenticated, agent, login, logout, isLoading: authLoading, error: authError } = useAuth();

  // Login form state
  const [username, setUsername] = useState('agent1');
  const [password, setPassword] = useState('courier123');
  const [loginError, setLoginError] = useState(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Agent schedule state
  const [scheduleData, setScheduleData] = useState(null);
  const [scheduleError, setScheduleError] = useState(null);
  const [selectedPickup, setSelectedPickup] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Fetch agent schedule: GET /agents/{id}/schedule
  const fetchSchedule = useCallback(async () => {
    if (!isAuthenticated || !agent?.id) return;
    try {
      const data = await api.getAgentSchedule(agent.id);
      setScheduleData(data);
      setScheduleError(null);
      setLastRefreshed(new Date());

      // Auto-select first active pickup if none currently selected
      if (!selectedPickup && data?.schedule?.length > 0) {
        const nextActive = data.schedule.find(
          (p) => p.status === 'En route' || p.status === 'Scheduled'
        ) || data.schedule[0];
        setSelectedPickup(nextActive);
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === 'TOKEN_EXPIRED') {
        logout();
      } else {
        setScheduleError(err.message || 'Failed to fetch agent schedule');
      }
    }
  }, [isAuthenticated, agent?.id, logout, selectedPickup]);

  // Polling every 30 seconds (30000ms) when authenticated per specification
  usePolling(fetchSchedule, 30000, isAuthenticated && Boolean(agent?.id));

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);

    try {
      const res = await login(username.trim(), password);
      if (!res.success) {
        setLoginError(res.error || 'Invalid credentials');
      }
    } catch (err) {
      setLoginError(err.message || 'Login failed');
    } finally {
      setIsLoggingIn(false);
    }
  };

  // Status update handler: PATCH /requests/{id}/status
  const handleStatusUpdate = async (requestId, nextStatus) => {
    try {
      await api.updateStatus(requestId, nextStatus);
      await fetchSchedule();
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message || 'Failed to update request status' };
    }
  };

  const scheduleList = scheduleData?.schedule || [];

  // Determine next active stop
  const nextStop = useMemo(() => {
    return (
      scheduleList.find((p) => p.status === 'En route') ||
      scheduleList.find((p) => p.status === 'Scheduled') ||
      scheduleList[0] ||
      null
    );
  }, [scheduleList]);

  // Safe agent location
  const agentLat = isValidCoord(agent?.current_location?.latitude)
    ? agent.current_location.latitude
    : HUB_LOCATION.latitude;
  const agentLng = isValidCoord(agent?.current_location?.longitude)
    ? agent.current_location.longitude
    : HUB_LOCATION.longitude;

  // Build full route polyline:
  // Agent location → first pickup → hub → second pickup → hub → ...
  const routePositions = useMemo(() => {
    const points = [[agentLat, agentLng]];
    scheduleList.forEach((pickup) => {
      const pLat = Number(pickup.latitude);
      const pLng = Number(pickup.longitude);
      if (isValidCoord(pLat) && isValidCoord(pLng)) {
        points.push([pLat, pLng]);
        points.push([HUB_LOCATION.latitude, HUB_LOCATION.longitude]);
      }
    });
    return points;
  }, [agentLat, agentLng, scheduleList]);

  // Map markers: Agent location, Hub, Pickups
  const mapMarkers = useMemo(() => {
    const markers = [
      {
        id: 'agent-pin',
        lat: agentLat,
        lng: agentLng,
        type: 'Agent',
        radius: 8,
        color: '#2563eb',
        popupContent: (
          <div className="text-xs">
            <div className="font-semibold text-gray-900">{agent?.name || 'Agent'}</div>
            <div className="text-gray-500 text-[11px]">Current Location</div>
          </div>
        ),
      },
      {
        id: 'hub-pin',
        lat: HUB_LOCATION.latitude,
        lng: HUB_LOCATION.longitude,
        type: 'Hub',
        radius: 8,
        color: '#4b5563',
        popupContent: (
          <div className="text-xs">
            <div className="font-semibold text-gray-900">Courier Sorting Hub</div>
            <div className="text-gray-500 text-[11px]">12.9716, 77.5946</div>
          </div>
        ),
      },
    ];

    scheduleList.forEach((p, idx) => {
      const pLat = Number(p.latitude);
      const pLng = Number(p.longitude);
      if (isValidCoord(pLat) && isValidCoord(pLng)) {
        const isNext = (nextStop?.id === p.id || nextStop?.request_id === p.request_id);
        markers.push({
          id: `stop-${p.id || p.request_id || idx}`,
          lat: pLat,
          lng: pLng,
          radius: isNext ? 10 : 7,
          color: isNext
            ? '#2563eb'
            : p.status === 'Delivered to hub'
            ? '#16a34a'
            : p.status === 'Picked up'
            ? '#16a34a'
            : p.status === 'En route'
            ? '#9333ea'
            : '#d97706',
          popupContent: (
            <div className="text-xs">
              <div className="font-semibold text-gray-900">
                #{idx + 1} {p.customer_name} {isNext && <span className="text-blue-600 font-bold">(Next Stop)</span>}
              </div>
              <div className="text-gray-600 text-[11px] mt-0.5">{p.address}</div>
              <div className="text-gray-500 text-[11px] mt-1 font-mono">
                Status: <strong className="font-sans text-gray-800">{p.status}</strong>
              </div>
              {p.scheduled_time && (
                <div className="text-gray-500 text-[11px] font-mono">
                  ETA: <strong className="font-sans text-gray-800">{formatLocalTime(p.scheduled_time)}</strong>
                </div>
              )}
            </div>
          ),
        });
      }
    });

    return markers;
  }, [agentLat, agentLng, agent?.name, scheduleList, nextStop]);

  // Center map on next stop or agent or hub
  const mapCenter = useMemo(() => {
    if (nextStop && isValidCoord(nextStop.latitude) && isValidCoord(nextStop.longitude)) {
      return [nextStop.latitude, nextStop.longitude];
    }
    return [agentLat, agentLng];
  }, [nextStop, agentLat, agentLng]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {!isAuthenticated ? (
          /* Clean Professional Login Card */
          <div className="max-w-md mx-auto my-12 bg-white border border-gray-200 rounded-lg p-6 sm:p-8 shadow-sm">
            <div className="text-center mb-6">
              <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-md flex items-center justify-center mx-auto mb-2 border border-blue-100 font-bold text-sm">
                AG
              </div>
              <h1 className="text-lg font-bold text-gray-900">Agent Portal Login</h1>
              <p className="text-xs text-gray-500 mt-1">
                Authenticate with your credentials to access your pickup schedule
              </p>
            </div>

            {(loginError || authError) && (
              <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-800 text-xs">
                ⚠️ {loginError || authError}
              </div>
            )}

            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="agent1"
                  className="w-full bg-white border border-gray-300 focus:border-blue-500 rounded-md px-3 py-2 text-xs text-gray-900 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="courier123"
                  className="w-full bg-white border border-gray-300 focus:border-blue-500 rounded-md px-3 py-2 text-xs text-gray-900 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <button
                type="submit"
                disabled={isLoggingIn || authLoading}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md shadow-sm text-xs transition-colors disabled:opacity-50"
              >
                {isLoggingIn ? 'Authenticating...' : 'Sign In as Agent'}
              </button>
            </form>

            {/* Quick Demo Credentials */}
            <div className="mt-6 pt-4 border-t border-gray-100 text-xs text-gray-500">
              <span className="block mb-2 font-medium text-gray-700">Quick Demo Select:</span>
              <div className="grid grid-cols-3 gap-2">
                {['agent1', 'agent2', 'agent3'].map((u) => (
                  <button
                    key={u}
                    type="button"
                    onClick={() => {
                      setUsername(u);
                      setPassword('courier123');
                    }}
                    className="py-1 px-2 bg-gray-50 hover:bg-gray-100 border border-gray-200 text-xs rounded text-gray-700 font-mono text-center transition-colors"
                  >
                    {u}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-gray-400 mt-2 text-center font-mono">Password: courier123</p>
            </div>
          </div>
        ) : (
          /* Authenticated Agent Dashboard */
          <div className="space-y-6">
            {/* Header: Agent info & Session Controls */}
            <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center space-x-2 text-xs text-gray-500 mb-1">
                  <span>Courier Field Terminal</span>
                  <span>•</span>
                  <span className="text-green-600 font-medium">Session Active</span>
                </div>
                <h1 className="text-xl font-bold text-gray-900 flex items-center space-x-3">
                  <span>{agent?.name || 'Courier Agent'}</span>
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-gray-100 text-gray-700 border border-gray-200">
                    Shift: {formatLocalTime(agent?.shift_start)} – {formatLocalTime(agent?.shift_end)}
                  </span>
                </h1>
              </div>

              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-md text-xs text-gray-600">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                  <span>Live (30s poll)</span>
                  {lastRefreshed && (
                    <span className="font-mono text-gray-400">
                      • {formatLocalTime(lastRefreshed.toISOString())}
                    </span>
                  )}
                </div>

                <button
                  onClick={logout}
                  className="px-3 py-1.5 bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 rounded-md text-xs font-medium shadow-sm transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>

            {/* Error Banner */}
            {scheduleError && (
              <div className="p-3.5 rounded-md bg-red-50 border border-red-200 text-red-800 text-xs">
                ⚠️ {scheduleError}
              </div>
            )}

            {/* Next Stop Highlighted Banner */}
            {nextStop && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-600 text-white">
                      Next Stop
                    </span>
                    <span className="text-sm font-semibold text-gray-900">
                      {nextStop.customer_name}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-100 text-blue-800">
                      {nextStop.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600">{nextStop.address}</p>
                  <div className="flex items-center space-x-4 text-[11px] text-gray-500 font-mono">
                    {nextStop.scheduled_time && (
                      <span>ETA: <strong className="font-sans text-gray-800">{formatLocalTime(nextStop.scheduled_time)}</strong></span>
                    )}
                    {nextStop.window_end && (
                      <span>Deadline: <strong className="font-sans text-gray-800">{formatLocalTime(nextStop.window_end)}</strong></span>
                    )}
                  </div>
                </div>

                <div className="shrink-0">
                  <StatusButton
                    currentStatus={nextStop.status}
                    onUpdate={(nextStatus) => handleStatusUpdate(nextStop.request_id || nextStop.id, nextStatus)}
                  />
                </div>
              </div>
            )}

            {/* Split View: Schedule List (left) + Full Route Map (right) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Ordered Pickup List */}
              <div className="lg:col-span-5">
                <AgentSchedule
                  schedule={scheduleList}
                  totalTravelTime={scheduleData?.total_travel_time_seconds}
                  isEstimatedTimes={scheduleData?.estimated_times}
                  onStatusUpdate={handleStatusUpdate}
                  selectedPickupId={selectedPickup?.request_id || selectedPickup?.id || nextStop?.request_id || nextStop?.id}
                  onSelectPickup={(pickup) => setSelectedPickup(pickup)}
                />
              </div>

              {/* Full Route Map */}
              <div className="lg:col-span-7">
                <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex flex-col h-full min-h-[500px]">
                  <div className="flex items-center justify-between pb-3 mb-3 border-b border-gray-100">
                    <div>
                      <h2 className="text-sm font-semibold text-gray-900">
                        Shift Route Map
                      </h2>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Blue polyline: Agent location → first pickup → hub → second pickup → hub...
                      </p>
                    </div>

                    <div className="flex items-center space-x-3 text-xs text-gray-600">
                      <span className="flex items-center space-x-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block"></span>
                        <span>Agent / Next</span>
                      </span>
                      <span className="flex items-center space-x-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-gray-600 inline-block"></span>
                        <span>Hub</span>
                      </span>
                      <span className="flex items-center space-x-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-green-600 inline-block"></span>
                        <span>Completed</span>
                      </span>
                    </div>
                  </div>

                  <div className="relative flex-1 min-h-[420px] rounded-md overflow-hidden border border-gray-200">
                    <LeafletMap
                      center={mapCenter}
                      zoom={13}
                      polylines={
                        routePositions.length > 1
                          ? [
                              {
                                positions: routePositions,
                                color: '#2563eb', // Blue polyline per specification
                                weight: 4,
                                opacity: 0.8,
                              },
                            ]
                          : []
                      }
                      markers={mapMarkers}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default AgentPage;
