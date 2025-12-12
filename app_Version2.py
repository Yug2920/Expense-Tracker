from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
from io import StringIO, BytesIO
import csv
import os

# local module imports (keep same filenames as in your repo)
from models_Version2 import db, User, Expense
from forms_Version2 import RegisterForm, LoginForm, ExpenseForm

def create_app(test_config=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_this_secret_for_prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///expenses.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.before_first_request
    def create_tables():
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            existing = User.query.filter_by(username=form.username.data).first()
            if existing:
                flash('Username already taken.', 'warning')
                return render_template('register.html', form=form)
            hashed_pw = generate_password_hash(form.password.data, method='sha256')
            user = User(username=form.username.data, password=hashed_pw)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                flash('Logged in successfully.', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Login unsuccessful. Check username and password.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        # summary for charts
        summary = (
            db.session.query(Expense.category, db.func.sum(Expense.amount))
            .filter(Expense.user_id == current_user.id)
            .group_by(Expense.category)
            .all()
        )
        categories = [s[0] for s in summary]
        amounts = [float(s[1]) for s in summary]
        return render_template('dashboard.html', expenses=expenses, categories=categories, amounts=amounts)

    @app.route('/add', methods=['GET', 'POST'])
    @login_required
    def add_expense():
        form = ExpenseForm()
        if form.validate_on_submit():
            expense = Expense(
                amount=float(form.amount.data),
                category=form.category.data,
                date=form.date.data or date.today(),
                description=form.description.data,
                user_id=current_user.id
            )
            db.session.add(expense)
            db.session.commit()
            flash('Expense added!', 'success')
            return redirect(url_for('dashboard'))
        return render_template('add_expense.html', form=form)

    @app.route('/delete/<int:expense_id>', methods=['POST'])
    @login_required
    def delete_expense(expense_id):
        expense = Expense.query.get_or_404(expense_id)
        if expense.user_id != current_user.id:
            flash('Unauthorized.', 'danger')
            return redirect(url_for('dashboard'))
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted.', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/export')
    @login_required
    def export():
        # export current user's expenses as CSV
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['id', 'amount', 'category', 'date', 'description', 'created_at'])
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        for e in expenses:
            cw.writerow([e.id, float(e.amount), e.category, e.date.isoformat(), e.description or '', e.created_at.isoformat()])
        si.seek(0)
        return send_file(
            BytesIO(si.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'expenses_{current_user.username}_{datetime.utcnow().date()}.csv'
        )

    @app.route('/export/pdf')
    @login_required
    def export_pdf():
        """
        Generate a PDF report of the current user's expenses.
        Uses reportlab if installed. If reportlab is not available, redirects with a flash.
        """
        try:
            # import locally to avoid failing app start if reportlab missing
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
        except Exception as exc:
            flash('PDF generation requires the reportlab package. Install with: pip install reportlab', 'warning')
            return redirect(url_for('dashboard'))

        buffer = BytesIO()
        page_width, page_height = letter
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setTitle(f'Expense Report - {current_user.username}')

        # Header
        c.setFont('Helvetica-Bold', 14)
        c.drawString(inch, page_height - inch, f'Expense Report for {current_user.username}')
        c.setFont('Helvetica', 10)
        c.drawString(inch, page_height - inch - 14, f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}')
        c.line(inch, page_height - inch - 18, page_width - inch, page_height - inch - 18)

        # Table header
        y = page_height - inch - 40
        left_margin = inch
        col_amount = left_margin
        col_category = left_margin + 80
        col_date = left_margin + 220
        col_desc = left_margin + 320

        c.setFont('Helvetica-Bold', 10)
        c.drawString(col_amount, y, 'Amount')
        c.drawString(col_category, y, 'Category')
        c.drawString(col_date, y, 'Date')
        c.drawString(col_desc, y, 'Description')
        y -= 12
        c.setLineWidth(0.5)
        c.line(left_margin, y, page_width - inch, y)
        y -= 12
        c.setFont('Helvetica', 10)

        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        if not expenses:
            c.drawString(left_margin, y, 'No expenses found.')
            y -= 20

        for e in expenses:
            if y < inch + 40:  # avoid bottom, create new page
                c.showPage()
                # recreate header on new page
                c.setFont('Helvetica-Bold', 14)
                c.drawString(inch, page_height - inch, f'Expense Report for {current_user.username}')
                c.setFont('Helvetica', 10)
                c.drawString(inch, page_height - inch - 14, f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}')
                c.line(inch, page_height - inch - 18, page_width - inch, page_height - inch - 18)
                y = page_height - inch - 40
                c.setFont('Helvetica-Bold', 10)
                c.drawString(col_amount, y, 'Amount')
                c.drawString(col_category, y, 'Category')
                c.drawString(col_date, y, 'Date')
                c.drawString(col_desc, y, 'Description')
                y -= 12
                c.line(left_margin, y, page_width - inch, y)
                y -= 12
                c.setFont('Helvetica', 10)

            desc = (e.description or '').replace('\n', ' ')[:80]
            c.drawRightString(col_amount + 60, y, f'{float(e.amount):.2f}')
            c.drawString(col_category, y, e.category)
            c.drawString(col_date, y, e.date.isoformat())
            c.drawString(col_desc, y, desc)
            y -= 16

        c.showPage()
        c.save()
        buffer.seek(0)
        filename = f'expenses_{current_user.username}_{datetime.utcnow().date()}.pdf'
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)

    @app.route('/api/expenses')
    @login_required
    def api_expenses():
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
        data = [
            {
                'id': e.id,
                'amount': float(e.amount),
                'category': e.category,
                'date': e.date.isoformat(),
                'description': e.description
            } for e in expenses
        ]
        return jsonify(data)

    return app

if __name__ == '__main__':
    application = create_app()
    application.run(debug=True)
