import React, { createContext, useReducer, useCallback } from 'react';
import { api } from '../api/client';

export const DataContext = createContext(null);

const initialState = {
  requests: [],
  agents: [],
  unassigned: [],
  schedule: [],
  isPolling: false,
  lastUpdated: null,
  osrmStatus: 'unknown', // 'osrm' | 'estimated' | 'error'
  error: null,
};

function dataReducer(state, action) {
  switch (action.type) {
    case 'SET_REQUESTS': {
      const requests = Array.isArray(action.payload) ? action.payload : [];
      const unassigned = requests.filter(
        (r) => r.status === 'Unassigned' || (!r.assigned_agent_id && r.status === 'Pending')
      );
      return {
        ...state,
        requests,
        unassigned,
        lastUpdated: new Date(),
        error: null,
      };
    }
    case 'SET_AGENTS':
      return {
        ...state,
        agents: Array.isArray(action.payload) ? action.payload : [],
      };
    case 'SET_UNASSIGNED':
      return {
        ...state,
        unassigned: Array.isArray(action.payload) ? action.payload : [],
      };
    case 'SET_SCHEDULE':
      return {
        ...state,
        schedule: action.payload,
      };
    case 'SET_OSRM_STATUS':
      return {
        ...state,
        osrmStatus: action.payload,
      };
    case 'UPDATE_REQUEST_STATUS':
      return {
        ...state,
        requests: state.requests.map((r) =>
          r.id === action.payload.id ? { ...r, ...action.payload } : r
        ),
      };
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    default:
      return state;
  }
}

export function DataProvider({ children }) {
  const [state, dispatch] = useReducer(dataReducer, initialState);

  // Fetch all requests and agents for Dispatcher
  const refreshDispatcherData = useCallback(async () => {
    try {
      const [requestsData, agentsData] = await Promise.all([
        api.getRequests(),
        api.getAgents(),
      ]);
      dispatch({ type: 'SET_REQUESTS', payload: requestsData });
      dispatch({ type: 'SET_AGENTS', payload: agentsData });
      return { success: true };
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message });
      return { success: false, error: err.message };
    }
  }, []);

  const runSchedulerAction = async () => {
    try {
      const result = await api.runScheduler();
      await refreshDispatcherData();
      return { success: true, result };
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message });
      return { success: false, error: err.message };
    }
  };

  const seedDemoAction = async () => {
    try {
      const result = await api.seedDemo();
      await refreshDispatcherData();
      return { success: true, result };
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message });
      return { success: false, error: err.message };
    }
  };

  const createUrgentAction = async () => {
    try {
      const result = await api.createUrgent();
      await refreshDispatcherData();
      return { success: true, result };
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message });
      return { success: false, error: err.message };
    }
  };

  const cancelRequestAction = async (id) => {
    try {
      const result = await api.cancelRequest(id);
      dispatch({
        type: 'UPDATE_REQUEST_STATUS',
        payload: { id, status: 'Cancelled' },
      });
      return { success: true, result };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const updateRequestStatusAction = async (id, status) => {
    try {
      const result = await api.updateStatus(id, status);
      dispatch({
        type: 'UPDATE_REQUEST_STATUS',
        payload: { id, status: result.status },
      });
      return { success: true, result };
    } catch (err) {
      return { success: false, error: err.message };
    }
  };

  const setOsrmStatus = (status) => {
    dispatch({ type: 'SET_OSRM_STATUS', payload: status });
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  return (
    <DataContext.Provider
      value={{
        ...state,
        dispatch,
        refreshDispatcherData,
        runSchedulerAction,
        seedDemoAction,
        createUrgentAction,
        cancelRequestAction,
        updateRequestStatusAction,
        setOsrmStatus,
        clearError,
      }}
    >
      {children}
    </DataContext.Provider>
  );
}

export default DataContext;
