import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import LeafletMap from './Map/LeafletMap';

const DEFAULT_WINDOWS = () => {
  const now = new Date();
  const start = new Date(now.getTime() + 2 * 60 * 60 * 1000);
  const end = new Date(now.getTime() + 4 * 60 * 60 * 1000);

  const format = (d) => {
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  return {
    window_start: format(start),
    window_end: format(end),
  };
};

export function RequestForm() {
  const defaults = DEFAULT_WINDOWS();

  const [formData, setFormData] = useState({
    customer_name: '',
    address: '',
    latitude: 12.9716,
    longitude: 77.5946,
    window_start: defaults.window_start,
    window_end: defaults.window_end,
    priority: 'normal',
  });

  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedRequest, setSubmittedRequest] = useState(null);
  const [copied, setCopied] = useState(false);

  const validate = () => {
    const errs = {};
    if (!formData.customer_name.trim()) errs.customer_name = 'Customer name is required';
    if (!formData.address.trim()) errs.address = 'Address is required';

    if (formData.latitude == null || formData.longitude == null) {
      errs.coordinates = 'Please choose a location on the map';
    } else {
      if (formData.latitude < -90 || formData.latitude > 90) errs.coordinates = 'Latitude must be between -90 and 90';
      if (formData.longitude < -180 || formData.longitude > 180) errs.coordinates = 'Longitude must be between -180 and 180';
    }

    if (!formData.window_start) {
      errs.window_start = 'Window start is required';
    } else if (new Date(formData.window_start) <= new Date()) {
      errs.window_start = 'window_start must be in the future';
    }

    if (!formData.window_end) {
      errs.window_end = 'Window end is required';
    } else if (formData.window_start && new Date(formData.window_end) <= new Date(formData.window_start)) {
      errs.window_end = 'window_end must be after window_start';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: null }));
    if (generalError) setGeneralError(null);
  };

  const handleMapClick = (coords) => {
    setFormData((prev) => ({
      ...prev,
      latitude: coords.latitude,
      longitude: coords.longitude,
    }));
    if (errors.coordinates) setErrors((prev) => ({ ...prev, coordinates: null }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setGeneralError(null);
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const payload = {
        customer_name: formData.customer_name.trim(),
        address: formData.address.trim(),
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
        window_start: new Date(formData.window_start).toISOString(),
        window_end: new Date(formData.window_end).toISOString(),
        priority: formData.priority,
      };

      const res = await api.createRequest(payload);
      setSubmittedRequest(res);
    } catch (err) {
      if (err instanceof ApiError && err.field) {
        setErrors((prev) => ({ ...prev, [err.field]: err.message }));
      }
      setGeneralError(err.message || 'Failed to submit pickup request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (submittedRequest?.id) {
      navigator.clipboard.writeText(submittedRequest.id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleReset = () => {
    const fresh = DEFAULT_WINDOWS();
    setFormData({
      customer_name: '',
      phone: '',
      address: '',
      latitude: 12.9716,
      longitude: 77.5946,
      window_start: fresh.window_start,
      window_end: fresh.window_end,
      priority: 'normal',
    });
    setErrors({});
    setGeneralError(null);
    setSubmittedRequest(null);
  };

  if (submittedRequest) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4 text-center">
        <div className="w-12 h-12 rounded-full bg-green-100 text-green-700 flex items-center justify-center mx-auto text-xl font-bold">
          ✓
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Pickup Request Created</h3>
        <p className="text-xs text-gray-600 max-w-md mx-auto">
          Your request was registered with status{' '}
          <span className="font-semibold text-gray-900">{submittedRequest.status}</span>.
        </p>

        <div className="max-w-md mx-auto bg-gray-50 border border-gray-200 rounded-md p-4 text-left space-y-2">
          <div className="text-xs text-gray-500">Request Tracking ID:</div>
          <div className="flex items-center justify-between gap-2 font-mono text-xs text-gray-900 bg-white p-2 border border-gray-200 rounded">
            <span className="break-all">{submittedRequest.id}</span>
            <button
              type="button"
              onClick={handleCopy}
              className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded shrink-0"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-center gap-3 pt-2">
          <Link
            to={`/track/${submittedRequest.id}`}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-medium shadow-sm transition-colors"
          >
            Track Status
          </Link>
          <button
            type="button"
            onClick={handleReset}
            className="px-4 py-2 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 rounded-md text-xs font-medium shadow-sm transition-colors"
          >
            Create Another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <div className="border-b border-gray-100 pb-4 mb-5">
        <h2 className="text-base font-semibold text-gray-900">Request a Courier Pickup</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Fill in your pickup address and select an available time window.
        </p>
      </div>

      {generalError && (
        <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-xs text-red-700">
          {generalError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Customer Name
          </label>
          <input
            type="text"
            name="customer_name"
            value={formData.customer_name}
            onChange={handleChange}
            placeholder="e.g. Aarav Sharma"
            maxLength={100}
            className={`w-full bg-white border ${
              errors.customer_name ? 'border-red-500' : 'border-gray-300'
            } rounded-md px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
          />
          {errors.customer_name && <p className="text-red-600 text-xs mt-1">{errors.customer_name}</p>}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Pickup Address
          </label>
          <input
            type="text"
            name="address"
            value={formData.address}
            onChange={handleChange}
            placeholder="Street address, building number, city"
            maxLength={255}
            className={`w-full bg-white border ${
              errors.address ? 'border-red-500' : 'border-gray-300'
            } rounded-md px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
          />
          {errors.address && <p className="text-red-600 text-xs mt-1">{errors.address}</p>}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Window Start
            </label>
            <input
              type="datetime-local"
              name="window_start"
              value={formData.window_start}
              onChange={handleChange}
              className={`w-full bg-white border ${
                errors.window_start ? 'border-red-500' : 'border-gray-300'
              } rounded-md px-3 py-2 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
            />
            {errors.window_start && <p className="text-red-600 text-xs mt-1">{errors.window_start}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Window End
            </label>
            <input
              type="datetime-local"
              name="window_end"
              value={formData.window_end}
              onChange={handleChange}
              className={`w-full bg-white border ${
                errors.window_end ? 'border-red-500' : 'border-gray-300'
              } rounded-md px-3 py-2 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
            />
            {errors.window_end && <p className="text-red-600 text-xs mt-1">{errors.window_end}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              name="priority"
              value={formData.priority}
              onChange={handleChange}
              className="w-full bg-white border border-gray-300 rounded-md px-3 py-2 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="normal">Normal</option>
              <option value="urgent">Urgent</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {/* Map Pin Picker */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-medium text-gray-700">
              Pickup Pin Location (Click map to adjust pin)
            </label>
            <span className="text-[11px] font-mono text-gray-500">
              {formData.latitude.toFixed(4)}, {formData.longitude.toFixed(4)}
            </span>
          </div>

          <div className="h-64 rounded-md overflow-hidden border border-gray-200">
            <LeafletMap
              center={[formData.latitude, formData.longitude]}
              zoom={13}
              onMapClick={handleMapClick}
              markers={[
                {
                  id: 'pickup-point',
                  lat: formData.latitude,
                  lng: formData.longitude,
                  color: '#2563eb',
                  popupContent: (
                    <div className="text-xs">
                      <strong>Selected Pickup Point</strong>
                      <p>{formData.address || 'Click to select location'}</p>
                    </div>
                  ),
                },
              ]}
            />
          </div>
          {errors.coordinates && <p className="text-red-600 text-xs mt-1">{errors.coordinates}</p>}
        </div>

        <div className="pt-2 flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-medium shadow-sm transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Pickup Request'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default RequestForm;
