'use client';

import { useEffect, useState } from 'react';

// Types
interface DashboardOverview {
  total_leads: number;
  scored_leads: number;
  contacted_leads: number;
  converted_leads: number;
  active_experiments: number;
  total_experiments: number;
  best_performing_experiment: string | null;
  best_conversion_rate: number;
}

interface PipelineMetrics {
  leads_raw: number;
  leads_scored: number;
  leads_contacted: number;
  leads_responded: number;
  leads_converted: number;
  new_leads_today: number;
  outreach_sent_today: number;
  conversions_today: number;
  score_to_contact_rate: number;
  contact_to_conversion_rate: number;
  overall_conversion_rate: number;
}

interface ExperimentMetrics {
  experiment_id: string;
  name: string;
  variant: string;
  is_active: boolean;
  alpha: number;
  beta: number;
  expected_conversion_rate: number;
  leads_assigned: number;
  outreach_sent: number;
  conversions: number;
  conversion_rate: number;
  responses_received: number;
}

interface ActivityItem {
  timestamp: string;
  event_type: string;
  description: string;
  lead_id?: number;
  experiment_id?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [metrics, setMetrics] = useState<PipelineMetrics | null>(null);
  const [experiments, setExperiments] = useState<ExperimentMetrics[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data
  const fetchData = async () => {
    try {
      const [overviewRes, metricsRes, experimentsRes, activityRes] = await Promise.all([
        fetch(`${API_BASE}/experiments/overview/dashboard`),
        fetch(`${API_BASE}/dashboard/metrics`),
        fetch(`${API_BASE}/experiments/`),
        fetch(`${API_BASE}/dashboard/activity?limit=10`),
      ]);

      if (!overviewRes.ok || !metricsRes.ok || !experimentsRes.ok || !activityRes.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const [overviewData, metricsData, experimentsData, activityData] = await Promise.all([
        overviewRes.json(),
        metricsRes.json(),
        experimentsRes.json(),
        activityRes.json(),
      ]);

      setOverview(overviewData);
      setMetrics(metricsData);
      setExperiments(experimentsData);
      setActivity(activityData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Toggle experiment active status
  const toggleExperiment = async (experimentId: string, currentStatus: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/experiments/${experimentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      if (!res.ok) throw new Error('Failed to update experiment');

      // Refresh data
      await fetchData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update experiment');
    }
  };

  useEffect(() => {
    fetchData();
    // Refresh every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl font-semibold">Error loading dashboard</div>
          <p className="mt-2 text-gray-600">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchData();
            }}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Pipeline Whisperer</h1>
        <p className="text-lg text-gray-600 mt-2">
          Autonomous GTM Agent - Real-time Dashboard
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Total Leads</div>
          <div className="text-3xl font-bold text-gray-900">{overview?.total_leads || 0}</div>
          <div className="text-xs text-green-600 mt-2">+{metrics?.new_leads_today || 0} today</div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Contacted</div>
          <div className="text-3xl font-bold text-blue-600">{overview?.contacted_leads || 0}</div>
          <div className="text-xs text-green-600 mt-2">+{metrics?.outreach_sent_today || 0} today</div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Conversions</div>
          <div className="text-3xl font-bold text-green-600">{overview?.converted_leads || 0}</div>
          <div className="text-xs text-green-600 mt-2">+{metrics?.conversions_today || 0} today</div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-600 mb-1">Conversion Rate</div>
          <div className="text-3xl font-bold text-purple-600">
            {metrics?.overall_conversion_rate.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 mt-2">Overall pipeline</div>
        </div>
      </div>

      {/* Pipeline Funnel */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Pipeline Funnel</h2>
        <div className="space-y-3">
          <FunnelStage
            label="Raw Leads"
            count={metrics?.leads_raw || 0}
            percentage={100}
            color="bg-gray-400"
          />
          <FunnelStage
            label="Scored"
            count={metrics?.leads_scored || 0}
            percentage={((metrics?.leads_scored || 0) / (metrics?.leads_raw || 1)) * 100}
            color="bg-blue-400"
          />
          <FunnelStage
            label="Contacted"
            count={metrics?.leads_contacted || 0}
            percentage={((metrics?.leads_contacted || 0) / (metrics?.leads_raw || 1)) * 100}
            color="bg-indigo-400"
          />
          <FunnelStage
            label="Responded"
            count={metrics?.leads_responded || 0}
            percentage={((metrics?.leads_responded || 0) / (metrics?.leads_raw || 1)) * 100}
            color="bg-purple-400"
          />
          <FunnelStage
            label="Converted"
            count={metrics?.leads_converted || 0}
            percentage={((metrics?.leads_converted || 0) / (metrics?.leads_raw || 1)) * 100}
            color="bg-green-500"
          />
        </div>
      </div>

      {/* Experiments Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Experiments */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">A/B Experiments</h2>
            <span className="text-sm text-gray-600">
              {overview?.active_experiments} / {overview?.total_experiments} active
            </span>
          </div>

          <div className="space-y-4">
            {experiments.map((exp) => (
              <div
                key={exp.experiment_id}
                className="border rounded-lg p-4 hover:border-blue-400 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{exp.name}</h3>
                      <span
                        className={`px-2 py-0.5 text-xs rounded ${
                          exp.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {exp.is_active ? 'Active' : 'Paused'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{exp.variant}</p>
                  </div>

                  <button
                    onClick={() => toggleExperiment(exp.experiment_id, exp.is_active)}
                    className={`px-3 py-1 text-sm rounded ${
                      exp.is_active
                        ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                        : 'bg-green-100 text-green-800 hover:bg-green-200'
                    }`}
                  >
                    {exp.is_active ? 'Pause' : 'Activate'}
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-3 text-sm">
                  <div>
                    <div className="text-gray-600">Thompson Sampling</div>
                    <div className="font-mono text-xs text-gray-800 mt-1">
                      α={exp.alpha.toFixed(1)}, β={exp.beta.toFixed(1)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600">Expected Rate</div>
                    <div className="font-bold text-blue-600">
                      {(exp.expected_conversion_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t text-center text-xs">
                  <div>
                    <div className="text-gray-600">Assigned</div>
                    <div className="font-semibold">{exp.leads_assigned}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Sent</div>
                    <div className="font-semibold">{exp.outreach_sent}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Converted</div>
                    <div className="font-semibold text-green-600">{exp.conversions}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">CVR</div>
                    <div className="font-semibold text-purple-600">
                      {(exp.conversion_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {experiments.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              No experiments configured yet
            </div>
          )}
        </div>

        {/* Activity Feed */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Activity</h2>

          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {activity.map((item, idx) => (
              <div key={idx} className="flex items-start gap-3 pb-3 border-b last:border-0">
                <div className="flex-shrink-0 mt-1">
                  <EventIcon eventType={item.event_type} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">{item.description}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(item.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {activity.length === 0 && (
            <div className="text-center text-gray-500 py-8">No activity yet</div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center text-sm text-gray-500 mt-8">
        <p>Auto-refreshing every 5 seconds • Last updated: {new Date().toLocaleTimeString()}</p>
      </div>
    </div>
  );
}

// Helper Components
function FunnelStage({
  label,
  count,
  percentage,
  color,
}: {
  label: string;
  count: number;
  percentage: number;
  color: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-600">
          {count} ({percentage.toFixed(0)}%)
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div className={`${color} h-3 rounded-full transition-all`} style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
}

function EventIcon({ eventType }: { eventType: string }) {
  const iconClasses = 'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold';

  if (eventType === 'lead.created')
    return <div className={`${iconClasses} bg-blue-100 text-blue-600`}>L</div>;
  if (eventType === 'lead.scored')
    return <div className={`${iconClasses} bg-purple-100 text-purple-600`}>S</div>;
  if (eventType === 'outreach.sent')
    return <div className={`${iconClasses} bg-indigo-100 text-indigo-600`}>O</div>;
  if (eventType === 'lead.converted')
    return <div className={`${iconClasses} bg-green-100 text-green-600`}>🎉</div>;

  return <div className={`${iconClasses} bg-gray-100 text-gray-600`}>•</div>;
}
