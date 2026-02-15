from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
import os

# Database setup
DATABASE_URL = "sqlite:///./instance/app.db"
os.makedirs("instance", exist_ok=True)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Association table for many-to-many relationship
expense_participant = Table(
    "expense_participant",
    Base.metadata,
    Column("expense_id", Integer, ForeignKey("expense.id"), primary_key=True),
    Column("person_id", Integer, ForeignKey("person.id"), primary_key=True)
)

# Models
class Person(Base):
    __tablename__ = "person"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    paid_expenses = relationship("Expense", back_populates="payer")
    participated_expenses = relationship("Expense", secondary=expense_participant, back_populates="participants")

class Expense(Base):
    __tablename__ = "expense"
    id = Column(Integer, primary_key=True)
    desc = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payer_id = Column(Integer, ForeignKey("person.id"), nullable=False)
    payer = relationship("Person", back_populates="paid_expenses")
    participants = relationship("Person", secondary=expense_participant, back_populates="participated_expenses")
    shares = relationship("ExpenseShare", cascade="all, delete-orphan", back_populates="expense")

class ExpenseShare(Base):
    __tablename__ = "expense_share"
    id = Column(Integer, primary_key=True)
    expense_id = Column(Integer, ForeignKey("expense.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("person.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    expense = relationship("Expense", back_populates="shares")

# Create tables
Base.metadata.create_all(bind=engine)

def recompute(db: Session):
    # Compute balances and settlement suggestions from DB
    people = db.query(Person).order_by(Person.name).all()
    balances = {p.name: Decimal("0.00") for p in people}
    expenses = db.query(Expense).order_by(Expense.id).all()

    for e in expenses:
        amount = Decimal(str(e.amount))
        payer = e.payer.name
        participants = [p.name for p in e.participants]
        if not participants:
            continue
        balances[payer] += amount
        if e.shares:
            for s in e.shares:
                person = db.query(Person).filter(Person.id == s.person_id).first()
                if person:
                    balances[person.name] -= Decimal(str(s.amount))
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

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    db = SessionLocal()
    try:
        people, expenses, balances, settlements = recompute(db)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "people": [p.name for p in people],
                "expenses": [{
                    "desc": e.desc,
                    "amount": float(e.amount),
                    "payer": e.payer.name,
                    "participants": [p.name for p in e.participants],
                    "shares": {db.query(Person).filter(Person.id == s.person_id).first().name: float(s.amount) for s in e.shares}
                } for e in expenses],
                "balances": balances,
                "settlements": settlements
            }
        )
    finally:
        db.close()

@app.post("/add_person")
def add_person(name: str = Form("")):
    db = SessionLocal()
    try:
        name = name.strip()
        if name and not db.query(Person).filter_by(name=name).first():
            db.add(Person(name=name))
            db.commit()
        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()

@app.post("/remove_person")
def remove_person(name: str = Form("")):
    db = SessionLocal()
    try:
        person = db.query(Person).filter_by(name=name).first()
        if person:
            # Delete related participation and shares via cascade on expense, or explicit cleanup
            # Remove from participants for each expense
            for e in db.query(Expense).all():
                if person in e.participants:
                    e.participants.remove(person)
                for s in list(e.shares):
                    if s.person_id == person.id:
                        db.delete(s)
                # If payer is the person, delete the expense
                if e.payer_id == person.id:
                    db.delete(e)
            db.delete(person)
            db.commit()
        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()

@app.post("/add_expense")
async def add_expense(
    request: Request,
    desc: str = Form(""),
    amount: str = Form("0"),
    payer: str = Form(""),
    split_mode: str = Form("equal")
):
    db = SessionLocal()
    try:
        form_data = await request.form()
        participant_names = form_data.getlist("participants")
        
        desc = desc.strip() or "Expense"
        payer_name = payer.strip()
        amount_raw = amount.strip()

        try:
            amount_decimal = Decimal(amount_raw)
        except:
            return RedirectResponse(url="/", status_code=303)
        
        payer_obj = db.query(Person).filter_by(name=payer_name).first()
        participants = db.query(Person).filter(Person.name.in_(participant_names)).all()
        
        if amount_decimal <= 0 or not payer_obj or not participants:
            return RedirectResponse(url="/", status_code=303)

        e = Expense(desc=desc, amount=amount_decimal, payer=payer_obj)
        e.participants = participants
        db.add(e)
        db.flush()  # ensure e.id exists

        if split_mode == "custom":
            total = Decimal("0")
            shares = []
            for p in participants:
                val = form_data.get(f"share_{p.name}", "").strip()
                try:
                    amt = Decimal(val)
                except:
                    db.rollback()
                    return RedirectResponse(url="/", status_code=303)
                if amt < 0:
                    db.rollback()
                    return RedirectResponse(url="/", status_code=303)
                shares.append(ExpenseShare(expense_id=e.id, person_id=p.id, amount=amt))
                total += amt
            if (total - amount_decimal).copy_abs() > Decimal("0.01"):
                db.rollback()
                return RedirectResponse(url="/", status_code=303)
            for s in shares:
                db.add(s)

        db.commit()
        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()

@app.post("/remove_expense")
def remove_expense(idx: str = Form("")):
    db = SessionLocal()
    try:
        try:
            idx_int = int(idx)
        except:
            return RedirectResponse(url="/", status_code=303)
        # Map table row index to actual expense order
        expenses = db.query(Expense).order_by(Expense.id).all()
        if 0 <= idx_int < len(expenses):
            db.delete(expenses[idx_int])
            db.commit()
        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)