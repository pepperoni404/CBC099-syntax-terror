import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import RequestForm from '../components/RequestForm';

export function CustomerPage() {
  const [trackId, setTrackId] = useState('');
  const [trackError, setTrackError] = useState('');
  const navigate = useNavigate();

  const handleTrack = (e) => {
    e.preventDefault();
    const cleanId = trackId.trim();
    if (!cleanId) {
      setTrackError('Please enter a Request ID');
      return;
    }
    navigate(`/track/${cleanId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            Courier Pickup Scheduling
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Schedule an on-demand courier pickup within your designated service window.
          </p>
        </div>

        {/* Request Form */}
        <RequestForm />

        {/* Tracking Lookup Section */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            Track Existing Pickup Request
          </h3>
          <p className="text-xs text-gray-500 mb-4">
            Enter your pickup Request ID to view live status updates and route milestones.
          </p>

          <form onSubmit={handleTrack} className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <input
                type="text"
                value={trackId}
                onChange={(e) => {
                  setTrackId(e.target.value);
                  if (trackError) setTrackError('');
                }}
                placeholder="Enter 36-character Request UUID"
                className="w-full bg-white border border-gray-300 focus:border-blue-500 rounded-md px-3 py-2 text-xs text-gray-900 font-mono placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              {trackError && <p className="text-red-600 text-xs mt-1">{trackError}</p>}
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-gray-800 hover:bg-gray-900 text-white font-medium rounded-md text-xs shadow-sm transition-colors shrink-0"
            >
              Track Request
            </button>
          </form>
        </div>
      </main>

      <footer className="border-t border-gray-200 py-4 text-center text-xs text-gray-500">
        Smart Courier Pickup Scheduling System &copy; 2026
      </footer>
    </div>
  );
}

export default CustomerPage;
