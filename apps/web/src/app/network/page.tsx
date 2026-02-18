'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeft, Globe } from 'lucide-react'
import { getNetworkInfo } from '@/lib/api'

interface NetworkInfo {
  network: string
  horizon_url: string
  status: string
}

export default function NetworkPage() {
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchNetworkInfo()
  }, [])

  const fetchNetworkInfo = async () => {
    try {
      const data = await getNetworkInfo()
      setNetworkInfo(data)
    } catch (error) {
      console.error('Error fetching network info:', error)
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

        <h1 className="text-4xl font-bold text-white mb-8">Network Information</h1>

        {loading ? (
          <div className="text-center text-gray-400">Loading network info...</div>
        ) : networkInfo ? (
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white/10 backdrop-blur-md rounded-lg p-8 border border-white/20">
              <div className="flex items-center mb-4">
                <Globe className="text-stellar-blue mr-3" size={32} />
                <h2 className="text-2xl font-bold text-white">Network Status</h2>
              </div>
              <div className="space-y-4">
                <div>
                  <p className="text-gray-400 text-sm mb-1">Network</p>
                  <p className="text-white text-lg font-semibold uppercase">{networkInfo.network}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm mb-1">Status</p>
                  <p className="text-green-400 text-lg font-semibold">{networkInfo.status}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm mb-1">Horizon URL</p>
                  <p className="text-white text-sm font-mono break-all">{networkInfo.horizon_url}</p>
                </div>
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-md rounded-lg p-8 border border-white/20">
              <h2 className="text-2xl font-bold text-white mb-4">Statistics</h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Total Accounts</span>
                  <span className="text-white font-semibold">-</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Total Transactions</span>
                  <span className="text-white font-semibold">-</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Total Assets</span>
                  <span className="text-white font-semibold">-</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Latest Ledger</span>
                  <span className="text-white font-semibold">-</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center text-gray-400">Failed to load network information</div>
        )}
      </div>
    </main>
  )
}
