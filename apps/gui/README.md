# Stellar Explorer GUI

A native desktop GUI for the Stellar Explorer application.

## Requirements

- Python 3.9+
- Docker (for running the backend)

## Setup

1. **Start the backend** (postgres + api):
   ```bash
   cd /path/to/stellar_explorer
   docker-compose up -d
   ```

2. **Install GUI dependencies**:
   ```bash
   cd apps/gui
   pip install -r requirements.txt
   ```

3. **Run the GUI**:
   ```bash
   python main.py
   ```

## Features

- **Dashboard**: Overview of tracked accounts, watchlists, and transactions
- **Accounts**: View all tracked Stellar accounts
- **Watchlists**: Create watchlists and add accounts to track
- **Transactions**: View recorded transactions

## Troubleshooting

- **"Connection refused"**: Make sure the backend is running (`docker-compose up -d`)
- **"Module not found"**: Install dependencies (`pip install -r requirements.txt`)
