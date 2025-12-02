
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal, ROUND_HALF_UP

app = Flask(__name__, instance_relative_config=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Models
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    desc = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    payer = db.relationship("Person", backref="paid_expenses")
    # If no shares rows exist, the split is equal among participants
    participants = db.relationship("Person", secondary="expense_participant", backref="participated_expenses")
    shares = db.relationship("ExpenseShare", cascade="all, delete-orphan", backref="expense")

class ExpenseParticipant(db.Model):
    __tablename__ = "expense_participant"
    expense_id = db.Column(db.Integer, db.ForeignKey("expense.id"), primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), primary_key=True)

class ExpenseShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expense.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

# Startup
with app.app_context():
    db.create_all()

def recompute():
    # Compute balances and settlement suggestions from DB
    people = Person.query.order_by(Person.name).all()
    balances = {p.name: Decimal("0.00") for p in people}
    expenses = Expense.query.order_by(Expense.id).all()

    for e in expenses:
        amount = Decimal(str(e.amount))
        payer = e.payer.name
        participants = [p.name for p in e.participants]
        if not participants:
            continue
        balances[payer] += amount
        if e.shares:
            for s in e.shares:
                balances[s.person_id and Person.query.get(s.person_id).name] -= Decimal(str(s.amount))
        else:
            share = (amount / Decimal(len(participants))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for p in participants:
                balances[p] -= share

    # Round balances
    for k, v in balances.items():
        balances[k] = v.quantize(Decimal("0.01"))

    # Greedy settlements
    creditors = [[p, v] for p, v in balances.items() if v > 0]
    debtors = [[p, -v] for p, v in balances.items() if v < 0]
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    settlements = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        d_name, d_amt = debtors[i]
        c_name, c_amt = creditors[j]
        pay = min(d_amt, c_amt)
        settlements.append(f"{d_name} -> {c_name}: ₹{pay.quantize(Decimal('0.01'))}")
        d_amt -= pay
        c_amt -= pay
        if d_amt <= Decimal("0.0001"):
            i += 1
        else:
            debtors[i][1] = d_amt
        if c_amt <= Decimal("0.0001"):
            j += 1
        else:
            creditors[j][1] = c_amt
    return people, expenses, balances, settlements

@app.route("/")
def index():
    people, expenses, balances, settlements = recompute()
    return render_template(
        "index.html",
        people=[p.name for p in people],
        expenses=[{
            "desc": e.desc,
            "amount": float(e.amount),
            "payer": e.payer.name,
            "participants": [p.name for p in e.participants],
            "shares": {Person.query.get(s.person_id).name: float(s.amount) for s in e.shares}
        } for e in expenses],
        balances=balances,
        settlements=settlements
    )

@app.route("/add_person", methods=["POST"])
def add_person():
    name = request.form.get("name", "").strip()
    if name and not Person.query.filter_by(name=name).first():
        db.session.add(Person(name=name))
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/remove_person", methods=["POST"])
def remove_person():
    name = request.form.get("name", "")
    person = Person.query.filter_by(name=name).first()
    if person:
        # Delete related participation and shares via cascade on expense, or explicit cleanup
        # Remove from participants for each expense
        for e in Expense.query.all():
            if person in e.participants:
                e.participants.remove(person)
            for s in list(e.shares):
                if s.person_id == person.id:
                    db.session.delete(s)
            # If payer is the person, delete the expense
            if e.payer_id == person.id:
                db.session.delete(e)
        db.session.delete(person)
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/add_expense", methods=["POST"])
def add_expense():
    desc = request.form.get("desc", "").strip() or "Expense"
    amount_raw = request.form.get("amount", "0").strip()
    payer_name = request.form.get("payer", "").strip()
    split_mode = request.form.get("split_mode", "equal")
    participant_names = request.form.getlist("participants")

    try:
        amount = Decimal(amount_raw)
    except:
        return redirect(url_for("index"))
    payer = Person.query.filter_by(name=payer_name).first()
    participants = Person.query.filter(Person.name.in_(participant_names)).all()
    if amount <= 0 or not payer or not participants:
        return redirect(url_for("index"))

    e = Expense(desc=desc, amount=amount, payer=payer)
    e.participants = participants
    db.session.add(e)
    db.session.flush()  # ensure e.id exists

    if split_mode == "custom":
        total = Decimal("0")
        shares = []
        for p in participants:
            val = request.form.get(f"share_{p.name}", "").strip()
            try:
                amt = Decimal(val)
            except:
                db.session.rollback()
                return redirect(url_for("index"))
            if amt < 0:
                db.session.rollback()
                return redirect(url_for("index"))
            shares.append(ExpenseShare(expense_id=e.id, person_id=p.id, amount=amt))
            total += amt
        if (total - amount).copy_abs() > Decimal("0.01"):
            db.session.rollback()
            return redirect(url_for("index"))
        for s in shares:
            db.session.add(s)

    db.session.commit()
    return redirect(url_for("index"))

@app.route("/remove_expense", methods=["POST"])
def remove_expense():
    idx_raw = request.form.get("idx", "")
    try:
        idx = int(idx_raw)
    except:
        return redirect(url_for("index"))
    # Map table row index to actual expense order
    expenses = Expense.query.order_by(Expense.id).all()
    if 0 <= idx < len(expenses):
        db.session.delete(expenses[idx])
        db.session.commit()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)