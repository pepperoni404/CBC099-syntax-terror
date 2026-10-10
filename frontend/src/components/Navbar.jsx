import React from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function Navbar() {
  const { isAuthenticated, agent, logout } = useAuth();
  const navigate = useNavigate();

  const linkClass = ({ isActive }) =>
    `px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
      isActive
        ? 'bg-blue-50 text-blue-700'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
    }`;

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo / Brand */}
          <Link to="/" className="flex items-center space-x-2">
            <span className="w-6 h-6 rounded bg-blue-600 text-white flex items-center justify-center font-bold text-xs">
              C
            </span>
            <span className="text-sm font-semibold text-gray-900 tracking-tight">
              Smart Courier
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-2">
            <NavLink to="/" className={linkClass}>
              Request Pickup
            </NavLink>
            <NavLink to="/agent" className={linkClass}>
              Agent Portal
            </NavLink>
          </nav>

          {/* User state */}
          <div className="flex items-center space-x-2 text-xs">
            {isAuthenticated ? (
              <div className="flex items-center space-x-2">
                <span className="text-gray-700 font-medium">{agent?.name || 'Agent'}</span>
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    navigate('/agent');
                  }}
                  className="px-2.5 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded border border-gray-200 transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <Link
                to="/agent"
                className="px-3 py-1 bg-white hover:bg-gray-50 border border-gray-300 rounded text-gray-700 font-medium transition-colors"
              >
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
