import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { DataProvider } from './context/DataContext';
import CustomerPage from './pages/CustomerPage';
import CustomerTrackPage from './pages/CustomerTrackPage';
import AgentPage from './pages/AgentPage';

/**
 * Exactly 3 routes per frontend-spec.md Section 3:
 * 1. /          -> CustomerPage (Auth: No)
 * 2. /track/:id -> CustomerTrackPage (Auth: No)
 * 3. /agent     -> AgentPage (Auth: Yes)
 */
export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <DataProvider>
          <Routes>
            <Route path="/" element={<CustomerPage />} />
            <Route path="/track/:id" element={<CustomerTrackPage />} />
            <Route path="/agent" element={<AgentPage />} />
            {/* Catch-all redirect to CustomerPage */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </DataProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
