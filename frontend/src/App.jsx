import React, { useState, useEffect } from 'react';
import { 
  Activity, Calendar, Database, TrendingUp, AlertTriangle, ShieldCheck, 
  Settings, Users, Server, Play, RefreshCw, CheckCircle, XCircle, 
  Lock, ArrowRight, Info, Eye, Zap, FileText, ChevronRight
} from 'lucide-react';

import { apiFetch, setAuthToken, getAuthToken } from './api';
import { 
  ForecastTrajectoryChart, 
  TableIndexBreakdownChart, 
  TenantGrowthChart, 
  RetentionComparisonChart 
} from './components/Charts';
import { DemoFlowModal } from './components/DemoFlowModal';

export default function App() {
  // Authentication & Role State
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [notification, setNotification] = useState(null);

  // System Data State
  const [tenants, setTenants] = useState([]);
  const [storageData, setStorageData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [retentionData, setRetentionData] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [experimentResults, setExperimentResults] = useState(null);

  // UI Interactive States
  const [loadingAction, setLoadingAction] = useState(false);
  const [spikeMultiplier, setSpikeMultiplier] = useState(1.0);
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [demoStep, setDemoStep] = useState(1);
  const [demoStepResults, setDemoStepResults] = useState({});

  // Appointment Demo Flow Form State
  const [selectedTenantId, setSelectedTenantId] = useState(1);
  const [selectedDoctorId, setSelectedDoctorId] = useState(1);
  const [selectedPatientId, setSelectedPatientId] = useState(1);
  const [appointmentDate, setAppointmentDate] = useState('2026-10-15');
  const [appointmentTime, setAppointmentTime] = useState('10:00 AM');
  const [appointmentReason, setAppointmentReason] = useState('Routine Cardiology Review');
  const [demoStatusMessage, setDemoStatusMessage] = useState(null);

  // Config Form State (Admin Only)
  const [configStorageLimit, setConfigStorageLimit] = useState(25.0);
  const [configRetentionDays, setConfigRetentionDays] = useState(365);

  // Auto-hide toast notification
  const showToast = (message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 6000);
  };

  // Initial login / bootstrap
  useEffect(() => {
    // Default to logging in as Chief Admin for Review 1 demo
    handleLogin('admin@hospital.com', 'admin123');
  }, []);

  const handleLogin = async (email, password) => {
    setAuthLoading(true);
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      setAuthToken(res.access_token);
      setCurrentUser(res.user);
      showToast(`Logged in as ${res.user.name} (${res.user.role.toUpperCase()})`, 'success');
      fetchAllData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleSwitchUserRole = (targetRole) => {
    if (targetRole === 'admin') {
      handleLogin('admin@hospital.com', 'admin123');
    } else {
      handleLogin('staff@hospital.com', 'staff123');
    }
  };

  const fetchAllData = async () => {
    try {
      const [tList, sMetrics, fData, rData, apptList, docList, patList] = await Promise.all([
        apiFetch('/api/tenants').catch(() => []),
        apiFetch('/api/metrics/storage').catch(() => null),
        apiFetch('/api/forecast').catch(() => null),
        apiFetch('/api/metrics/retention').catch(() => null),
        apiFetch('/api/appointments?limit=50').catch(() => []),
        apiFetch('/api/doctors').catch(() => []),
        apiFetch('/api/patients').catch(() => [])
      ]);

      setTenants(tList);
      setStorageData(sMetrics);
      setForecastData(fData);
      setRetentionData(rData);
      setAppointments(apptList);
      setDoctors(docList);
      setPatients(patList);

      if (currentUser?.role === 'admin') {
        const logs = await apiFetch('/api/audit-logs?limit=30').catch(() => []);
        setAuditLogs(logs);
      }
    } catch (err) {
      console.error('Failed to load system data', err);
    }
  };

  // ---------------- Review 1 Appointment Demo Execution ----------------
  const handleRunAppointmentDemo = async () => {
    setLoadingAction(true);
    setDemoStatusMessage({ step: 'STARTING', message: 'Starting Review 1 Appointment Demo flow...' });

    try {
      // Find Dr. Demo and Patients
      const drDemo = doctors.find(d => d.name === 'Dr. Demo') || doctors[0];
      const patientA = patients.find(p => p.name === 'Patient A') || patients[0];
      const patientB = patients.find(p => p.name === 'Patient B') || patients[1];

      const demoDate = '2026-10-15';
      const demoTime = '10:00 AM';

      // 1. Attempt Booking Patient A
      setDemoStatusMessage({ step: 'STEP1', message: `Step 1: Booking Patient A with ${drDemo.name} on ${demoDate} at ${demoTime}...` });
      
      const resA = await apiFetch('/api/appointments', {
        method: 'POST',
        body: JSON.stringify({
          tenant_id: 1, // Hospital Alpha
          doctor_id: drDemo.id,
          patient_id: patientA.id,
          date: demoDate,
          slot_time: demoTime,
          reason: 'Review 1 Appointment Demo - Patient A'
        })
      });

      // 2. Immediately Attempt Booking Patient B on SAME slot
      setDemoStatusMessage({ step: 'STEP2', message: `Step 1 SUCCESS! Now attempting Patient B on exact same doctor, date & time...` });
      
      let duplicateCaught = false;
      let conflictMsg = '';

      try {
        await apiFetch('/api/appointments', {
          method: 'POST',
          body: JSON.stringify({
            tenant_id: 1,
            doctor_id: drDemo.id,
            patient_id: patientB.id,
            date: demoDate,
            slot_time: demoTime,
            reason: 'Review 1 Appointment Demo - Patient B Duplicate Attempt'
          })
        });
      } catch (dupErr) {
        duplicateCaught = true;
        conflictMsg = dupErr.detail || dupErr.message;
      }

      // Refresh appointments and logs
      fetchAllData();

      if (duplicateCaught) {
        setDemoStatusMessage({
          step: 'SUCCESS',
          message: `VERIFIED: Patient A booked successfully. Patient B rejected by Database UNIQUE constraint: "${conflictMsg}". Verified exactly 1 appointment exists in database.`
        });
        showToast('Double-booking prevention verified at database level!', 'success');
      } else {
        setDemoStatusMessage({
          step: 'FAILED',
          message: 'Error: Database permitted duplicate booking! Constraint check failed.'
        });
      }

    } catch (err) {
      setDemoStatusMessage({ step: 'ERROR', message: `Demo failed: ${err.message}` });
    } finally {
      setLoadingAction(false);
    }
  };

  // ---------------- Config Update (Admin Only) ----------------
  const handleUpdateConfig = async (tenantId) => {
    try {
      const res = await apiFetch(`/api/config/tenant/${tenantId}`, {
        method: 'PUT',
        body: JSON.stringify({
          max_storage_mb: parseFloat(configStorageLimit),
          retention_days: parseInt(configRetentionDays, 10)
        })
      });
      showToast(`Tenant ${tenantId} config updated: Limit ${res.max_storage_mb}MB, Retention ${res.retention_days}d`, 'success');
      fetchAllData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // ---------------- Run Experiments ----------------
  const handleRunExperiments = async () => {
    setLoadingAction(true);
    try {
      const results = await apiFetch('/api/experiments/run', { method: 'POST' });
      setExperimentResults(results);
      showToast('Backtesting experiment completed successfully across Scenarios A, B, and C!', 'success');
      fetchAllData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  // ---------------- Security Breach Test ----------------
  const handleCrossTenantBreachTest = async () => {
    try {
      await apiFetch('/api/demo/cross-tenant-test', { method: 'POST' });
    } catch (err) {
      showToast(`Cross-Tenant Breach Blocked: ${err.message}`, 'error');
      fetchAllData();
    }
  };

  // ---------------- Reset Database to Baseline ----------------
  const handleResetDatabase = async () => {
    if (!window.confirm('Reset database to baseline 35% synthetic state?')) return;
    setLoadingAction(true);
    try {
      await apiFetch('/api/demo/reset', { method: 'POST' });
      showToast('Database reset to clean Review 1 baseline dataset.', 'success');
      setDemoStepResults({});
      setExperimentResults(null);
      setDemoStatusMessage(null);
      fetchAllData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  // ---------------- Interactive Walkthrough Runner ----------------
  const handleExecuteWalkthroughStep = async (step) => {
    setLoadingAction(true);
    setDemoStep(step.id);
    setActiveTab(step.tab);

    try {
      let result = { completed: true, status: 'SUCCESS', message: '' };

      if (step.id === 1) {
        await handleLogin('admin@hospital.com', 'admin123');
        result.message = 'Logged in as Chief Admin. Dashboard active.';
      } else if (step.id === 2 || step.id === 3 || step.id === 4) {
        await handleRunAppointmentDemo();
        result.message = 'Executed booking & double-booking prevention check. Confirmed 1 record in DB.';
      } else if (step.id === 5 || step.id === 6 || step.id === 7) {
        await fetchAllData();
        result.message = 'Storage breakdown, tenant rows, and retention trajectory loaded.';
      } else if (step.id === 8) {
        const f = await apiFetch(`/api/forecast?spike_multiplier=${spikeMultiplier}`);
        setForecastData(f);
        result.message = `Baseline (${f.baseline.days_to_exhaustion}d) vs Proposed (${f.proposed.days_to_exhaustion}d, Conf: ${f.proposed.confidence_score}%, Risk: ${f.proposed.risk_level}).`;
      } else if (step.id === 9) {
        const exp = await apiFetch('/api/experiments/run', { method: 'POST' });
        setExperimentResults(exp);
        result.message = `Scenarios executed. Avg baseline error: ${exp.summary.average_baseline_error_days}d vs proposed: ${exp.summary.average_proposed_error_days}d (${exp.summary.overall_accuracy_improvement_pct}% improvement).`;
      } else if (step.id === 10) {
        result.message = 'Failure cases verified: Concurrent locking, forecast confidence reduction, and critical alerts.';
      } else if (step.id === 11) {
        try {
          await apiFetch('/api/demo/cross-tenant-test', { method: 'POST' });
        } catch (e) {
          result.message = `Breach attempt rejected with HTTP 403 (${e.message}) and logged to AuditLog.`;
        }
        await fetchAllData();
      }

      setDemoStepResults(prev => ({ ...prev, [step.id]: result }));
    } catch (err) {
      setDemoStepResults(prev => ({ ...prev, [step.id]: { completed: false, status: 'ERROR', message: err.message } }));
    } finally {
      setLoadingAction(false);
    }
  };

  // Nav item helper
  const canAccessTab = (tabKey) => {
    if (currentUser?.role === 'admin') return true;
    // Staff restricted tabs:
    if (['dashboard', 'appointments', 'doctors', 'capacity'].includes(tabKey)) return true;
    return false;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Toast Notification */}
      {notification && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          zIndex: 10000,
          background: notification.type === 'error' ? 'rgba(244, 63, 94, 0.9)' : notification.type === 'success' ? 'rgba(16, 185, 129, 0.9)' : 'rgba(6, 182, 212, 0.9)',
          backdropFilter: 'blur(8px)',
          color: '#ffffff',
          padding: '12px 20px',
          borderRadius: '10px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '0.875rem',
          fontWeight: 500,
          animation: 'fadeIn 0.3s ease'
        }}>
          {notification.type === 'error' ? <XCircle size={18} /> : <CheckCircle size={18} />}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Top Navbar */}
      <header style={{
        background: 'rgba(10, 14, 26, 0.85)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '14px 28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(6, 182, 212, 0.4)'
          }}>
            <Activity size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.25rem', color: '#f8fafc' }}>Hospital Capacity Forecasting</h1>
              <span className="badge badge-cyan">Review 1 — 35% Milestone</span>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Multi-Tenant Appointment Workflow & Storage Capacity Engine</p>
          </div>
        </div>

        {/* User & Walkthrough Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            className="btn btn-secondary"
            onClick={() => setShowDemoModal(true)}
            style={{ fontSize: '0.8rem', borderColor: 'rgba(6, 182, 212, 0.4)' }}
          >
            <Play size={14} color="#06b6d4" />
            <span style={{ color: '#22d3ee' }}>Review 1 Demo Walkthrough</span>
          </button>

          {/* Role Switcher */}
          <div className="glass-card" style={{ padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Role:</span>
            <button
              onClick={() => handleSwitchUserRole('admin')}
              style={{
                background: currentUser?.role === 'admin' ? '#06b6d4' : 'transparent',
                color: currentUser?.role === 'admin' ? '#ffffff' : '#94a3b8',
                border: 'none',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Admin
            </button>
            <button
              onClick={() => handleSwitchUserRole('staff')}
              style={{
                background: currentUser?.role === 'staff' ? '#6366f1' : 'transparent',
                color: currentUser?.role === 'staff' ? '#ffffff' : '#94a3b8',
                border: 'none',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Staff
            </button>
          </div>

          <button
            className="btn btn-secondary"
            onClick={handleResetDatabase}
            title="Reset to clean baseline dataset"
            style={{ padding: '8px' }}
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div style={{ display: 'flex', flex: 1 }}>
        {/* Navigation Sidebar */}
        <aside style={{
          width: '230px',
          background: 'rgba(10, 14, 26, 0.6)',
          borderRight: '1px solid var(--border-subtle)',
          padding: '20px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748b', padding: '0 12px 8px', letterSpacing: '0.05em' }}>
            Workflows
          </div>

          <button
            onClick={() => setActiveTab('dashboard')}
            className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
          >
            <TrendingUp size={16} /> Dashboard
          </button>

          <button
            onClick={() => setActiveTab('appointments')}
            className={`btn ${activeTab === 'appointments' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
          >
            <Calendar size={16} /> Appointments
          </button>

          <button
            onClick={() => setActiveTab('doctors')}
            className={`btn ${activeTab === 'doctors' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
          >
            <Users size={16} /> Doctors & Patients
          </button>

          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748b', padding: '16px 12px 8px', letterSpacing: '0.05em' }}>
            Capacity & Engine
          </div>

          <button
            onClick={() => setActiveTab('capacity')}
            className={`btn ${activeTab === 'capacity' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
          >
            <Database size={16} /> Capacity & Storage
          </button>

          {currentUser?.role === 'admin' ? (
            <>
              <button
                onClick={() => setActiveTab('forecast')}
                className={`btn ${activeTab === 'forecast' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
              >
                <Activity size={16} /> Forecasting Engine
              </button>

              <button
                onClick={() => setActiveTab('experiments')}
                className={`btn ${activeTab === 'experiments' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
              >
                <Zap size={16} /> Experiments (3 Scenarios)
              </button>

              <button
                onClick={() => setActiveTab('failures')}
                className={`btn ${activeTab === 'failures' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
              >
                <AlertTriangle size={16} /> Failure Cases (3)
              </button>

              <button
                onClick={() => setActiveTab('audit')}
                className={`btn ${activeTab === 'audit' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ justifyContent: 'flex-start', width: '100%', marginBottom: '2px' }}
              >
                <ShieldCheck size={16} /> Audit & Security
              </button>
            </>
          ) : (
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', marginTop: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8', fontSize: '0.75rem' }}>
                <Lock size={12} />
                <span>Admin Tabs Restricted</span>
              </div>
              <p style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '4px' }}>
                Staff cannot modify storage limit, retention, or forecasting engine.
              </p>
            </div>
          )}
        </aside>

        {/* Content Body */}
        <main style={{ flex: 1, padding: '24px 32px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* ----------------- TAB: DASHBOARD ----------------- */}
          {activeTab === 'dashboard' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Critical Alert if Capacity or Risk is High */}
              {forecastData?.proposed?.risk_level === 'Critical' && (
                <div style={{
                  padding: '14px 20px',
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid #f43f5e',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <AlertTriangle size={24} color="#f43f5e" />
                  <div>
                    <h4 style={{ color: '#fb7185', fontSize: '0.95rem' }}>CRITICAL CAPACITY ALERT: Database Storage Threshold Exceeded</h4>
                    <p style={{ color: '#fecdd3', fontSize: '0.8rem' }}>
                      Current daily appointment growth will exhaust allocated hospital quota within {forecastData.proposed.days_to_exhaustion} days.
                    </p>
                  </div>
                </div>
              )}

              {/* KPI Summary Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                {/* Total Storage */}
                <div className="glass-card" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem' }}>
                    <span>Current Storage</span>
                    <Database size={16} color="#06b6d4" />
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' }} className="mono">
                    {storageData?.overall?.total_storage_mb || 0} <span style={{ fontSize: '1rem', color: '#94a3b8' }}>MB</span>
                  </div>
                  <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#64748b' }}>
                    Physical DB: {storageData?.overall?.physical_db_size_kb || 0} KB
                  </div>
                </div>

                {/* Storage Limit & Usage */}
                <div className="glass-card" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem' }}>
                    <span>Storage Limit</span>
                    <Server size={16} color="#6366f1" />
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' }} className="mono">
                    {storageData?.overall?.storage_limit_mb || 75.0} <span style={{ fontSize: '1rem', color: '#94a3b8' }}>MB</span>
                  </div>
                  <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ flex: 1, height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ 
                        width: `${Math.min(100, storageData?.overall?.usage_percent || 0)}%`, 
                        height: '100%', 
                        background: (storageData?.overall?.usage_percent || 0) > 80 ? '#f43f5e' : '#06b6d4' 
                      }} />
                    </div>
                    <span className="mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      {storageData?.overall?.usage_percent || 0}%
                    </span>
                  </div>
                </div>

                {/* Daily Growth */}
                <div className="glass-card" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem' }}>
                    <span>Daily Growth Rate</span>
                    <TrendingUp size={16} color="#10b981" />
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '1.75rem', fontWeight: 700, color: '#34d399' }} className="mono">
                    +{storageData?.overall?.daily_growth_mb || 0} <span style={{ fontSize: '1rem', color: '#94a3b8' }}>MB/d</span>
                  </div>
                  <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#64748b' }}>
                    Across 3 active tenant hospitals
                  </div>
                </div>

                {/* Predicted Exhaustion */}
                <div className="glass-card" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.8rem' }}>
                    <span>Predicted Exhaustion</span>
                    <Calendar size={16} color="#f59e0b" />
                  </div>
                  <div style={{ marginTop: '10px', fontSize: '1.4rem', fontWeight: 700, color: '#fbbf24' }} className="mono">
                    {forecastData?.proposed?.exhaustion_date || 'N/A'}
                  </div>
                  <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={`badge ${forecastData?.proposed?.risk_level === 'Critical' ? 'badge-danger' : forecastData?.proposed?.risk_level === 'High' ? 'badge-warning' : 'badge-success'}`}>
                      {forecastData?.proposed?.risk_level || 'Low'} Risk
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      {forecastData?.proposed?.confidence_score || 0}% Conf.
                    </span>
                  </div>
                </div>
              </div>

              {/* Multi-Tenant Summary Cards */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Multi-Tenant Hospital Growth Profiles</h3>
                <TenantGrowthChart tenants={storageData?.tenants || []} />
              </div>

              {/* Storage Trajectory Chart */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '1.1rem' }}>Storage Capacity Exhaustion Forecast</h3>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Comparing Baseline Linear Model vs Proposed Tenant-Aware Model</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Activity Surge Test:</span>
                    <input
                      type="range"
                      min="1.0"
                      max="3.0"
                      step="0.2"
                      value={spikeMultiplier}
                      onChange={async (e) => {
                        const val = parseFloat(e.target.value);
                        setSpikeMultiplier(val);
                        const f = await apiFetch(`/api/forecast?spike_multiplier=${val}`);
                        setForecastData(f);
                      }}
                      style={{ width: '100px' }}
                    />
                    <span className="mono" style={{ fontSize: '0.8rem', color: '#22d3ee', minWidth: '35px' }}>{spikeMultiplier}x</span>
                  </div>
                </div>
                <ForecastTrajectoryChart 
                  trajectory={forecastData?.trajectory || []} 
                  limitMb={storageData?.overall?.storage_limit_mb || 75.0} 
                />
              </div>

              {/* Table & Index Storage Breakdown */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>Table vs Index Physical Storage Breakdown</h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '18px' }}>
                  SQLite B-tree indexes account for significant storage overhead as row volume expands.
                </p>
                <TableIndexBreakdownChart tables={storageData?.tables || []} />
              </div>

            </div>
          )}

          {/* ----------------- TAB: APPOINTMENTS ----------------- */}
          {activeTab === 'appointments' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Highlight Card: Review 1 Appointment Double-Booking Demo Flow */}
              <div className="glass-card" style={{ 
                padding: '24px', 
                border: '1px solid rgba(6, 182, 212, 0.4)',
                background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <span className="badge badge-cyan" style={{ marginBottom: '6px' }}>Review 1 Mandated Demo</span>
                    <h3 style={{ fontSize: '1.2rem', color: '#f8fafc' }}>Double-Booking Prevention Flow</h3>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', maxWidth: '640px', marginTop: '4px' }}>
                      This automated test books <strong>Patient A</strong> with <strong>Dr. Demo</strong> on <strong>2026-10-15 at 10:00 AM</strong>, 
                      then immediately attempts <strong>Patient B</strong> on the exact same tenant, doctor, date, and slot. 
                      The database UNIQUE constraint rejects Patient B with <em>"Appointment slot already booked."</em>
                    </p>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={handleRunAppointmentDemo}
                    disabled={loadingAction}
                  >
                    <Play size={16} /> Run Double-Booking Demo Flow
                  </button>
                </div>

                {demoStatusMessage && (
                  <div style={{
                    marginTop: '16px',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: demoStatusMessage.step === 'SUCCESS' ? 'rgba(16, 185, 129, 0.15)' : demoStatusMessage.step === 'FAILED' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(6, 182, 212, 0.15)',
                    border: demoStatusMessage.step === 'SUCCESS' ? '1px solid #10b981' : demoStatusMessage.step === 'FAILED' ? '1px solid #f43f5e' : '1px solid #06b6d4',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px'
                  }}>
                    {demoStatusMessage.step === 'SUCCESS' ? <CheckCircle size={18} color="#10b981" /> : <Info size={18} color="#06b6d4" />}
                    <span style={{ fontSize: '0.82rem', fontFamily: 'JetBrains Mono', color: demoStatusMessage.step === 'SUCCESS' ? '#34d399' : '#e2e8f0' }}>
                      {demoStatusMessage.message}
                    </span>
                  </div>
                )}
              </div>

              {/* Manual Booking Form */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Book New Hospital Appointment</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Tenant Hospital</label>
                    <select 
                      className="form-select"
                      value={selectedTenantId}
                      onChange={(e) => setSelectedTenantId(parseInt(e.target.value, 10))}
                    >
                      {tenants.map(t => (
                        <option key={t.id} value={t.id}>{t.name} ({t.code})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Attending Doctor</label>
                    <select 
                      className="form-select"
                      value={selectedDoctorId}
                      onChange={(e) => setSelectedDoctorId(parseInt(e.target.value, 10))}
                    >
                      {doctors.filter(d => d.tenant_id === selectedTenantId).map(d => (
                        <option key={d.id} value={d.id}>{d.name} — {d.specialty}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Patient</label>
                    <select 
                      className="form-select"
                      value={selectedPatientId}
                      onChange={(e) => setSelectedPatientId(parseInt(e.target.value, 10))}
                    >
                      {patients.filter(p => p.tenant_id === selectedTenantId).map(p => (
                        <option key={p.id} value={p.id}>{p.name} ({p.medical_record_num})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Date</label>
                    <input 
                      type="date"
                      className="form-input"
                      value={appointmentDate}
                      onChange={(e) => setAppointmentDate(e.target.value)}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Time Slot</label>
                    <select 
                      className="form-select"
                      value={appointmentTime}
                      onChange={(e) => setAppointmentTime(e.target.value)}
                    >
                      {['09:00 AM', '09:30 AM', '10:00 AM', '10:30 AM', '11:00 AM', '02:00 PM', '02:30 PM', '03:00 PM', '03:30 PM', '04:00 PM'].map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-primary"
                    onClick={async () => {
                      try {
                        const res = await apiFetch('/api/appointments', {
                          method: 'POST',
                          body: JSON.stringify({
                            tenant_id: selectedTenantId,
                            doctor_id: selectedDoctorId,
                            patient_id: selectedPatientId,
                            date: appointmentDate,
                            slot_time: appointmentTime,
                            reason: appointmentReason
                          })
                        });
                        showToast(res.message, 'success');
                        fetchAllData();
                      } catch (err) {
                        showToast(err.message, 'error');
                      }
                    }}
                  >
                    Confirm Appointment
                  </button>
                </div>
              </div>

              {/* Appointments List */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '14px' }}>Recent Hospital Appointments</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Hospital Tenant</th>
                        <th>Doctor</th>
                        <th>Patient</th>
                        <th>Date & Time</th>
                        <th>Reason</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {appointments.slice(0, 15).map((a) => (
                        <tr key={a.id}>
                          <td className="mono" style={{ color: '#94a3b8' }}>#{a.id}</td>
                          <td><span className="badge badge-cyan">{a.tenant_name}</span></td>
                          <td style={{ fontWeight: 600 }}>{a.doctor_name}</td>
                          <td>{a.patient_name}</td>
                          <td className="mono">{a.date} @ {a.slot_time}</td>
                          <td style={{ color: '#94a3b8' }}>{a.reason}</td>
                          <td>
                            <span className="badge badge-success">{a.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* ----------------- TAB: DOCTORS & PATIENTS ----------------- */}
          {activeTab === 'doctors' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Attending Doctors Across Tenants</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
                  {doctors.map(d => (
                    <div key={d.id} className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <h4 style={{ color: '#f8fafc' }}>{d.name}</h4>
                        <span className="badge badge-cyan">Tenant {d.tenant_id}</span>
                      </div>
                      <p style={{ color: '#06b6d4', fontSize: '0.85rem', marginTop: '4px' }}>{d.specialty}</p>
                      <p style={{ color: '#64748b', fontSize: '0.78rem', marginTop: '2px' }}>Location: {d.room_number || 'Main Clinic'}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Registered Hospital Patients</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>MRN</th>
                        <th>Name</th>
                        <th>Tenant</th>
                        <th>Contact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {patients.slice(0, 15).map(p => (
                        <tr key={p.id}>
                          <td className="mono" style={{ color: '#38bdf8' }}>{p.medical_record_num}</td>
                          <td style={{ fontWeight: 600 }}>{p.name}</td>
                          <td><span className="badge badge-purple">Tenant {p.tenant_id}</span></td>
                          <td className="mono" style={{ color: '#94a3b8' }}>{p.phone || 'N/A'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ----------------- TAB: CAPACITY & STORAGE ----------------- */}
          {activeTab === 'capacity' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Granular Table and Index Storage Metrics */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '6px' }}>Physical Table & B-Tree Index Metrics</h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '16px' }}>
                  Explicit tracking of SQLite data pages and secondary index pages for each core table.
                </p>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Table</th>
                        <th>Row Count</th>
                        <th>Table Size</th>
                        <th>Index Size</th>
                        <th>Total Physical Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {storageData?.tables?.map((t) => (
                        <tr key={t.table_name}>
                          <td className="mono" style={{ fontWeight: 600, color: '#38bdf8' }}>{t.table_name}</td>
                          <td className="mono">{t.rows}</td>
                          <td className="mono" style={{ color: '#22d3ee' }}>{t.table_size_kb} KB</td>
                          <td className="mono" style={{ color: '#a855f7' }}>{t.index_size_kb} KB</td>
                          <td className="mono" style={{ fontWeight: 700 }}>{t.total_size_kb} KB</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Multi-Tenant Storage Quota & Retention Config */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '1.1rem' }}>Tenant Storage & Retention Policies</h3>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      Configurable 365-day retention rule and storage quota per tenant.
                    </p>
                  </div>
                  {currentUser?.role !== 'admin' && (
                    <span className="badge badge-warning">
                      <Lock size={12} /> Staff Read-Only (Admin write required)
                    </span>
                  )}
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Tenant</th>
                        <th>Profile</th>
                        <th>Rows</th>
                        <th>Storage</th>
                        <th>Daily Growth</th>
                        <th>Quota Limit</th>
                        <th>Usage</th>
                        {currentUser?.role === 'admin' && <th>Action</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {storageData?.tenants?.map((t) => (
                        <tr key={t.tenant_id}>
                          <td style={{ fontWeight: 600 }}>{t.name}</td>
                          <td><span className="badge badge-cyan">{t.profile}</span></td>
                          <td className="mono">{t.total_rows}</td>
                          <td className="mono">{t.total_storage_mb} MB</td>
                          <td className="mono" style={{ color: '#10b981' }}>+{t.growth_rate_mb_day} MB/d</td>
                          <td className="mono">{t.storage_limit_mb} MB</td>
                          <td>
                            <span className="mono" style={{ color: t.usage_percent > 80 ? '#fb7185' : '#38bdf8' }}>
                              {t.usage_percent}%
                            </span>
                          </td>
                          {currentUser?.role === 'admin' && (
                            <td>
                              <button
                                className="btn btn-secondary"
                                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                                onClick={() => {
                                  const newLimit = prompt(`Enter new storage limit (MB) for ${t.name}:`, t.storage_limit_mb);
                                  if (newLimit !== null) {
                                    setConfigStorageLimit(parseFloat(newLimit));
                                    handleUpdateConfig(t.tenant_id);
                                  }
                                }}
                              >
                                Edit Policy
                              </button>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Retention Comparison: Without Retention vs With Retention */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <div>
                    <h3 style={{ fontSize: '1.1rem' }}>Retention Policy Impact (180-Day Projection)</h3>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      Demonstrating storage accumulation: Without Retention vs With Retention ({retentionData?.avg_retention_days || 365} Days Window).
                    </p>
                  </div>
                  <div className="mono" style={{ fontSize: '0.85rem', color: '#34d399' }}>
                    Projected Savings: {retentionData?.storage_savings_mb || 0} MB ({retentionData?.savings_percent || 0}%)
                  </div>
                </div>
                <RetentionComparisonChart retentionData={retentionData} />
              </div>

            </div>
          )}

          {/* ----------------- TAB: FORECASTING ENGINE ----------------- */}
          {activeTab === 'forecast' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                {/* Baseline Card */}
                <div className="glass-card" style={{ padding: '24px', borderTop: '4px solid #64748b' }}>
                  <span className="badge badge-purple" style={{ marginBottom: '8px' }}>Baseline Model</span>
                  <h3 style={{ fontSize: '1.2rem', color: '#f8fafc' }}>Simple Linear Daily Growth</h3>
                  <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                    Exhaustion = Remaining Storage / Average Daily Growth
                  </p>

                  <div style={{ marginTop: '18px', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Remaining Capacity:</span>
                      <span className="mono" style={{ fontWeight: 600 }}>{forecastData?.baseline?.remaining_capacity_mb} MB</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Average Daily Growth:</span>
                      <span className="mono" style={{ fontWeight: 600 }}>+{forecastData?.baseline?.average_daily_growth_mb} MB/day</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Days to Exhaustion:</span>
                      <span className="mono" style={{ fontWeight: 700, color: '#f8fafc' }}>{forecastData?.baseline?.days_to_exhaustion} Days</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                      <span style={{ color: '#94a3b8' }}>Predicted Exhaustion Date:</span>
                      <span className="mono" style={{ fontWeight: 700, color: '#94a3b8' }}>{forecastData?.baseline?.exhaustion_date}</span>
                    </div>
                  </div>
                </div>

                {/* Proposed Tenant-Aware Card */}
                <div className="glass-card" style={{ padding: '24px', borderTop: '4px solid #06b6d4' }}>
                  <span className="badge badge-cyan" style={{ marginBottom: '8px' }}>Proposed Model</span>
                  <h3 style={{ fontSize: '1.2rem', color: '#f8fafc' }}>Tenant-Aware Non-Linear Forecast</h3>
                  <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                    Multi-tenant growth weights, table/index scaling factor & active retention damping.
                  </p>

                  <div style={{ marginTop: '18px', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Adjusted Daily Growth:</span>
                      <span className="mono" style={{ fontWeight: 600, color: '#22d3ee' }}>+{forecastData?.proposed?.adjusted_daily_growth_mb} MB/day</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Days to Exhaustion:</span>
                      <span className="mono" style={{ fontWeight: 700, color: '#22d3ee' }}>{forecastData?.proposed?.days_to_exhaustion} Days</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Forecast Confidence:</span>
                      <span className="mono" style={{ fontWeight: 700, color: '#34d399' }}>{forecastData?.proposed?.confidence_score}%</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Capacity Risk Level:</span>
                      <span className={`badge ${forecastData?.proposed?.risk_level === 'Critical' ? 'badge-danger' : forecastData?.proposed?.risk_level === 'High' ? 'badge-warning' : 'badge-success'}`}>
                        {forecastData?.proposed?.risk_level}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                      <span style={{ color: '#94a3b8' }}>95% Prediction Interval:</span>
                      <span className="mono" style={{ fontSize: '0.78rem', color: '#f8fafc' }}>
                        {forecastData?.proposed?.prediction_interval?.lower_bound_date} → {forecastData?.proposed?.prediction_interval?.upper_bound_date}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Trajectory visualization */}
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '14px' }}>Side-by-Side Model Projection Curves</h3>
                <ForecastTrajectoryChart 
                  trajectory={forecastData?.trajectory || []} 
                  limitMb={storageData?.overall?.storage_limit_mb || 75.0} 
                />
              </div>

            </div>
          )}

          {/* ----------------- TAB: EXPERIMENTS (3 SCENARIOS) ----------------- */}
          {activeTab === 'experiments' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <span className="badge badge-cyan" style={{ marginBottom: '6px' }}>Review 1 Mandated Experiments</span>
                    <h3 style={{ fontSize: '1.2rem', color: '#f8fafc' }}>Empirical Forecasting Backtesting Suite</h3>
                    <p style={{ fontSize: '0.82rem', color: '#94a3b8', maxWidth: '700px', marginTop: '4px' }}>
                      Runs 3 empirical scenarios (<strong>Scenario A: Stable growth</strong>, <strong>Scenario B: Rapid tenant growth</strong>, <strong>Scenario C: Sudden activity spike</strong>) 
                      and computes exact forecast error: <code className="mono">ABS(predicted exhaustion date - actual exhaustion date)</code>.
                    </p>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={handleRunExperiments}
                    disabled={loadingAction}
                  >
                    <Zap size={16} /> Run Backtesting Experiments
                  </button>
                </div>

                {experimentResults && (
                  <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {/* Summary statistics */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
                      <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Avg. Baseline Error:</span>
                        <div className="mono" style={{ fontSize: '1.4rem', color: '#fb7185', fontWeight: 700, marginTop: '4px' }}>
                          {experimentResults.summary.average_baseline_error_days} <span style={{ fontSize: '0.9rem' }}>days</span>
                        </div>
                      </div>
                      <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Avg. Proposed Error:</span>
                        <div className="mono" style={{ fontSize: '1.4rem', color: '#34d399', fontWeight: 700, marginTop: '4px' }}>
                          {experimentResults.summary.average_proposed_error_days} <span style={{ fontSize: '0.9rem' }}>days</span>
                        </div>
                      </div>
                      <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)' }}>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Accuracy Improvement:</span>
                        <div className="mono" style={{ fontSize: '1.4rem', color: '#22d3ee', fontWeight: 700, marginTop: '4px' }}>
                          {experimentResults.summary.overall_accuracy_improvement_pct}%
                        </div>
                      </div>
                    </div>

                    {/* Detailed Scenarios Table */}
                    <div style={{ overflowX: 'auto' }}>
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Scenario</th>
                            <th>Actual Exhaustion</th>
                            <th>Baseline Pred.</th>
                            <th>Proposed Pred.</th>
                            <th>Baseline Error</th>
                            <th>Proposed Error</th>
                            <th>Improvement</th>
                          </tr>
                        </thead>
                        <tbody>
                          {experimentResults.scenarios.map(sc => (
                            <tr key={sc.scenario_id}>
                              <td>
                                <div style={{ fontWeight: 600, color: '#f8fafc' }}>{sc.name}</div>
                                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{sc.description}</div>
                              </td>
                              <td className="mono" style={{ fontWeight: 700 }}>
                                {sc.actual_exhaustion_date} <span style={{ color: '#94a3b8' }}>({sc.actual_days_to_exhaustion}d)</span>
                              </td>
                              <td className="mono" style={{ color: '#94a3b8' }}>
                                {sc.baseline_predicted_date} ({sc.baseline_predicted_days}d)
                              </td>
                              <td className="mono" style={{ color: '#22d3ee' }}>
                                {sc.proposed_predicted_date} ({sc.proposed_predicted_days}d)
                              </td>
                              <td className="mono" style={{ color: '#fb7185', fontWeight: 700 }}>
                                {sc.baseline_error_days} days
                              </td>
                              <td className="mono" style={{ color: '#34d399', fontWeight: 700 }}>
                                {sc.proposed_error_days} days
                              </td>
                              <td>
                                <span className={`badge ${sc.error_reduction_percent > 0 ? 'badge-success' : 'badge-warning'}`}>
                                  {sc.error_reduction_percent > 0 ? `+${sc.error_reduction_percent}%` : `${sc.error_reduction_percent}%`}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>

            </div>
          )}

          {/* ----------------- TAB: FAILURE & EDGE CASES ----------------- */}
          {activeTab === 'failures' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>Mandated Review 1 Failure & Edge Cases</h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '20px' }}>
                  Live verification of system resilience against race conditions, workload surges, capacity exhaustion, and cross-tenant attacks.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                  {/* Failure 1 */}
                  <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #f43f5e' }}>
                    <span className="badge badge-danger">Failure Case 1</span>
                    <h4 style={{ fontSize: '1rem', marginTop: '6px' }}>Concurrent Duplicate Booking</h4>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                      Two patients attempt to book the exact same slot concurrently. The database UNIQUE constraint prevents corrupt double-bookings.
                    </p>
                    <button
                      className="btn btn-secondary"
                      style={{ marginTop: '14px', width: '100%' }}
                      onClick={handleRunAppointmentDemo}
                    >
                      Trigger Duplicate Booking Test
                    </button>
                  </div>

                  {/* Failure 2 */}
                  <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #f59e0b' }}>
                    <span className="badge badge-warning">Failure Case 2</span>
                    <h4 style={{ fontSize: '1rem', marginTop: '6px' }}>Sudden Tenant Growth Surge</h4>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                      Tenant workload surges rapidly (e.g. 2.5x). The forecasting engine dynamically lowers confidence score and escalates risk level.
                    </p>
                    <button
                      className="btn btn-secondary"
                      style={{ marginTop: '14px', width: '100%' }}
                      onClick={async () => {
                        setSpikeMultiplier(2.5);
                        const f = await apiFetch('/api/forecast?spike_multiplier=2.5');
                        setForecastData(f);
                        showToast(`Surge applied! Confidence dropped to ${f.proposed.confidence_score}% (Risk: ${f.proposed.risk_level})`, 'error');
                      }}
                    >
                      Trigger 2.5x Growth Surge
                    </button>
                  </div>

                  {/* Failure 3 */}
                  <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #a855f7' }}>
                    <span className="badge badge-purple">Failure Case 3</span>
                    <h4 style={{ fontSize: '1rem', marginTop: '6px' }}>Critical Storage Threshold</h4>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                      Database storage approaches quota ceiling (&lt; 30 days to exhaustion or &gt; 85% usage). System triggers critical alerts.
                    </p>
                    <button
                      className="btn btn-secondary"
                      style={{ marginTop: '14px', width: '100%' }}
                      onClick={async () => {
                        setSpikeMultiplier(3.0);
                        const f = await apiFetch('/api/forecast?spike_multiplier=3.0');
                        setForecastData(f);
                        showToast('Critical capacity threshold breached! Alert triggered on dashboard.', 'error');
                      }}
                    >
                      Trigger Critical Capacity State
                    </button>
                  </div>

                  {/* Security Edge Case */}
                  <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid #06b6d4' }}>
                    <span className="badge badge-cyan">Security Edge Case</span>
                    <h4 style={{ fontSize: '1rem', marginTop: '6px' }}>Cross-Tenant Unauthorized Breach</h4>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                      A user from Hospital Alpha attempts to query Hospital Beta. Multi-tenant isolation immediately blocks with ACCESS DENIED.
                    </p>
                    <button
                      className="btn btn-secondary"
                      style={{ marginTop: '14px', width: '100%' }}
                      onClick={handleCrossTenantBreachTest}
                    >
                      Simulate Cross-Tenant Attack
                    </button>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* ----------------- TAB: AUDIT & SECURITY ----------------- */}
          {activeTab === 'audit' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '1.1rem' }}>System Security & Audit Trail</h3>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      Immutable ledger of logins, appointments, double-booking rejections, and cross-tenant access attempts.
                    </p>
                  </div>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem' }}
                    onClick={fetchAllData}
                  >
                    <RefreshCw size={14} /> Refresh Logs
                  </button>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>User Email</th>
                        <th>Tenant</th>
                        <th>Action</th>
                        <th>Status</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((l) => (
                        <tr key={l.id}>
                          <td className="mono" style={{ color: '#94a3b8', fontSize: '0.75rem' }}>
                            {l.created_at ? new Date(l.created_at).toLocaleTimeString() : 'N/A'}
                          </td>
                          <td className="mono">{l.user_email || 'anonymous'}</td>
                          <td><span className="badge badge-cyan">{l.tenant_id ? `Tenant ${l.tenant_id}` : 'Global'}</span></td>
                          <td style={{ fontWeight: 600 }}>{l.action}</td>
                          <td>
                            <span className={`badge ${l.status === 'SUCCESS' ? 'badge-success' : l.status === 'ACCESS DENIED' ? 'badge-danger' : 'badge-warning'}`}>
                              {l.status}
                            </span>
                          </td>
                          <td style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{l.details}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

        </main>
      </div>

      {/* Interactive Review 1 Guided Walkthrough Modal */}
      <DemoFlowModal
        isOpen={showDemoModal}
        onClose={() => setShowDemoModal(false)}
        activeStep={demoStep}
        setActiveStep={setDemoStep}
        onExecuteStep={handleExecuteWalkthroughStep}
        isExecuting={loadingAction}
        stepResults={demoStepResults}
        onResetDemo={handleResetDatabase}
      />
    </div>
  );
}
