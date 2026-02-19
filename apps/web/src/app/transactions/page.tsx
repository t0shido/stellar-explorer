// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeft, CheckCircle, XCircle } from 'lucide-react'
import { getTransactions } from '@/lib/api'

type Transaction = {
  id?: number
  tx_hash?: string
  hash?: string
  source_account_id?: number | string | null
  source_account?: string | null
  fee_charged?: number
  fee?: number
  operation_count?: number
  successful?: boolean
  ledger?: number
  created_at?: string
  memo?: string | null
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
      const normalized: Transaction[] = Array.isArray(data)
        ? data.map((tx: Record<string, any>): Transaction => ({
            id: tx.id,
            tx_hash: tx.tx_hash || tx.hash,
            source_account_id: tx.source_account_id ?? tx.source_account,
            operation_count: tx.operation_count,
            successful: tx.successful,
            ledger: tx.ledger,
            created_at: tx.created_at,
            fee_charged: tx.fee_charged ?? tx.fee,
            memo: tx.memo ?? null,
          }))
        : []
      setTransactions(normalized)
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
                {transactions.map((tx, idx) => (
                  <tr key={tx.id ?? idx} className="border-t border-white/10 hover:bg-white/5">
                    <td className="px-6 py-4 text-sm text-white font-mono">
                      {tx.tx_hash
                        ? `${tx.tx_hash.substring(0, 8)}...${tx.tx_hash.substring(tx.tx_hash.length - 8)}`
                        : '—'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-300 font-mono">
                      {tx.source_account_id
                        ? String(tx.source_account_id).substring(0, 8) + '...'
                        : '—'}
                    </td>
                    <td className="px-6 py-4 text-sm text-white">{tx.operation_count ?? '—'}</td>
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
