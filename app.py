# --- Flask framework imports ---
from flask import Flask, render_template, request, redirect, session  
# --- Database integration ---
from flask_sqlalchemy import SQLAlchemy  
# --- Date and time handling ---
from datetime import date  
# Used for working with and storing the current date (e.g., timestamps, records)

app = Flask(__name__)
app.secret_key = 'secret'

# MySQL DB URI (adjust as per your MySQL setup)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost/finance_app'
db = SQLAlchemy(app)

# ===================== MODELS =====================

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Income(db.Model):
    __tablename__ = 'income'
    income_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    amount = db.Column(db.Float)

class Expenses(db.Model):  # Matches table name 'expenses'
    __tablename__ = 'expenses'
    expense_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    category = db.Column(db.String(50))
    amount = db.Column(db.Float)
    date = db.Column(db.Date)

class Savings(db.Model):
    __tablename__ = 'savings'
    saving_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    amount = db.Column(db.Float)

class SavingsGoal(db.Model):
    __tablename__ = 'savingsgoal'
    goal_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    target_amount = db.Column(db.Float)

    @property
    def current_amount(self):
        total_income = db.session.query(db.func.sum(Income.amount)).filter_by(user_id=self.user_id).scalar() or 0.0
        total_expenses = db.session.query(db.func.sum(Expenses.amount)).filter_by(user_id=self.user_id).scalar() or 0.0
        return total_income - total_expenses


# Create tables
with app.app_context():
    db.create_all()

# ===================== ROUTES =====================

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "Username already exists."
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/')
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['user_id'] = user.user_id
        return redirect('/dashboard')
    return "Invalid credentials"

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    user_id = session['user_id']
    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expenses.query.filter_by(user_id=user_id).all()
    savings = Savings.query.filter_by(user_id=user_id).first()
    return render_template('dashboard.html', incomes=incomes, expenses=expenses, savings=savings)

@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        user_id = session['user_id']
        amount = float(request.form['amount'])
        income = Income(user_id=user_id, amount=amount)
        db.session.add(income)

        # Update or create savings
        savings = Savings.query.filter_by(user_id=user_id).first()
        if savings:
            savings.amount += amount
        else:
            savings = Savings(user_id=user_id, amount=amount)
            db.session.add(savings)

        db.session.commit()
        return redirect('/dashboard')
    return render_template('add_income.html')

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        user_id = session['user_id']
        amount = float(request.form['amount'])
        category = request.form['category']
        today = date.today()

        expense = Expenses(user_id=user_id, amount=amount, category=category, date=today)
        db.session.add(expense)

        savings = Savings.query.filter_by(user_id=user_id).first()
        if savings:
            savings.amount -= amount

        db.session.commit()
        return redirect('/dashboard')
    return render_template('add_expense.html')

@app.route('/api/savings', methods=['GET'])
def api_savings():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401

    user_id = session['user_id']
    savings = Savings.query.filter_by(user_id=user_id).first()
    
    if savings:
        return {
            "user_id": user_id,
            "savings_amount": savings.amount
        }
    else:
        return {
            "user_id": user_id,
            "savings_amount": 0.0
        }
@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expenses.query.filter_by(user_id=user_id).all()
    savings = Savings.query.filter_by(user_id=user_id).first()
    goal = SavingsGoal.query.filter_by(user_id=user_id).first()

    return render_template('reports.html', incomes=incomes, expenses=expenses, savings=savings, goal=goal)

@app.route('/goal', methods=['GET', 'POST'])
def goal():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']

    if request.method == 'POST':
        target = float(request.form['target_amount'])

        # Compute current amount from income - expenses
        total_income = db.session.query(db.func.sum(Income.amount)).filter_by(user_id=user_id).scalar() or 0.0
        total_expenses = db.session.query(db.func.sum(Expenses.amount)).filter_by(user_id=user_id).scalar() or 0.0
        current_amount = total_income - total_expenses

        existing_goal = SavingsGoal.query.filter_by(user_id=user_id).first()

        if existing_goal:
            existing_goal.target_amount = target
        else:
            goal = SavingsGoal(
                user_id=user_id,
                target_amount=target
            )
            db.session.add(goal)

        db.session.commit()
        return redirect('/dashboard')

    return render_template('goal.html')



# ===================== RUN =====================
if __name__ == '__main__':
    app.run(debug=True)
