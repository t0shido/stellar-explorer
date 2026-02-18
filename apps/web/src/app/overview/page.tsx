/**
 * Overview Dashboard Page
 */
'use client';

import { useEffect, useState } from 'react';
import { apiClient, Alert } from '@/lib/api-client';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorMessage from '@/components/ErrorMessage';
import { AlertCircle, Eye, TrendingUp, Shield } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface Stats {
  watchedAccounts: number;
  activeAlerts: number;
  criticalAlerts: number;
  highAlerts: number;
  mediumAlerts: number;
  lowAlerts: number;
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);

      // Load watchlists
      const watchlists = await apiClient.getWatchlists();
      const totalWatched = watchlists.reduce((sum, wl) => sum + wl.member_count, 0);

      // Load alerts
      const alertsResponse = await apiClient.getAlerts({ limit: 100 });
      const allAlerts = alertsResponse.data;
      const unacknowledged = allAlerts.filter(a => !a.acknowledged_at);

      // Calculate stats
      const statsBySeverity = {
        critical: unacknowledged.filter(a => a.severity === 'critical').length,
        error: unacknowledged.filter(a => a.severity === 'error').length,
        warning: unacknowledged.filter(a => a.severity === 'warning').length,
        info: unacknowledged.filter(a => a.severity === 'info').length,
      };

      setStats({
        watchedAccounts: totalWatched,
        activeAlerts: unacknowledged.length,
        criticalAlerts: statsBySeverity.critical,
        highAlerts: statsBySeverity.error,
        mediumAlerts: statsBySeverity.warning,
        lowAlerts: statsBySeverity.info,
      });

      setAlerts(unacknowledged.slice(0, 5));
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!stats) return <ErrorMessage message="No data available" />;

  const alertChartData = [
    { name: 'Critical', value: stats.criticalAlerts, color: '#ef4444' },
    { name: 'High', value: stats.highAlerts, color: '#f97316' },
    { name: 'Medium', value: stats.mediumAlerts, color: '#eab308' },
    { name: 'Low', value: stats.lowAlerts, color: '#3b82f6' },
  ].filter(item => item.value > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Overview</h1>
        <p className="text-gray-600 mt-1">Monitor your Stellar network surveillance</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Watched Accounts"
          value={stats.watchedAccounts}
          icon={<Eye className="h-6 w-6 text-blue-600" />}
          bgColor="bg-blue-50"
        />
        <StatCard
          title="Active Alerts"
          value={stats.activeAlerts}
          icon={<AlertCircle className="h-6 w-6 text-orange-600" />}
          bgColor="bg-orange-50"
        />
        <StatCard
          title="Critical Alerts"
          value={stats.criticalAlerts}
          icon={<Shield className="h-6 w-6 text-red-600" />}
          bgColor="bg-red-50"
        />
        <StatCard
          title="Risk Score Avg"
          value="24.5"
          icon={<TrendingUp className="h-6 w-6 text-green-600" />}
          bgColor="bg-green-50"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerts by Severity Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Alerts by Severity
          </h2>
          {alertChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={alertChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {alertChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-500">
              No active alerts
            </div>
          )}
        </div>

        {/* Recent Alerts */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Alerts
          </h2>
          <div className="space-y-3">
            {alerts.length > 0 ? (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                >
                  <div className={`mt-1 ${getSeverityColor(alert.severity)}`}>
                    <AlertCircle className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      {alert.alert_type.replace(/_/g, ' ').toUpperCase()}
                    </p>
                    <p className="text-xs text-gray-600 truncate">
                      {alert.account_address || 'System alert'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityBadge(
                      alert.severity
                    )}`}
                  >
                    {alert.severity}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-center text-gray-500 py-8">
                No recent alerts
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  bgColor,
}: {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  bgColor: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        </div>
        <div className={`${bgColor} p-3 rounded-lg`}>{icon}</div>
      </div>
    </div>
  );
}

function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: 'text-red-600',
    error: 'text-orange-600',
    warning: 'text-yellow-600',
    info: 'text-blue-600',
  };
  return colors[severity] || 'text-gray-600';
}

function getSeverityBadge(severity: string): string {
  const badges: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    error: 'bg-orange-100 text-orange-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
  };
  return badges[severity] || 'bg-gray-100 text-gray-800';
}
