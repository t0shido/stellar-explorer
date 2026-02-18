'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { getAccounts } from '@/lib/api'

interface Account {
  id: number
  account_id: string
  balance: number
  sequence: string
  created_at: string
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
      setAccounts(data)
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
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Account ID</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Balance</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Sequence</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Created</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id} className="border-t border-white/10 hover:bg-white/5">
                    <td className="px-6 py-4 text-sm text-white font-mono">
                      {account.account_id.substring(0, 8)}...{account.account_id.substring(account.account_id.length - 8)}
                    </td>
                    <td className="px-6 py-4 text-sm text-white">{account.balance} XLM</td>
                    <td className="px-6 py-4 text-sm text-gray-300">{account.sequence}</td>
                    <td className="px-6 py-4 text-sm text-gray-300">
                      {new Date(account.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}
