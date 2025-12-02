# python
import tkinter as tk
from tkinter import ttk, messagebox


class MoneySplitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Community Money Split")
        self.geometry("900x600")
        self.minsize(900, 600)

        # Data
        self.people = []  # list[str]
        # expense: {desc, amount, payer, participants, shares(optional dict[name]->amount)}
        self.expenses = []
        self.balances = {}  # name -> float

        # UI state for participants
        self.participant_vars = {}      # name -> tk.BooleanVar (included)
        self.share_entries = {}         # name -> ttk.Entry (custom amount input)
        self.split_mode = tk.StringVar(value="equal")  # "equal" or "custom"

        # UI
        self._build_ui()
        self._refresh_all()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=10)
        root.grid(sticky="nsew")
        for i in range(3):
            root.columnconfigure(i, weight=1)
        for i in range(3):
            root.rowconfigure(i, weight=1)

        # People section
        people_frame = ttk.LabelFrame(root, text="Participants")
        people_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        people_frame.columnconfigure(0, weight=1)

        self.person_entry = ttk.Entry(people_frame)
        self.person_entry.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Button(people_frame, text="Add Person", command=self.add_person).grid(row=0, column=1, padx=5, pady=5)

        self.people_list = tk.Listbox(people_frame, height=10)
        self.people_list.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        ttk.Button(people_frame, text="Remove Selected", command=self.remove_selected_person).grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        # Expense section
        expense_frame = ttk.LabelFrame(root, text="Add Expense")
        expense_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        for i in range(2):
            expense_frame.columnconfigure(i, weight=1)

        ttk.Label(expense_frame, text="Description").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.exp_desc = ttk.Entry(expense_frame)
        self.exp_desc.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(expense_frame, text="Amount").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.exp_amount = ttk.Entry(expense_frame)
        self.exp_amount.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(expense_frame, text="Payer").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.exp_payer = ttk.Combobox(expense_frame, state="readonly", values=self.people)
        self.exp_payer.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        # Split mode
        ttk.Label(expense_frame, text="Split Mode").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        split_mode_frame = ttk.Frame(expense_frame)
        split_mode_frame.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        ttk.Radiobutton(split_mode_frame, text="Equal", value="equal", variable=self.split_mode, command=self._toggle_split_mode).grid(row=0, column=0, padx=2)
        ttk.Radiobutton(split_mode_frame, text="Custom amounts", value="custom", variable=self.split_mode, command=self._toggle_split_mode).grid(row=0, column=1, padx=2)

        # Participants with optional custom shares
        ttk.Label(expense_frame, text="Participants").grid(row=4, column=0, sticky="nw", padx=5, pady=2)
        self.participants_frame = ttk.Frame(expense_frame)
        self.participants_frame.grid(row=4, column=1, sticky="nsew", padx=5, pady=2)
        self.participants_frame.columnconfigure(1, weight=1)

        ttk.Button(expense_frame, text="Add Expense", command=self.add_expense).grid(row=5, column=0, columnspan=2, padx=5, pady=8)

        # Expenses list
        list_frame = ttk.LabelFrame(root, text="Expenses")
        list_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.expenses_list = tk.Listbox(list_frame)
        self.expenses_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Button(list_frame, text="Remove Selected", command=self.remove_selected_expense).grid(row=1, column=0, padx=5, pady=5)

        # Balances
        balance_frame = ttk.LabelFrame(root, text="Balances")
        balance_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        balance_frame.columnconfigure(0, weight=1)
        balance_frame.rowconfigure(0, weight=1)

        self.balance_text = tk.Text(balance_frame, height=8)
        self.balance_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.balance_text.configure(state="disabled")

        # Settlement suggestions
        settle_frame = ttk.LabelFrame(root, text="Suggested Settlements")
        settle_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        settle_frame.columnconfigure(0, weight=1)
        settle_frame.rowconfigure(0, weight=1)

        self.settle_text = tk.Text(settle_frame, height=8)
        self.settle_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.settle_text.configure(state="disabled")

    def add_person(self):
        name = self.person_entry.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Enter a name.")
            return
        if name in self.people:
            messagebox.showwarning("Validation", "Name already exists.")
            return
        self.people.append(name)
        self.person_entry.delete(0, tk.END)
        self._refresh_people_ui()

    def remove_selected_person(self):
        sel = self.people_list.curselection()
        if not sel:
            return
        name = self.people_list.get(sel[0])
        # Remove from people
        self.people = [p for p in self.people if p != name]
        # Remove from expenses participants or payer
        new_expenses = []
        for e in self.expenses:
            if e["payer"] == name:
                # Skip/remove expenses where the removed person was payer
                continue
            e["participants"] = [p for p in e["participants"] if p != name]
            if "shares" in e:
                e["shares"] = {p: amt for p, amt in e["shares"].items() if p != name}
                if sum(e["shares"].values()) <= 0:
                    continue
            if e["participants"]:
                new_expenses.append(e)
        self.expenses = new_expenses
        self._refresh_all()

    def _toggle_split_mode(self):
        # Enable/disable share entry fields based on mode
        is_custom = self.split_mode.get() == "custom"
        for name, entry in self.share_entries.items():
            state = "normal" if is_custom else "disabled"
            entry.configure(state=state)

    def _refresh_people_ui(self):
        # Update people listbox
        self.people_list.delete(0, tk.END)
        for p in self.people:
            self.people_list.insert(tk.END, p)
        # Update payer combobox
        self.exp_payer["values"] = self.people
        if self.people:
            current = self.exp_payer.get()
            if current not in self.people:
                self.exp_payer.set(self.people[0])
        else:
            self.exp_payer.set("")
        # Rebuild participant controls
        for w in self.participants_frame.winfo_children():
            w.destroy()
        self.participant_vars.clear()
        self.share_entries.clear()

        # Header row
        ttk.Label(self.participants_frame, text="Include").grid(row=0, column=0, sticky="w", padx=2)
        ttk.Label(self.participants_frame, text="Name").grid(row=0, column=1, sticky="w", padx=2)
        ttk.Label(self.participants_frame, text="Custom amount").grid(row=0, column=2, sticky="w", padx=2)

        for i, p in enumerate(self.people, start=1):
            var = tk.BooleanVar(value=True)
            self.participant_vars[p] = var
            cb = ttk.Checkbutton(self.participants_frame, variable=var)
            cb.grid(row=i, column=0, sticky="w", padx=2, pady=2)
            ttk.Label(self.participants_frame, text=p).grid(row=i, column=1, sticky="w", padx=2, pady=2)
            entry = ttk.Entry(self.participants_frame, width=12, state=("normal" if self.split_mode.get() == "custom" else "disabled"))
            entry.grid(row=i, column=2, sticky="w", padx=2, pady=2)
            self.share_entries[p] = entry

        self._recompute()

    def add_expense(self):
        desc = self.exp_desc.get().strip() or "Expense"
        try:
            amount = float(self.exp_amount.get().strip())
        except ValueError:
            messagebox.showwarning("Validation", "Enter a valid amount.")
            return
        if amount <= 0:
            messagebox.showwarning("Validation", "Amount must be positive.")
            return
        payer = self.exp_payer.get().strip()
        if payer not in self.people:
            messagebox.showwarning("Validation", "Select a valid payer.")
            return
        participants = [p for p, v in self.participant_vars.items() if v.get()]
        if not participants:
            messagebox.showwarning("Validation", "Select at least one participant.")
            return

        expense = {
            "desc": desc,
            "amount": amount,
            "payer": payer,
            "participants": participants,
        }

        if self.split_mode.get() == "custom":
            shares = {}
            for p in participants:
                val = self.share_entries[p].get().strip()
                if not val:
                    messagebox.showwarning("Validation", f"Enter custom amount for {p}.")
                    return
                try:
                    amt = float(val)
                except ValueError:
                    messagebox.showwarning("Validation", f"Invalid amount for {p}.")
                    return
                if amt < 0:
                    messagebox.showwarning("Validation", f"Amount for {p} must be non-negative.")
                    return
                shares[p] = amt
            total_shares = round(sum(shares.values()), 2)
            if abs(total_shares - amount) > 0.01:
                messagebox.showwarning("Validation", f"Custom shares must sum to ₹{amount:.2f}. Current sum: ₹{total_shares:.2f}")
                return
            expense["shares"] = shares

        self.expenses.append(expense)

        # Clear form
        self.exp_desc.delete(0, tk.END)
        self.exp_amount.delete(0, tk.END)
        for p in self.share_entries:
            self.share_entries[p].delete(0, tk.END)
        self._refresh_all()

    def remove_selected_expense(self):
        sel = self.expenses_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self.expenses):
            del self.expenses[idx]
        self._refresh_all()

    def _refresh_expenses_list(self):
        self.expenses_list.delete(0, tk.END)
        for e in self.expenses:
            participants_str = ", ".join(e["participants"])
            if "shares" in e:
                shares_str = ", ".join(f"{p}:{amt:.2f}" for p, amt in e["shares"].items())
                self.expenses_list.insert(
                    tk.END,
                    f'{e["desc"]} | ₹{e["amount"]:.2f} | Payer: {e["payer"]} | Custom split: {shares_str}'
                )
            else:
                self.expenses_list.insert(
                    tk.END,
                    f'{e["desc"]} | ₹{e["amount"]:.2f} | Payer: {e["payer"]} | Split: {participants_str} (equal)'
                )

    def _recompute(self):
        self.balances = {p: 0.0 for p in self.people}
        for e in self.expenses:
            amount = e["amount"]
            payer = e["payer"]
            participants = e["participants"]
            if not participants:
                continue
            # Payer paid amount
            if payer in self.balances:
                self.balances[payer] += amount

            if "shares" in e:
                # Custom amounts per participant
                for p in participants:
                    share_amt = e["shares"].get(p, 0.0)
                    if p in self.balances:
                        self.balances[p] -= share_amt
            else:
                # Equal split
                share = amount / len(participants)
                for p in participants:
                    if p in self.balances:
                        self.balances[p] -= share

        for k in self.balances:
            self.balances[k] = round(self.balances[k], 2)

        self._compute_settlements()
        self._update_balance_text()

    def _update_balance_text(self):
        self.balance_text.configure(state="normal")
        self.balance_text.delete("1.0", tk.END)
        if not self.people:
            self.balance_text.insert(tk.END, "No participants yet.")
        else:
            for p in self.people:
                bal = self.balances.get(p, 0.0)
                status = "owes" if bal < 0 else "is owed"
                self.balance_text.insert(tk.END, f"{p}: {status} ₹{abs(bal):.2f}\n")
        self.balance_text.configure(state="disabled")

    def _compute_settlements(self):
        creditors = []
        debtors = []
        for p, bal in self.balances.items():
            if bal > 0:
                creditors.append([p, bal])
            elif bal < 0:
                debtors.append([p, -bal])

        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)

        settlements = []
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            d_name, d_amt = debtors[i]
            c_name, c_amt = creditors[j]
            pay = min(d_amt, c_amt)
            settlements.append(f"{d_name} -> {c_name}: ₹{pay:.2f}")
            d_amt -= pay
            c_amt -= pay
            if abs(d_amt) < 1e-9:
                i += 1
            else:
                debtors[i][1] = d_amt
            if abs(c_amt) < 1e-9:
                j += 1
            else:
                creditors[j][1] = c_amt

        self.settle_text.configure(state="normal")
        self.settle_text.delete("1.0", tk.END)
        if settlements:
            self.settle_text.insert(tk.END, "\n".join(settlements))
        else:
            self.settle_text.insert(tk.END, "No settlements needed.")
        self.settle_text.configure(state="disabled")

    def _refresh_all(self):
        self._refresh_people_ui()
        self._refresh_expenses_list()


if __name__ == "__main__":
    app = MoneySplitApp()
    app.mainloop()