import Link from 'next/link'
import { Search, Activity, Database } from 'lucide-react'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-stellar-dark via-gray-900 to-stellar-dark">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <header className="text-center mb-16">
          <h1 className="text-6xl font-bold text-white mb-4">
            Stellar Explorer
          </h1>
          <p className="text-xl text-gray-300">
            Explore the Stellar blockchain network in real-time
          </p>
        </header>

        {/* Search Bar */}
        <div className="max-w-3xl mx-auto mb-16">
          <div className="relative">
            <input
              type="text"
              placeholder="Search by account, transaction hash, or asset..."
              className="w-full px-6 py-4 rounded-lg bg-white/10 backdrop-blur-md text-white placeholder-gray-400 border border-white/20 focus:outline-none focus:ring-2 focus:ring-stellar-blue"
            />
            <Search className="absolute right-4 top-4 text-gray-400" size={24} />
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <Link href="/accounts">
            <div className="bg-white/10 backdrop-blur-md rounded-lg p-8 border border-white/20 hover:bg-white/20 transition-all cursor-pointer">
              <Database className="text-stellar-blue mb-4" size={40} />
              <h3 className="text-2xl font-bold text-white mb-2">Accounts</h3>
              <p className="text-gray-300">
                View account details, balances, and transaction history
              </p>
            </div>
          </Link>

          <Link href="/transactions">
            <div className="bg-white/10 backdrop-blur-md rounded-lg p-8 border border-white/20 hover:bg-white/20 transition-all cursor-pointer">
              <Activity className="text-stellar-blue mb-4" size={40} />
              <h3 className="text-2xl font-bold text-white mb-2">Transactions</h3>
              <p className="text-gray-300">
                Explore recent transactions and network activity
              </p>
            </div>
          </Link>

          <Link href="/network">
            <div className="bg-white/10 backdrop-blur-md rounded-lg p-8 border border-white/20 hover:bg-white/20 transition-all cursor-pointer">
              <Search className="text-stellar-blue mb-4" size={40} />
              <h3 className="text-2xl font-bold text-white mb-2">Network</h3>
              <p className="text-gray-300">
                Monitor network statistics and performance metrics
              </p>
            </div>
          </Link>
        </div>

        {/* Stats */}
        <div className="max-w-6xl mx-auto mt-16 grid md:grid-cols-4 gap-6">
          <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/10">
            <p className="text-gray-400 text-sm mb-2">Network</p>
            <p className="text-2xl font-bold text-white">Testnet</p>
          </div>
          <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/10">
            <p className="text-gray-400 text-sm mb-2">Latest Ledger</p>
            <p className="text-2xl font-bold text-white">-</p>
          </div>
          <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/10">
            <p className="text-gray-400 text-sm mb-2">Transactions</p>
            <p className="text-2xl font-bold text-white">-</p>
          </div>
          <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/10">
            <p className="text-gray-400 text-sm mb-2">Operations</p>
            <p className="text-2xl font-bold text-white">-</p>
          </div>
        </div>
      </div>
    </main>
  )
}
