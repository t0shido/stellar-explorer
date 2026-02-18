/**
 * Typed API client for Stellar Explorer
 */
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Debug: Log the API base URL
console.log('API_BASE_URL:', API_BASE_URL);
console.log('process.env.NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL);

// Types
export interface Account {
  id: number;
  address: string;
  label: string | null;
  risk_score: number;
  first_seen: string;
  last_seen: string | null;
  metadata: Record<string, any>;
  balances: Balance[];
}

export interface Balance {
  asset_code: string | null;
  asset_issuer: string | null;
  asset_type: string;
  balance: string;
  limit: string | null;
  buying_liabilities: string;
  selling_liabilities: string;
}

export interface Transaction {
  tx_hash: string;
  ledger: number;
  created_at: string;
  operation_count: number;
  successful: boolean;
  fee_charged: number;
  memo: string | null;
}

export interface Counterparty {
  account_id: number;
  account_address: string;
  account_label: string | null;
  asset_code: string | null;
  asset_issuer: string | null;
  tx_count: number;
  total_amount: string;
  last_seen: string;
  direction: 'sent' | 'received';
}

export interface Alert {
  id: number;
  account_id: number | null;
  account_address: string | null;
  asset_id: number | null;
  asset_code: string | null;
  alert_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  payload: Record<string, any>;
  created_at: string;
  acknowledged_at: string | null;
}

export interface Flag {
  id: number;
  account_id: number;
  account_address: string;
  flag_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  evidence: Record<string, any>;
  created_at: string;
  resolved_at: string | null;
}

export interface Watchlist {
  id: number;
  name: string;
  description: string | null;
  member_count: number;
}

export interface WatchlistMember {
  id: number;
  account_id: number;
  account_address: string;
  reason: string | null;
  added_at: string;
}

export interface AssetHolder {
  account_id: number;
  account_address: string;
  account_label: string | null;
  balance: string;
  percentage: number;
}

export interface AssetTopHolders {
  asset_code: string;
  asset_issuer: string | null;
  asset_type: string;
  total_holders: number;
  total_supply: string;
  holders: AssetHolder[];
}

export interface PaginationMetadata {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationMetadata;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Health
  async getHealth() {
    const { data } = await this.client.get('/health');
    return data;
  }

  // Accounts
  async getAccount(address: string): Promise<Account> {
    const { data } = await this.client.get(`/accounts/${address}`);
    return data;
  }

  async getAccountActivity(
    address: string,
    params?: { limit?: number; page?: number }
  ): Promise<PaginatedResponse<Transaction>> {
    const { data } = await this.client.get(`/accounts/${address}/activity`, { params });
    return data;
  }

  async getAccountCounterparties(
    address: string,
    params?: { limit?: number }
  ): Promise<Counterparty[]> {
    const { data } = await this.client.get(`/accounts/${address}/counterparties`, { params });
    return data;
  }

  // Watchlists
  async getWatchlists(): Promise<Watchlist[]> {
    const { data } = await this.client.get('/watchlists');
    return data;
  }

  async getWatchlist(id: number): Promise<Watchlist & { members: WatchlistMember[] }> {
    const { data } = await this.client.get(`/watchlists/${id}`);
    return data;
  }

  async createWatchlist(name: string, description?: string): Promise<Watchlist> {
    const { data } = await this.client.post('/watchlists', { name, description });
    return data;
  }

  async addAccountToWatchlist(
    watchlistId: number,
    address: string,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    const { data } = await this.client.post(`/watchlists/${watchlistId}/accounts`, {
      address,
      reason,
    });
    return data;
  }

  // Assets
  async getAssetTopHolders(
    assetCode: string,
    assetIssuer?: string,
    limit?: number
  ): Promise<AssetTopHolders> {
    const { data } = await this.client.get('/assets/top-holders', {
      params: { asset_code: assetCode, asset_issuer: assetIssuer, limit },
    });
    return data;
  }

  // Alerts
  async getAlerts(params?: {
    severity?: string;
    acknowledged?: boolean;
    page?: number;
    limit?: number;
  }): Promise<PaginatedResponse<Alert>> {
    const { data } = await this.client.get('/alerts', { params });
    return data;
  }

  async acknowledgeAlert(id: number): Promise<{ success: boolean; message: string }> {
    const { data } = await this.client.post(`/alerts/${id}/ack`);
    return data;
  }

  // Flags
  async createManualFlag(
    address: string,
    flagType: string,
    severity: string,
    reason: string,
    evidence?: Record<string, any>
  ): Promise<Flag> {
    const { data } = await this.client.post('/flags/manual', {
      address,
      flag_type: flagType,
      severity,
      reason,
      evidence,
    });
    return data;
  }
}

export const apiClient = new ApiClient();
