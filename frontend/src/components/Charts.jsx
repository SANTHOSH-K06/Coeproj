import React from 'react';

// 1. Forecast Trajectory Chart: Baseline Linear vs Proposed Tenant-Aware
export const ForecastTrajectoryChart = ({ trajectory = [], limitMb = 75.0 }) => {
  if (!trajectory || trajectory.length === 0) return null;

  const width = 680;
  const height = 280;
  const padding = { top: 20, right: 30, bottom: 40, left: 50 };

  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const maxVal = Math.max(limitMb * 1.15, ...trajectory.map(d => Math.max(d.baseline_mb, d.proposed_mb)));
  const minVal = 0;

  const xScale = (index) => padding.left + (index / (trajectory.length - 1)) * innerWidth;
  const yScale = (val) => padding.top + innerHeight - ((val - minVal) / (maxVal - minVal)) * innerHeight;

  // Paths
  const baselinePoints = trajectory.map((d, i) => `${xScale(i)},${yScale(d.baseline_mb)}`).join(" ");
  const proposedPoints = trajectory.map((d, i) => `${xScale(i)},${yScale(d.proposed_mb)}`).join(" ");
  const limitY = yScale(limitMb);

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto' }}>
        <defs>
          <linearGradient id="baselineGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#94a3b8" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#64748b" stopOpacity="0.8" />
          </linearGradient>
          <linearGradient id="proposedGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="1" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="1" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
          const y = padding.top + innerHeight * (1 - ratio);
          const val = Math.round(minVal + (maxVal - minVal) * ratio);
          return (
            <g key={idx}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <text x={padding.left - 10} y={y + 4} fill="#64748b" fontSize="11" textAnchor="end" fontFamily="JetBrains Mono">
                {val}M
              </text>
            </g>
          );
        })}

        {/* Limit Line */}
        <line
          x1={padding.left}
          y1={limitY}
          x2={width - padding.right}
          y2={limitY}
          stroke="#f43f5e"
          strokeWidth="2"
          strokeDasharray="5 5"
        />
        <text x={width - padding.right - 8} y={limitY - 6} fill="#f43f5e" fontSize="11" textAnchor="end" fontWeight="bold">
          Storage Limit ({limitMb} MB)
        </text>

        {/* Baseline Line */}
        <polyline
          fill="none"
          stroke="url(#baselineGrad)"
          strokeWidth="2.5"
          strokeDasharray="4 4"
          points={baselinePoints}
        />

        {/* Proposed Line */}
        <polyline
          fill="none"
          stroke="url(#proposedGrad)"
          strokeWidth="3.5"
          points={proposedPoints}
        />

        {/* X Axis labels */}
        {trajectory.filter((_, i) => i % 5 === 0 || i === trajectory.length - 1).map((d, idx) => {
          const originalIdx = trajectory.findIndex(item => item.day === d.day);
          const x = xScale(originalIdx);
          return (
            <g key={idx}>
              <line x1={x} y1={height - padding.bottom} x2={x} y2={height - padding.bottom + 5} stroke="#64748b" />
              <text x={x} y={height - padding.bottom + 20} fill="#94a3b8" fontSize="10" textAnchor="middle">
                +{d.day}d
              </text>
            </g>
          );
        })}
      </svg>
      
      {/* Legend */}
      <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginTop: '8px', fontSize: '0.8rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '16px', height: '3px', background: '#64748b', display: 'inline-block' }}></span>
          <span style={{ color: '#94a3b8' }}>Baseline Linear</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '16px', height: '3px', background: 'linear-gradient(to right, #06b6d4, #6366f1)', display: 'inline-block' }}></span>
          <span style={{ color: '#22d3ee', fontWeight: 600 }}>Proposed Tenant-Aware</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '16px', height: '2px', borderTop: '2px dashed #f43f5e', display: 'inline-block' }}></span>
          <span style={{ color: '#fb7185' }}>Storage Limit</span>
        </div>
      </div>
    </div>
  );
};

// 2. Table vs Index Breakdown Chart
export const TableIndexBreakdownChart = ({ tables = [] }) => {
  if (!tables || tables.length === 0) return null;

  const maxTotalKb = Math.max(...tables.map(t => t.total_size_kb), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', width: '100%' }}>
      {tables.map(table => {
        const dataWidthPct = (table.table_size_kb / maxTotalKb) * 100;
        const indexWidthPct = (table.index_size_kb / maxTotalKb) * 100;

        return (
          <div key={table.table_name} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
              <span className="mono" style={{ color: '#e2e8f0', fontWeight: 600 }}>{table.table_name}</span>
              <span style={{ color: '#94a3b8' }}>
                <span style={{ color: '#22d3ee' }}>Data: {table.table_size_kb} KB</span> | <span style={{ color: '#a855f7' }}>Index: {table.index_size_kb} KB</span> ({table.rows} rows)
              </span>
            </div>
            <div style={{ display: 'flex', height: '14px', background: 'rgba(255,255,255,0.04)', borderRadius: '6px', overflow: 'hidden' }}>
              <div style={{ width: `${dataWidthPct}%`, background: 'linear-gradient(90deg, #0891b2, #06b6d4)' }} title="Data Table Size" />
              <div style={{ width: `${indexWidthPct}%`, background: 'linear-gradient(90deg, #7c3aed, #a855f7)' }} title="Index Storage Size" />
            </div>
          </div>
        );
      })}
      
      <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '12px', height: '12px', background: '#06b6d4', borderRadius: '2px' }} />
          <span>Table Data Pages</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '12px', height: '12px', background: '#a855f7', borderRadius: '2px' }} />
          <span>B-Tree Index Pages</span>
        </div>
      </div>
    </div>
  );
};

// 3. Tenant Growth Comparison Chart
export const TenantGrowthChart = ({ tenants = [] }) => {
  if (!tenants || tenants.length === 0) return null;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
      {tenants.map(t => {
        const isAlpha = t.code === 'ALPHA';
        const isBeta = t.code === 'BETA';
        const color = isAlpha ? '#06b6d4' : isBeta ? '#6366f1' : '#10b981';

        return (
          <div key={t.tenant_id} className="glass-card" style={{ padding: '16px', borderLeft: `4px solid ${color}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h4 style={{ fontSize: '1rem', color: '#f8fafc' }}>{t.name}</h4>
                <span className="badge" style={{ marginTop: '4px', background: `${color}20`, color }}>
                  {t.profile} growth
                </span>
              </div>
            </div>
            
            <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.82rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Appointments:</span>
                <span className="mono" style={{ fontWeight: 600 }}>{t.appointment_count}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Total Rows:</span>
                <span className="mono" style={{ fontWeight: 600 }}>{t.total_rows}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Daily Growth:</span>
                <span className="mono" style={{ color: '#38bdf8', fontWeight: 600 }}>+{t.growth_rate_mb_day} MB/d</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Current Size:</span>
                <span className="mono" style={{ fontWeight: 600 }}>{t.total_storage_mb} MB</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// 4. Retention Comparison Chart
export const RetentionComparisonChart = ({ retentionData }) => {
  if (!retentionData || !retentionData.without_retention) return null;

  const withoutR = retentionData.without_retention;
  const withR = retentionData.with_retention;

  const width = 640;
  const height = 240;
  const padding = { top: 20, right: 30, bottom: 40, left: 50 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const maxVal = Math.max(...withoutR.map(d => d.storage_mb), 1) * 1.1;

  const xScale = (i) => padding.left + (i / (withoutR.length - 1)) * innerWidth;
  const yScale = (v) => padding.top + innerHeight - (v / maxVal) * innerHeight;

  const pointsWithout = withoutR.map((d, i) => `${xScale(i)},${yScale(d.storage_mb)}`).join(" ");
  const pointsWith = withR.map((d, i) => `${xScale(i)},${yScale(d.storage_mb)}`).join(" ");

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto' }}>
        {/* Grid lines */}
        {[0, 0.5, 1].map((r, idx) => {
          const y = padding.top + innerHeight * (1 - r);
          return (
            <g key={idx}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <text x={padding.left - 8} y={y + 4} fill="#64748b" fontSize="10" textAnchor="end">
                {Math.round(maxVal * r)}M
              </text>
            </g>
          );
        })}

        {/* Without Retention */}
        <polyline fill="none" stroke="#f43f5e" strokeWidth="2.5" strokeDasharray="4 4" points={pointsWithout} />

        {/* With Retention */}
        <polyline fill="none" stroke="#10b981" strokeWidth="3" points={pointsWith} />

        {/* X labels */}
        {withoutR.filter((_, i) => i % 3 === 0).map((d, idx) => {
          const originalIdx = withoutR.findIndex(x => x.day === d.day);
          return (
            <text key={idx} x={xScale(originalIdx)} y={height - padding.bottom + 18} fill="#94a3b8" fontSize="10" textAnchor="middle">
              {d.day}d
            </text>
          );
        })}
      </svg>
      <div style={{ display: 'flex', gap: '24px', justifyContent: 'center', marginTop: '6px', fontSize: '0.8rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '16px', height: '2px', borderTop: '2px dashed #f43f5e' }} />
          <span style={{ color: '#fb7185' }}>Without Retention (Linear Accumulation)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '16px', height: '3px', background: '#10b981' }} />
          <span style={{ color: '#34d399', fontWeight: 600 }}>With Retention ({retentionData.avg_retention_days} Days Window)</span>
        </div>
      </div>
    </div>
  );
};
