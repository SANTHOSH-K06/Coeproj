import React from 'react';
import { CheckCircle2, Circle, ArrowRight, Play, RefreshCw, X } from 'lucide-react';

export const DemoFlowModal = ({ 
  isOpen, 
  onClose, 
  activeStep, 
  setActiveStep, 
  onExecuteStep, 
  isExecuting, 
  stepResults,
  onResetDemo 
}) => {
  if (!isOpen) return null;

  const demoSteps = [
    { id: 1, tab: 'dashboard', title: '1. Login & Dashboard', desc: 'Authenticate as Chief Admin (admin@hospital.com) and review capacity metrics.' },
    { id: 2, tab: 'appointments', title: '2. Book Patient A', desc: 'Book Dr. Demo at Hospital Alpha on 2026-10-15 at 10:00 AM (Expect: SUCCESS).' },
    { id: 3, tab: 'appointments', title: '3. Attempt Duplicate (Patient B)', desc: 'Attempt booking same slot with Patient B (Expect: REJECTED with "Appointment slot already booked.").' },
    { id: 4, tab: 'appointments', title: '4. Verify Database Integrity', desc: 'Inspect database appointments table to confirm only 1 record exists for the doctor and slot.' },
    { id: 5, tab: 'capacity', title: '5. Tenant Isolation & Rows', desc: 'View tenant-specific metrics for Hospital Alpha, Beta, Gamma with activity levels.' },
    { id: 6, tab: 'capacity', title: '6. Table & Index Storage', desc: 'Inspect physical SQLite table vs index page metrics across appointments, patients, doctors.' },
    { id: 7, tab: 'capacity', title: '7. Retention Policy Test', desc: 'Evaluate 365-day retention rule comparing projected storage Without vs With retention.' },
    { id: 8, tab: 'forecast', title: '8. Baseline vs Proposed Forecast', desc: 'Compare simple linear daily growth vs tenant-aware model with confidence intervals.' },
    { id: 9, tab: 'experiments', title: '9. Run Backtesting Experiments', desc: 'Execute Scenarios A, B, and C to measure actual vs predicted error days.' },
    { id: 10, tab: 'failures', title: '10. Demonstrate Failure Cases', desc: 'Test concurrent booking lock, sudden tenant growth risk spike, and critical storage alerts.' },
    { id: 11, tab: 'audit', title: '11. Security & Cross-Tenant Audit', desc: 'Attempt unauthorized cross-tenant query, verify ACCESS DENIED and audit trail.' }
  ];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(5, 8, 18, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div className="glass-card" style={{
        width: '100%',
        maxWidth: '680px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid rgba(6, 182, 212, 0.4)',
        boxShadow: '0 20px 50px rgba(0,0,0,0.8), 0 0 30px rgba(6, 182, 212, 0.2)'
      }}>
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(6, 182, 212, 0.05)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className="badge badge-cyan">Review 1 Demo Flow</span>
            <h3 style={{ fontSize: '1.15rem' }}>5–10 Minute Reviewer Walkthrough</h3>
          </div>
          <button 
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Steps List */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {demoSteps.map((step) => {
            const isCompleted = stepResults[step.id]?.completed;
            const isCurrent = activeStep === step.id;
            const result = stepResults[step.id];

            return (
              <div 
                key={step.id} 
                style={{
                  padding: '12px 16px',
                  borderRadius: '10px',
                  background: isCurrent ? 'rgba(6, 182, 212, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                  border: isCurrent ? '1px solid #06b6d4' : '1px solid rgba(255, 255, 255, 0.05)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '12px',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ marginTop: '2px' }}>
                    {isCompleted ? (
                      <CheckCircle2 size={18} color="#10b981" />
                    ) : isCurrent ? (
                      <Circle size={18} color="#06b6d4" />
                    ) : (
                      <Circle size={18} color="#64748b" />
                    )}
                  </div>
                  <div>
                    <h4 style={{ fontSize: '0.92rem', color: isCurrent ? '#22d3ee' : '#f1f5f9' }}>{step.title}</h4>
                    <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '2px' }}>{step.desc}</p>
                    {result && (
                      <div style={{ 
                        marginTop: '6px', 
                        fontSize: '0.75rem', 
                        fontFamily: 'JetBrains Mono', 
                        color: result.status === 'ERROR' ? '#fb7185' : '#34d399',
                        background: 'rgba(0,0,0,0.3)',
                        padding: '4px 8px',
                        borderRadius: '4px'
                      }}>
                        {result.message}
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <button
                    className="btn btn-primary"
                    style={{ fontSize: '0.75rem', padding: '6px 12px' }}
                    onClick={() => onExecuteStep(step)}
                    disabled={isExecuting}
                  >
                    <Play size={12} /> Run Step
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(10, 14, 26, 0.8)'
        }}>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.8rem' }}
            onClick={onResetDemo}
          >
            <RefreshCw size={14} /> Reset Demo Dataset
          </button>
          
          <button
            className="btn btn-primary"
            onClick={onClose}
          >
            Close Walkthrough
          </button>
        </div>
      </div>
    </div>
  );
};
