# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import pandas as pd
from datetime import datetime
# Import libraries for Clerk, Charting, and PDF (install these!)
# from clerk_sdk import Clerk # Placeholder: You would install and configure the official Clerk SDK
# import matplotlib.pyplot as plt # For Chart generation
# from reportlab.pdfgen import canvas # For PDF Report generation

app = Flask(__name__)
# IMPORTANT: Replace with a secure, long, random key
app.secret_key = 'YOUR_SUPER_SECRET_KEY_HERE'
DATABASE = 'expense_tracker.db'

# --- 1. Database Initialization ---
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # 'user_id' is crucial for multi-user support and is where Clerk/Auth data comes in
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL, -- 'INCOME' or 'EXPENSE'
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Call this once when the app starts
init_db()

# --- 2. Authentication Mock/Placeholder ---
# In a real app, you would use a middleware/decorator provided by Clerk
# to verify the user's session and get the actual 'current_user_id'.

def get_current_user_id():
    # Placeholder: In a real app, this would come from Clerk/Auth session data.
    # We are using a simple session mock for this example.
    return session.get('user_id', 'mock_user_123') # Default to a mock ID if not logged in

# Mock login (replace with actual Clerk redirect/callback flow)
@app.route('/login')
def login():
    # After successful Clerk sign-in, you would set the session user ID
    session['user_id'] = 'clerk_user_abc_456'
    return redirect(url_for('dashboard'))

# Mock logout (replace with actual Clerk sign-out flow)
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


# --- 3. Core Endpoints ---

@app.route('/')
def index():
    if 'user_id' not in session:
        # Redirect to the authentication page placeholder
        return render_template('login.html', clerk_publishable_key='YOUR_CLERK_PUBLISHABLE_KEY')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    user_id = get_current_user_id()
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fetch all transactions for the logged-in user
    transactions = cursor.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC', (user_id,)).fetchall()
    
    # Calculate wallet/balance (remaining money)
    income_query = cursor.execute('SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = "INCOME"', (user_id,)).fetchone()[0] or 0
    expense_query = cursor.execute('SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = "EXPENSE"', (user_id,)).fetchone()[0] or 0
    wallet_balance = income_query - expense_query
    
    conn.close()
    
    # We'll assume a base currency for display (e.g., USD)
    base_currency = 'USD' 
    
    return render_template('index.html', 
                           transactions=transactions, 
                           balance=wallet_balance,
                           base_currency=base_currency)

@app.route('/add', methods=['POST'])
def add_transaction():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.form
    type = data.get('type') # 'INCOME' or 'EXPENSE'
    description = data.get('description')
    amount = float(data.get('amount'))
    currency = data.get('currency', 'USD') # Default currency
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (user_id, type, description, amount, currency)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, type, description, amount, currency))
    conn.commit()
    conn.close()
    
    return redirect(url_for('dashboard'))


# --- 4. Report Generation (PDF/Chart) Placeholder ---

@app.route('/report/pdf')
def generate_pdf_report():
    user_id = get_current_user_id()
    # 1. Fetch data for the user (same as dashboard, but perhaps date-filtered)
    # 2. Use 'reportlab' to create a PDF document
    # 3. Return the PDF file as a response
    return "PDF Report Generation (requires reportlab library)", 200

@app.route('/report/chart')
def generate_chart():
    user_id = get_current_user_id()
    # 1. Fetch data
    # 2. Use 'matplotlib' to create a chart (e.g., pie chart of expense categories)
    # 3. Save the chart as an image (PNG)
    # 4. Return the chart image or a page that displays it
    return "Chart Generation (requires matplotlib library)", 200

# --- 5. Currency Conversion (Placeholder) ---
# For full currency support, you would integrate a currency exchange API (e.g., ExchangeRate-API)
@app.route('/convert', methods=['POST'])
def convert_currency():
    # Logic to convert an amount from one currency to the base currency
    # For simplicity, this is not implemented but shows where it would go.
    return "Currency Conversion Endpoint Placeholder", 200

if __name__ == '__main__':
    # Flask runs on http://127.0.0.1:5000/
    app.run(debug=True)
