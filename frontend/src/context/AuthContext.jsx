import React, { createContext, useReducer, useEffect } from 'react';
import { api } from '../api/client';

export const AuthContext = createContext(null);

const initialState = {
  token: localStorage.getItem('agent_token') || null,
  agent: null,
  isAuthenticated: Boolean(localStorage.getItem('agent_token')),
  isLoading: false,
  error: null,
};

function authReducer(state, action) {
  switch (action.type) {
    case 'LOGIN_START':
      return { ...state, isLoading: true, error: null };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        isLoading: false,
        token: action.payload.token,
        agent: action.payload.agent,
        isAuthenticated: true,
        error: null,
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        isLoading: false,
        error: action.payload.error,
        isAuthenticated: false,
      };
    case 'SET_AGENT':
      return {
        ...state,
        agent: action.payload,
        isAuthenticated: true,
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    case 'LOGOUT':
      return {
        token: null,
        agent: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    default:
      return state;
  }
}

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Validate existing token on mount
  useEffect(() => {
    async function verifyAuth() {
      const token = localStorage.getItem('agent_token');
      if (!token) return;

      try {
        const agent = await api.getMe();
        dispatch({ type: 'SET_AGENT', payload: agent });
      } catch (err) {
        // Token expired or invalid
        localStorage.removeItem('agent_token');
        dispatch({ type: 'LOGOUT' });
      }
    }

    verifyAuth();
  }, []);

  const login = async (username, password) => {
    dispatch({ type: 'LOGIN_START' });
    try {
      const data = await api.login({ username, password });
      // JWT token from backend is in `access_token`
      const token = data.access_token;
      const agent = data.agent;

      localStorage.setItem('agent_token', token);

      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: { token, agent },
      });
      return { success: true, agent };
    } catch (err) {
      const errorMessage = err.message || 'Login failed. Please check your credentials.';
      dispatch({
        type: 'LOGIN_FAILURE',
        payload: { error: errorMessage },
      });
      return { success: false, error: errorMessage };
    }
  };

  const logout = () => {
    localStorage.removeItem('agent_token');
    dispatch({ type: 'LOGOUT' });
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export default AuthContext;
