// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { getAccounts } from '@/lib/api'

type Account = {
  id?: number
  address?: string
  account_id?: string
  risk_score?: number
  first_seen?: string
  last_seen?: string
  sequence?: string
  balance?: number
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAccounts()
  }, [])

  const fetchAccounts = async () => {
    try {
      const data = await getAccounts()
      const normalized: Account[] = Array.isArray(data)
        ? data.map((account: Record<string, any>): Account => ({
            id: account.id,
            address: account.address || account.account_id,
            risk_score: account.risk_score ?? account.risk ?? 0,
            sequence: account.meta_data?.sequence ?? account.sequence,
            first_seen: account.first_seen || account.created_at,
            last_seen: account.last_seen || account.updated_at,
          }))
        : []
      setAccounts(normalized)
    } catch (error) {
      console.error('Error fetching accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-stellar-dark via-gray-900 to-stellar-dark">
      <div className="container mx-auto px-4 py-16">
        <Link href="/" className="inline-flex items-center text-stellar-blue hover:text-blue-400 mb-8">
          <ArrowLeft className="mr-2" size={20} />
          Back to Home
        </Link>

        <h1 className="text-4xl font-bold text-white mb-8">Accounts</h1>

        {loading ? (
          <div className="text-center text-gray-400">Loading accounts...</div>
        ) : accounts.length === 0 ? (
          <div className="text-center text-gray-400">No accounts found</div>
        ) : (
          <div className="bg-white/10 backdrop-blur-md rounded-lg border border-white/20 overflow-hidden">
            <table className="w-full">
              <thead className="bg-white/5">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Address</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Risk</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Sequence</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">First Seen</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account: Account, idx: number) => {
                  const address = account.address || account.account_id || 'Unknown'
                  return (
                    <tr key={account.id ?? idx} className="border-t border-white/10 hover:bg-white/5">
                      <td className="px-6 py-4 text-sm text-white font-mono break-all">
                        {address.length > 20
                          ? `${address.slice(0, 8)}...${address.slice(-8)}`
                          : address}
                      </td>
                      <td className="px-6 py-4 text-sm text-white">
                        {account.risk_score !== undefined ? `${account.risk_score.toFixed(2)}` : '—'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">{account.sequence ?? '—'}</td>
                      <td className="px-6 py-4 text-sm text-gray-300">
                        {account.first_seen ? new Date(account.first_seen).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}
