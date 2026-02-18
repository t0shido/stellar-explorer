'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeft, CheckCircle, XCircle } from 'lucide-react'
import { getTransactions } from '@/lib/api'

interface Transaction {
  id: number
  hash: string
  source_account: string
  fee: number
  operation_count: number
  successful: boolean
  ledger: number
  created_at: string
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTransactions()
  }, [])

  const fetchTransactions = async () => {
    try {
      const data = await getTransactions()
      setTransactions(data)
    } catch (error) {
      console.error('Error fetching transactions:', error)
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

        <h1 className="text-4xl font-bold text-white mb-8">Transactions</h1>

        {loading ? (
          <div className="text-center text-gray-400">Loading transactions...</div>
        ) : transactions.length === 0 ? (
          <div className="text-center text-gray-400">No transactions found</div>
        ) : (
          <div className="bg-white/10 backdrop-blur-md rounded-lg border border-white/20 overflow-hidden">
            <table className="w-full">
              <thead className="bg-white/5">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Hash</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Source</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Operations</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Ledger</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-t border-white/10 hover:bg-white/5">
                    <td className="px-6 py-4 text-sm text-white font-mono">
                      {tx.hash.substring(0, 8)}...{tx.hash.substring(tx.hash.length - 8)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-300 font-mono">
                      {tx.source_account.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 text-sm text-white">{tx.operation_count}</td>
                    <td className="px-6 py-4 text-sm">
                      {tx.successful ? (
                        <span className="flex items-center text-green-400">
                          <CheckCircle size={16} className="mr-1" />
                          Success
                        </span>
                      ) : (
                        <span className="flex items-center text-red-400">
                          <XCircle size={16} className="mr-1" />
                          Failed
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-300">{tx.ledger}</td>
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
