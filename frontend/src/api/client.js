/**
 * Centralized API client for Smart Courier Pickup Scheduling System.
 * Matches exact endpoints and error handling from integration-guide.md Section 2.
 */

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export const ERROR_MESSAGES = {
  INVALID_WINDOW: 'window_end must be after window_start',
  WINDOW_IN_PAST: 'window_start must be in the future',
  NO_AGENT_AVAILABLE: 'No agent is available during the requested time window',
  INVALID_PRIORITY: 'priority must be one of: urgent, normal, low',
  INVALID_COORDINATES: 'latitude must be between -90 and 90, and longitude between -180 and 180',
  INVALID_CREDENTIALS: 'Invalid username or password',
  TOKEN_EXPIRED: 'Authentication token has expired. Please log in again.',
  NOT_AUTHENTICATED: 'Authentication required. Please log in.',
  NOT_ASSIGNED: 'You are not assigned to this request',
  INVALID_TRANSITION: 'Invalid status transition',
  REQUEST_NOT_FOUND: 'Pickup request not found',
  AGENT_NOT_FOUND: 'Agent not found',
  INTERNAL_ERROR: 'Internal server error. Please try again later.',
};

export class ApiError extends Error {
  constructor(code, message, field = null, status = 500) {
    const fallbackMessage = ERROR_MESSAGES[code] || message || 'An unexpected error occurred';
    super(fallbackMessage);
    this.name = 'ApiError';
    this.code = code || 'INTERNAL_ERROR';
    this.field = field;
    this.status = status;
  }
}

async function apiFetch(path, options = {}) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${API_BASE}${normalizedPath}`;
  const token = localStorage.getItem('agent_token');

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr) {
    throw new ApiError(
      'NETWORK_ERROR',
      `Unable to reach backend at ${API_BASE}. Please check your connection or ensure backend is running.`,
      null,
      0
    );
  }

  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const errCode = data?.error?.code || (response.status === 401 ? 'NOT_AUTHENTICATED' : 'INTERNAL_ERROR');
    const errMessage = data?.error?.message || response.statusText || 'Request failed';
    const errField = data?.error?.field || null;

    // Handle token expiration or unauthorized
    if (response.status === 401 && (errCode === 'TOKEN_EXPIRED' || errCode === 'NOT_AUTHENTICATED')) {
      if (token && errCode === 'TOKEN_EXPIRED') {
        localStorage.removeItem('agent_token');
      }
    }

    throw new ApiError(errCode, errMessage, errField, response.status);
  }

  return data;
}

export const api = {
  // 3.1 Authentication
  login: async (credentials) => {
    return apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  },

  getMe: async () => {
    return apiFetch('/auth/me');
  },

  // 3.2 Requests
  createRequest: async (requestData) => {
    // Ensures coordinates are strictly { latitude, longitude }
    const payload = {
      customer_name: requestData.customer_name,
      phone: requestData.phone,
      address: requestData.address,
      latitude: Number(requestData.latitude),
      longitude: Number(requestData.longitude),
      window_start: requestData.window_start,
      window_end: requestData.window_end,
      priority: requestData.priority || 'normal',
    };
    return apiFetch('/requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getRequests: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.agent_id) query.append('agent_id', params.agent_id);
    if (params.date) query.append('date', params.date);

    const queryString = query.toString();
    const endpoint = queryString ? `/requests?${queryString}` : '/requests';
    return apiFetch(endpoint);
  },

  getRequest: async (id) => {
    return apiFetch(`/requests/${id}`);
  },

  cancelRequest: async (id) => {
    return apiFetch(`/requests/${id}/cancel`, {
      method: 'PATCH',
    });
  },

  updateStatus: async (id, status) => {
    return apiFetch(`/requests/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  // 3.3 Agents
  getAgents: async () => {
    return apiFetch('/agents');
  },

  getAgentSchedule: async (id) => {
    return apiFetch(`/agents/${id}/schedule`);
  },

  // 3.4 Scheduler
  runScheduler: async () => {
    return apiFetch('/schedule/run', {
      method: 'POST',
    });
  },

  // 3.5 Demo actions
  seedDemo: async (reset = false) => {
    const endpoint = reset ? '/demo/seed?reset=true' : '/demo/seed';
    return apiFetch(endpoint, {
      method: 'POST',
    });
  },

  createUrgent: async () => {
    return apiFetch('/demo/urgent', {
      method: 'POST',
    });
  },
};
