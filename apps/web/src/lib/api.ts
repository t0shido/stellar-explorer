import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Accounts
export const getAccounts = async () => {
  const response = await api.get('/accounts/')
  return response.data
}

export const getAccount = async (accountId: string) => {
  const response = await api.get(`/accounts/${accountId}`)
  return response.data
}

// Transactions
export const getTransactions = async () => {
  const response = await api.get('/transactions/')
  return response.data
}

export const getTransaction = async (txHash: string) => {
  const response = await api.get(`/transactions/${txHash}`)
  return response.data
}

// Stellar Network
export const getNetworkInfo = async () => {
  const response = await api.get('/stellar/network')
  return response.data
}

export const getStellarAccount = async (accountId: string) => {
  const response = await api.get(`/stellar/account/${accountId}`)
  return response.data
}

export const getRecentTransactions = async (limit: number = 10) => {
  const response = await api.get(`/stellar/transactions/recent?limit=${limit}`)
  return response.data
}

export default api
