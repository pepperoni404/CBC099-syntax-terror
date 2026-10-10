# Frontend Specification: Smart Courier Pickup Scheduling System

**Date:** 2026-10-10
**Status:** Draft for review

---

## 1. Architecture Overview

`
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    React App                             │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │    │
│  │  │ AuthContext │  │ DataContext │  │ React Router v6 │  │    │
│  │  │  (useReducer)│  │  (useReducer)│  │                 │  │    │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │    │
│  │         │                │                   │           │    │
│  │         └────────────────┴───────────────────┘           │    │
│  │                          │                               │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │    │
│  │  │Customer  │  │Customer  │  │Dispatcher│  │  Agent   │ │    │
│  │  │FormPage  │  │TrackPage │  │  Page    │  │  Page    │ │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
`

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 18+ |
| Routing | React Router | v6 |
| State Management | Context API + useReducer | Built-in |
| Styling | Tailwind CSS | v3+ |
| Map | Leaflet + react-leaflet | v4+ |
| HTTP Client | Fetch API | Built-in |
| Build Tool | Vite | v5+ |

---

## 2. Routing

### 2.1 Route Definitions

| Path | Page | Auth Required | Description |
|------|------|---------------|-------------|
| / | CustomerPage | No | Customer request form |
| /track/:id | CustomerTrackPage | No | Customer tracking page |
| /dispatcher | DispatcherPage | No | Dispatcher map + calendar |
| /agent | AgentPage | Yes | Agent login + dashboard |

### 2.2 Route Configuration

`jsx
// App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { DataProvider } from './context/DataContext';
import CustomerPage from './pages/CustomerPage';
import CustomerTrackPage from './pages/CustomerTrackPage';
import DispatcherPage from './pages/DispatcherPage';
import AgentPage from './pages/AgentPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <DataProvider>
          <Routes>
            <Route path="/" element={<CustomerPage />} />
            <Route path="/track/:id" element={<CustomerTrackPage />} />
            <Route path="/dispatcher" element={<DispatcherPage />} />
            <Route path="/agent" element={<AgentPage />} />
          </Routes>
        </DataProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
`

---

## 3. State Management

### 3.1 AuthContext

Manages agent authentication state.

`javascript
// context/AuthContext.jsx
const AuthContext = createContext(null);

const initialState = {
  token: localStorage.getItem('agent_token') || null,
  agent: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

function authReducer(state, action) {
  switch (action.type) {
    case 'LOGIN_START':
      return { ...state, isLoading: true, error: null };
    case 'LOGIN_SUCCESS':
      return { ...state, isLoading: false, token: action.payload.token, agent: action.payload.agent, isAuthenticated: true };
    case 'LOGIN_FAILURE':
      return { ...state, isLoading: false, error: action.payload.error };
    case 'LOGOUT':
      return { ...initialState, token: null };
    default:
      return state;
  }
}
`

### 3.2 DataContext

Manages application data (requests, agents) with 30-second polling.

`javascript
// context/DataContext.jsx
const DataContext = createContext(null);

const initialState = {
  requests: [],
  agents: [],
  unassigned: [],
  schedule: [],
  isPolling: false,
  lastUpdated: null,
  osrmStatus: 'unknown', // 'osrm' | 'estimated' | 'error'
};

function dataReducer(state, action) {
  switch (action.type) {
    case 'SET_REQUESTS':
      return { ...state, requests: action.payload, lastUpdated: new Date() };
    case 'SET_AGENTS':
      return { ...state, agents: action.payload };
    case 'SET_UNASSIGNED':
      return { ...state, unassigned: action.payload };
    case 'SET_SCHEDULE':
      return { ...state, schedule: action.payload };
    case 'SET_OSRM_STATUS':
      return { ...state, osrmStatus: action.payload };
    case 'UPDATE_REQUEST_STATUS':
      return {
        ...state,
        requests: state.requests.map(r =>
          r.id === action.payload.id ? { ...r, ...action.payload } : r
        )
      };
    default:
      return state;
  }
}
`

### 3.3 Polling Strategy

- **Dispatcher and Agent pages**: Poll every 30 seconds
- **Customer tracking page**: Poll every 30 seconds
- **Customer form page**: No polling (one-time submission)

`javascript
// hooks/usePolling.js
function usePolling(callback, interval = 30000, enabled = true) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    const tick = () => savedCallback.current();
    const id = setInterval(tick, interval);
    tick(); // Immediate first call
    return () => clearInterval(id);
  }, [interval, enabled]);
}
`

---

## 4. Component Hierarchy

`
src/
├── context/
│   ├── AuthContext.jsx
│   └── DataContext.jsx
├── components/
│   ├── Map/
│   │   ├── LeafletMap.jsx
│   │   └── MarkerLayer.jsx
│   ├── RequestForm.jsx
│   ├── TrackingTimeline.jsx
│   ├── DispatcherCalendar.jsx
│   ├── AgentSchedule.jsx
│   └── StatusButton.jsx
├── pages/
│   ├── CustomerPage.jsx
│   ├── CustomerTrackPage.jsx
│   ├── DispatcherPage.jsx
│   └── AgentPage.jsx
├── hooks/
│   ├── usePolling.js
│   └── useAuth.js
├── api/
│   └── client.js
├── App.jsx
└── main.jsx
`

---

## 5. Page Specifications

### 5.1 CustomerPage (/)

**Purpose:** Allow customers to submit pickup requests.

**Layout:**
`
┌─────────────────────────────────────────┐
│           Header / Nav                  │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │      Request Form               │    │
│  │  - Customer Name                │    │
│  │  - Phone Number                 │    │
│  │  - Address                      │    │
│  │  - Map Pin Picker (Leaflet)     │    │
│  │  - Window Start (datetime)      │    │
│  │  - Window End (datetime)        │    │
│  │  - Priority (select)            │    │
│  │  - Submit Button                │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │      Tracking Section            │    │
│  │  - Input: Request ID            │    │
│  │  - Button: Track                │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
`

**Form Fields:**

| Field | Type | Validation |
|-------|------|------------|
| customer_name | text | Required, max 100 chars |
| phone | tel | Required, valid phone format |
| address | text | Required, max 255 chars |
| latitude | hidden | Set by map pin |
| longitude | hidden | Set by map pin |
| window_start | datetime-local | Required, must be future |
| window_end | datetime-local | Required, must be after start |
| priority | select | urgent / normal / low |

**On Submit:**
1. Validate all fields
2. POST /requests with form data
3. On success: show confirmation with request ID and tracking link
4. On error: show specific validation error message

**Components Used:**
- RequestForm.jsx — form with validation
- LeafletMap.jsx — map for pin selection

---

### 5.2 CustomerTrackPage (/track/:id)

**Purpose:** Show live status and history for a pickup request.

**Layout:**
`
┌─────────────────────────────────────────┐
│           Header / Nav                  │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │     Request Details              │    │
│  │  - Customer: John Doe            │    │
│  │  - Address: 123 Main St          │    │
│  │  - Window: 2:00 PM - 4:00 PM    │    │
│  │  - Status: Scheduled             │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │     Status Timeline              │    │
│  │  ● Pending        10:00 AM      │    │
│  │  ● Scheduled        10:05 AM      │    │
│  │  ○ En route      --:--         │    │
│  │  ○ Picked up     --:--         │    │
│  │  ○ Delivered     --:--         │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │     Mini Map                     │    │
│  │  - Pickup location marker        │    │
│  │  - Hub location marker           │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
`

**Polling:** Every 30 seconds, fetch GET /requests/{id}

**Components Used:**
- TrackingTimeline.jsx — visual timeline of status changes
- LeafletMap.jsx — mini map showing pickup and hub

---

### 5.3 DispatcherPage (/dispatcher)

**Purpose:** Overview of all pickups, agents, and schedules. This is the main demo screen.

**Layout:**
`
┌─────────────────────────────────────────────────────────────┐
│                    Header / Nav                              │
│  [Seed Demo] [Run Scheduler] [Create Urgent]                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌───────────────────────┐  │
│  │                             │  │   Agent Calendar      │  │
│  │      Leaflet Map            │  │                       │  │
│  │                             │  │   Agent 1             │  │
│  │  - Pickup markers           │  │   [====] [==] [===]   │  │
│  │    colored by status        │  │                       │  │
│  │  - Agent markers            │  │   Agent 2             │  │
│  │  - Hub marker               │  │   [==] [====] [==]    │  │
│  │  - Route polylines          │  │                       │  │
│  │                             │  │   Agent 3             │  │
│  │  - Estimated times badge    │  │   [===] [==] [====]   │  │
│  │    (if OSRM fallback)       │  │                       │  │
│  └─────────────────────────────┘  └───────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Unassigned Requests                     │   │
│  │  - John Doe - No agent available - Suggest: Tomorrow │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
`

**Map Markers:**

| Marker | Color | Description |
|--------|-------|-------------|
| Pending | Orange | Unscheduled pickup |
| Scheduled | Blue | Assigned to agent |
| En route | Purple | Agent heading to pickup |
| Picked up | Green | Parcel collected |
| Delivered | Dark Green | Delivered to hub |
| Unassigned | Red | No agent available |
| Cancelled | Gray | Cancelled |
| Agent | Black | Agent current location |
| Hub | Gold | Fixed hub location |

**Polling:** Every 30 seconds, fetch GET /requests and GET /agents

**Action Buttons:**
- **Seed Demo**: POST /demo/seed
- **Run Scheduler**: POST /schedule/run
- **Create Urgent**: POST /demo/urgent

**Components Used:**
- LeafletMap.jsx — main map with markers and routes
- DispatcherCalendar.jsx — agent schedule timeline
- MarkerLayer.jsx — colored markers for pickups and agents

---

### 5.4 AgentPage (/agent)

**Purpose:** Agent login and daily schedule dashboard.

**Layout (Not Logged In):**
`
┌─────────────────────────────────────────┐
│           Agent Login                    │
│                                         │
│  Username: [_______________]            │
│  Password: [_______________]            │
│                                         │
│  [Login Button]                         │
│                                         │
│  Error: Invalid credentials             │
└─────────────────────────────────────────┘
`

**Layout (Logged In):**
`
┌─────────────────────────────────────────┐
│  Agent 1                    [Logout]    │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │     Today's Schedule             │    │
│  │                                  │    │
│  │  1. John Doe                     │    │
│  │     123 Main St                  │    │
│  │     Scheduled: 2:30 PM          │    │
│  │     [En route]                  │    │
│  │                                  │    │
│  │  2. Jane Smith                   │    │
│  │     456 Oak Ave                  │    │
│  │     Scheduled: 3:00 PM          │    │
│  │     [En route] [Picked up]      │    │
│  │                                  │    │
│  │  3. Bob Wilson                   │    │
│  │     789 Pine Rd                  │    │
│  │     Scheduled: 4:00 PM          │    │
│  │     [En route] [Picked up]      │    │
│  │                  [Delivered]    │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │     Next Stop Map                │    │
│  │     (small Leaflet map)          │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
`

**Status Buttons:**

| Current Status | Available Buttons |
|---------------|-------------------|
| Scheduled | En route |
| En route | Picked up |
| Picked up | Delivered to hub |

**Polling:** Every 30 seconds, fetch GET /agents/{id}/schedule

**Components Used:**
- AgentSchedule.jsx — ordered pickup list with action buttons
- StatusButton.jsx — contextual action buttons
- LeafletMap.jsx — mini map of next stop

---

## 6. Component Specifications

### 6.1 LeafletMap.jsx

Reusable map component for all map displays.

`jsx
// components/Map/LeafletMap.jsx
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function LeafletMap({ center, zoom = 13, markers = [], polylines = [], onMapClick, children }) {
  return (
    <MapContainer center={center} zoom={zoom} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {markers.map(marker => (
        <Marker key={marker.id} position={[marker.lat, marker.lng]}>
          <Popup>{marker.popupContent}</Popup>
        </Marker>
      ))}
      {polylines.map((polyline, idx) => (
        <Polyline key={idx} positions={polyline.positions} color={polyline.color} />
      ))}
      {children}
    </MapContainer>
  );
}
`

### 6.2 RequestForm.jsx

Customer pickup request form.

`jsx
// components/RequestForm.jsx
function RequestForm() {
  const [formData, setFormData] = useState({
    customer_name: '',
    phone: '',
    address: '',
    latitude: null,
    longitude: null,
    window_start: '',
    window_end: '',
    priority: 'normal'
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [requestId, setRequestId] = useState(null);

  // Form validation
  // Map click handler
  // Submit handler
  // Error display
}
`

### 6.3 TrackingTimeline.jsx

Visual timeline of status history.

`jsx
// components/TrackingTimeline.jsx
const STATUS_ORDER = ['Pending', 'Scheduled', 'En route', 'Picked up', 'Delivered to hub'];
const STATUS_COLORS = {
  'Pending': 'bg-orange-500',
  'Scheduled': 'bg-blue-500',
  'En route': 'bg-purple-500',
  'Picked up': 'bg-green-500',
  'Delivered to hub': 'bg-green-700',
  'Unassigned': 'bg-red-500',
  'Cancelled': 'bg-gray-500'
};

function TrackingTimeline({ history, currentStatus }) {
  // Render vertical timeline with dots and connecting lines
  // Show timestamp for each status
}
`

### 6.4 DispatcherCalendar.jsx

Agent schedule timeline for dispatcher view.

`jsx
// components/DispatcherCalendar.jsx
function DispatcherCalendar({ agents, requests }) {
  // Render horizontal timeline for each agent
  // Show scheduled pickups as blocks
  // Color-code by status
}
`

### 6.5 AgentSchedule.jsx

Agent's ordered pickup list with action buttons.

`jsx
// components/AgentSchedule.jsx
function AgentSchedule({ schedule, onStatusUpdate }) {
  // Render ordered list of pickups
  // Show contextual action buttons based on current status
  // Call PATCH /requests/{id}/status on button click
}
`

### 6.6 StatusButton.jsx

Contextual status update button.

`jsx
// components/StatusButton.jsx
const NEXT_ACTIONS = {
  'Scheduled': { next: 'En route', label: 'En route', color: 'purple' },
  'En route': { next: 'Picked up', label: 'Picked up', color: 'green' },
  'Picked up': { next: 'Delivered to hub', label: 'Delivered', color: 'green' }
};

function StatusButton({ currentStatus, onUpdate, disabled }) {
  const action = NEXT_ACTIONS[currentStatus];
  if (!action) return null;
  // Render button with appropriate color and label
}
`

---

## 7. API Client

### 7.1 api/client.js

Centralized API client with error handling.

`javascript
// api/client.js
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function apiFetch(path, options = {}) {
  const url = ${API_BASE};
  const token = localStorage.getItem('agent_token');

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = Bearer ;
  }

  const response = await fetch(url, { ...options, headers });
  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(data.error.code, data.error.message, data.error.field);
  }

  return data;
}

export const api = {
  login: (credentials) => apiFetch('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  getMe: () => apiFetch('/auth/me'),
  createRequest: (data) => apiFetch('/requests', { method: 'POST', body: JSON.stringify(data) }),
  getRequests: (params) => apiFetch(/requests?),
  getRequest: (id) => apiFetch(/requests/),
  cancelRequest: (id) => apiFetch(/requests//cancel, { method: 'PATCH' }),
  updateStatus: (id, status) => apiFetch(/requests//status, { method: 'PATCH', body: JSON.stringify({ status }) }),
  getAgents: () => apiFetch('/agents'),
  getAgentSchedule: (id) => apiFetch(/agents//schedule),
  runScheduler: () => apiFetch('/schedule/run', { method: 'POST' }),
  seedDemo: () => apiFetch('/demo/seed', { method: 'POST' }),
  createUrgent: () => apiFetch('/demo/urgent', { method: 'POST' }),
};

class ApiError extends Error {
  constructor(code, message, field) {
    super(message);
    this.code = code;
    this.field = field;
  }
}
`

---

## 8. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| VITE_API_URL | http://localhost:8000 | Backend API base URL |

---

## 9. Project Structure

`
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Map/
│   │   │   ├── LeafletMap.jsx
│   │   │   └── MarkerLayer.jsx
│   │   ├── RequestForm.jsx
│   │   ├── TrackingTimeline.jsx
│   │   ├── DispatcherCalendar.jsx
│   │   ├── AgentSchedule.jsx
│   │   └── StatusButton.jsx
│   ├── context/
│   │   ├── AuthContext.jsx
│   │   └── DataContext.jsx
│   ├── hooks/
│   │   ├── usePolling.js
│   │   └── useAuth.js
│   ├── pages/
│   │   ├── CustomerPage.jsx
│   │   ├── CustomerTrackPage.jsx
│   │   ├── DispatcherPage.jsx
│   │   └── AgentPage.jsx
│   ├── api/
│   │   └── client.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
├── tailwind.config.js
├── vite.config.js
└── Dockerfile
`

---

## 10. Package Dependencies

`json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "vite": "^5.0.0"
  }
}
`

---

## 11. Deployment

### 11.1 Vite Config

`javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
});
`

### 11.2 CORS

Backend must allow http://localhost:3000 in development via ALLOWED_ORIGINS environment variable.

---

*End of Frontend Specification*
