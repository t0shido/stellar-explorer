#!/usr/bin/env python3
"""
Stellar Explorer GUI - Desktop application for tracking Stellar accounts
"""
import customtkinter as ctk
import requests
from datetime import datetime
from typing import Optional
import threading

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class StellarExplorerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Stellar Explorer")
        self.geometry("1200x700")
        self.minsize(900, 600)
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Show dashboard by default
        self.show_dashboard()
    
    def create_sidebar(self):
        """Create the navigation sidebar"""
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="⭐ Stellar Explorer",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", self.show_dashboard),
            ("Accounts", self.show_accounts),
            ("Watchlists", self.show_watchlists),
            ("Transactions", self.show_transactions),
        ]
        
        for i, (name, command) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                command=command,
                height=40,
                anchor="w",
                font=ctk.CTkFont(size=14)
            )
            btn.grid(row=i, column=0, padx=20, pady=5, sticky="ew")
            self.nav_buttons[name] = btn
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="● Connected",
            text_color="green",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=7, column=0, padx=20, pady=20)
    
    def clear_main_frame(self):
        """Clear the main content area"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        """Show the dashboard view"""
        self.clear_main_frame()
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Stats frame
        stats_frame = ctk.CTkFrame(self.main_frame)
        stats_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Fetch stats in background
        threading.Thread(target=self._load_dashboard_stats, args=(stats_frame,), daemon=True).start()
    
    def _load_dashboard_stats(self, stats_frame):
        """Load dashboard statistics from API"""
        try:
            # Get accounts count
            accounts = self.api_get("/accounts/")
            account_count = len(accounts) if accounts else 0
            
            # Get watchlists count
            watchlists = self.api_get("/watchlists")
            watchlist_count = len(watchlists) if watchlists else 0
            
            # Get transactions count
            transactions = self.api_get("/transactions/")
            tx_count = len(transactions) if transactions else 0
            
            # Update UI on main thread
            self.after(0, lambda: self._update_dashboard_ui(
                stats_frame, account_count, watchlist_count, tx_count
            ))
        except Exception as e:
            self.after(0, lambda: self._show_error(stats_frame, str(e)))
    
    def _update_dashboard_ui(self, stats_frame, accounts, watchlists, transactions):
        """Update dashboard UI with stats"""
        stats = [
            ("Tracked Accounts", accounts, "👤"),
            ("Watchlists", watchlists, "📋"),
            ("Transactions", transactions, "💸"),
        ]
        
        for i, (label, value, icon) in enumerate(stats):
            card = ctk.CTkFrame(stats_frame)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            
            icon_label = ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=32))
            icon_label.pack(pady=(20, 5))
            
            value_label = ctk.CTkLabel(
                card, 
                text=str(value),
                font=ctk.CTkFont(size=36, weight="bold")
            )
            value_label.pack()
            
            name_label = ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            name_label.pack(pady=(5, 20))
    
    def show_accounts(self):
        """Show the accounts view"""
        self.clear_main_frame()
        
        # Title row
        title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        title_frame.grid_columnconfigure(1, weight=1)
        
        title = ctk.CTkLabel(
            title_frame,
            text="Tracked Accounts",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            title_frame,
            text="↻ Refresh",
            width=100,
            command=self.show_accounts
        )
        refresh_btn.grid(row=0, column=2, padx=5)
        
        # Accounts list
        list_frame = ctk.CTkScrollableFrame(self.main_frame)
        list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Load accounts
        threading.Thread(target=self._load_accounts, args=(list_frame,), daemon=True).start()
    
    def _load_accounts(self, list_frame):
        """Load accounts from API"""
        try:
            accounts = self.api_get("/accounts/")
            self.after(0, lambda: self._display_accounts(list_frame, accounts))
        except Exception as e:
            self.after(0, lambda: self._show_error(list_frame, str(e)))
    
    def _display_accounts(self, list_frame, accounts):
        """Display accounts in the list"""
        if not accounts:
            empty_label = ctk.CTkLabel(
                list_frame,
                text="No accounts tracked yet.\nAdd accounts via Watchlists.",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.grid(row=0, column=0, pady=50)
            return
        
        # Header
        headers = ["Address", "Risk Score", "First Seen", "Last Seen"]
        header_frame = ctk.CTkFrame(list_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        for i, header in enumerate(headers):
            lbl = ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            lbl.grid(row=0, column=i, padx=10, pady=5, sticky="w")
        
        # Rows
        for idx, account in enumerate(accounts, start=1):
            row_frame = ctk.CTkFrame(list_frame)
            row_frame.grid(row=idx, column=0, sticky="ew", pady=2)
            row_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
            
            address = account.get("address", "N/A")
            short_addr = f"{address[:8]}...{address[-8:]}" if len(address) > 20 else address
            
            values = [
                short_addr,
                f"{account.get('risk_score', 0):.1f}",
                self._format_date(account.get("first_seen")),
                self._format_date(account.get("last_seen")),
            ]
            
            for i, val in enumerate(values):
                lbl = ctk.CTkLabel(row_frame, text=val)
                lbl.grid(row=0, column=i, padx=10, pady=8, sticky="w")
    
    def show_watchlists(self):
        """Show the watchlists view"""
        self.clear_main_frame()
        
        # Title row
        title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        title_frame.grid_columnconfigure(1, weight=1)
        
        title = ctk.CTkLabel(
            title_frame,
            text="Watchlists",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")
        
        # Add watchlist button
        add_btn = ctk.CTkButton(
            title_frame,
            text="+ New Watchlist",
            width=140,
            command=self._show_add_watchlist_dialog
        )
        add_btn.grid(row=0, column=2, padx=5)
        
        # Watchlists list
        list_frame = ctk.CTkScrollableFrame(self.main_frame)
        list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Load watchlists
        threading.Thread(target=self._load_watchlists, args=(list_frame,), daemon=True).start()
    
    def _load_watchlists(self, list_frame):
        """Load watchlists from API"""
        try:
            watchlists = self.api_get("/watchlists")
            self.after(0, lambda: self._display_watchlists(list_frame, watchlists))
        except Exception as e:
            self.after(0, lambda: self._show_error(list_frame, str(e)))
    
    def _display_watchlists(self, list_frame, watchlists):
        """Display watchlists"""
        if not watchlists:
            empty_label = ctk.CTkLabel(
                list_frame,
                text="No watchlists yet.\nClick '+ New Watchlist' to create one.",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.grid(row=0, column=0, pady=50)
            return
        
        for idx, wl in enumerate(watchlists):
            card = ctk.CTkFrame(list_frame)
            card.grid(row=idx, column=0, sticky="ew", pady=5)
            card.grid_columnconfigure(1, weight=1)
            
            # Watchlist info
            name_label = ctk.CTkLabel(
                card,
                text=wl.get("name", "Unnamed"),
                font=ctk.CTkFont(size=16, weight="bold")
            )
            name_label.grid(row=0, column=0, padx=15, pady=(10, 0), sticky="w")
            
            desc_label = ctk.CTkLabel(
                card,
                text=wl.get("description", "No description"),
                text_color="gray"
            )
            desc_label.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")
            
            count_label = ctk.CTkLabel(
                card,
                text=f"{wl.get('member_count', 0)} accounts",
                font=ctk.CTkFont(size=14)
            )
            count_label.grid(row=0, column=1, rowspan=2, padx=15, sticky="e")
            
            # Add account button
            add_btn = ctk.CTkButton(
                card,
                text="+ Add Account",
                width=120,
                command=lambda wl_id=wl.get("id"): self._show_add_account_dialog(wl_id)
            )
            add_btn.grid(row=0, column=2, rowspan=2, padx=15, pady=10)
    
    def _show_add_watchlist_dialog(self):
        """Show dialog to create a new watchlist"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("New Watchlist")
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 250) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Name
        name_label = ctk.CTkLabel(dialog, text="Name:")
        name_label.pack(padx=20, pady=(20, 5), anchor="w")
        
        name_entry = ctk.CTkEntry(dialog, width=360)
        name_entry.pack(padx=20)
        
        # Description
        desc_label = ctk.CTkLabel(dialog, text="Description:")
        desc_label.pack(padx=20, pady=(15, 5), anchor="w")
        
        desc_entry = ctk.CTkEntry(dialog, width=360)
        desc_entry.pack(padx=20)
        
        # Status label
        status_label = ctk.CTkLabel(dialog, text="", text_color="red")
        status_label.pack(pady=10)
        
        def create():
            name = name_entry.get().strip()
            if not name:
                status_label.configure(text="Name is required")
                return
            
            try:
                result = self.api_post("/watchlists", {
                    "name": name,
                    "description": desc_entry.get().strip()
                })
                dialog.destroy()
                self.show_watchlists()
            except Exception as e:
                status_label.configure(text=str(e))
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, width=100)
        cancel_btn.pack(side="left", padx=10)
        
        create_btn = ctk.CTkButton(btn_frame, text="Create", command=create, width=100)
        create_btn.pack(side="left", padx=10)
    
    def _show_add_account_dialog(self, watchlist_id: int):
        """Show dialog to add an account to a watchlist"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Account")
        dialog.geometry("500x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Address
        addr_label = ctk.CTkLabel(dialog, text="Stellar Address (starts with G):")
        addr_label.pack(padx=20, pady=(20, 5), anchor="w")
        
        addr_entry = ctk.CTkEntry(dialog, width=460, placeholder_text="GXXXX...")
        addr_entry.pack(padx=20)
        
        # Status label
        status_label = ctk.CTkLabel(dialog, text="", text_color="red")
        status_label.pack(pady=10)
        
        def add():
            address = addr_entry.get().strip()
            if not address or not address.startswith("G"):
                status_label.configure(text="Invalid address. Must start with G.")
                return
            
            status_label.configure(text="Adding...", text_color="gray")
            dialog.update()
            
            try:
                result = self.api_post(f"/watchlists/{watchlist_id}/accounts", {
                    "address": address
                })
                dialog.destroy()
                self.show_watchlists()
            except Exception as e:
                status_label.configure(text=str(e), text_color="red")
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, width=100)
        cancel_btn.pack(side="left", padx=10)
        
        add_btn = ctk.CTkButton(btn_frame, text="Add", command=add, width=100)
        add_btn.pack(side="left", padx=10)
    
    def show_transactions(self):
        """Show the transactions view"""
        self.clear_main_frame()
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="Transactions",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Transactions list
        list_frame = ctk.CTkScrollableFrame(self.main_frame)
        list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Load transactions
        threading.Thread(target=self._load_transactions, args=(list_frame,), daemon=True).start()
    
    def _load_transactions(self, list_frame):
        """Load transactions from API"""
        try:
            transactions = self.api_get("/transactions/")
            self.after(0, lambda: self._display_transactions(list_frame, transactions))
        except Exception as e:
            self.after(0, lambda: self._show_error(list_frame, str(e)))
    
    def _display_transactions(self, list_frame, transactions):
        """Display transactions"""
        if not transactions:
            empty_label = ctk.CTkLabel(
                list_frame,
                text="No transactions recorded yet.",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_label.grid(row=0, column=0, pady=50)
            return
        
        # Header
        headers = ["Hash", "Source", "Ledger", "Fee", "Created"]
        header_frame = ctk.CTkFrame(list_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        for i, header in enumerate(headers):
            lbl = ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold")
            )
            lbl.grid(row=0, column=i, padx=10, pady=5, sticky="w")
        
        # Rows
        for idx, tx in enumerate(transactions[:50], start=1):  # Limit to 50
            row_frame = ctk.CTkFrame(list_frame)
            row_frame.grid(row=idx, column=0, sticky="ew", pady=2)
            row_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
            
            tx_hash = tx.get("tx_hash", "N/A")
            short_hash = f"{tx_hash[:8]}..." if len(tx_hash) > 12 else tx_hash
            
            source = tx.get("source_account_id", "N/A")
            short_source = f"{source[:8]}..." if len(str(source)) > 12 else source
            
            values = [
                short_hash,
                short_source,
                str(tx.get("ledger", "N/A")),
                str(tx.get("fee_charged", 0)),
                self._format_date(tx.get("created_at")),
            ]
            
            for i, val in enumerate(values):
                lbl = ctk.CTkLabel(row_frame, text=val)
                lbl.grid(row=0, column=i, padx=10, pady=8, sticky="w")
    
    # API Helper Methods
    def api_get(self, endpoint: str):
        """Make GET request to API"""
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    
    def api_post(self, endpoint: str, data: dict):
        """Make POST request to API"""
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            json=data,
            timeout=10
        )
        if response.status_code >= 400:
            error = response.json().get("detail", "Unknown error")
            raise Exception(error)
        return response.json()
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Format ISO date string for display"""
        if not date_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return date_str[:16] if len(date_str) > 16 else date_str
    
    def _show_error(self, parent, message: str):
        """Show error message in parent frame"""
        error_label = ctk.CTkLabel(
            parent,
            text=f"Error: {message}",
            text_color="red",
            font=ctk.CTkFont(size=14)
        )
        error_label.grid(row=0, column=0, pady=50)


def main():
    app = StellarExplorerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
