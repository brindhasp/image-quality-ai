import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Analyze from './pages/Analyze';
import History from './pages/History';
import AnalysisDetail from './pages/AnalysisDetail';

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">Image Quality AI</div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}>
            <span className="sidebar-icon">&#9632;</span> Dashboard
          </NavLink>
          <NavLink to="/analyze" className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}>
            <span className="sidebar-icon">&#9654;</span> Analyze
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => isActive ? 'sidebar-link active' : 'sidebar-link'}>
            <span className="sidebar-icon">&#9776;</span> History
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/analyze" element={<Analyze />} />
          <Route path="/history" element={<History />} />
          <Route path="/analysis/:id" element={<AnalysisDetail />} />
        </Routes>
      </main>
    </div>
  );
}
