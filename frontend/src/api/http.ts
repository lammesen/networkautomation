import axios, { AxiosInstance } from 'axios';

export interface Device {
  id: number;
  hostname: string;
  mgmt_ip: string;
  vendor?: string;
  role?: string;
  site?: string;
  tags?: string;
}

export interface JobSummary {
  id: number;
  type: string;
  status: string;
  requested_at: string;
  started_at?: string;
  finished_at?: string;
  target_summary?: Record<string, unknown>;
  result_summary?: Record<string, unknown>;
}

export interface JobLogEntry {
  ts: string;
  level: string;
  message: string;
  host?: string;
  extra?: Record<string, unknown>;
}

export interface CompliancePolicy {
  id: number;
  name: string;
  scope: Record<string, unknown>;
  definition: Record<string, unknown>;
}

export const createHttpClient = (token: string | null): AxiosInstance => {
  const instance = axios.create({ baseURL: '/api' });
  if (token) {
    instance.defaults.headers.common.Authorization = `Bearer ${token}`;
  }
  return instance;
};
