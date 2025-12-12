from dataclasses import dataclass
from typing import Literal

TaxType = Literal['Roth', 'Pre-Tax', 'Taxable', 'N/A']

@dataclass
class Asset:
    name: str
    balance: float
    annual_contribution: float
    annual_growth_rate: float
    tax_status: TaxType
    category: str 

    def project_year(self, contribution_growth_rate):
        growth = self.balance * self.annual_growth_rate
        self.annual_contribution *= (1 + contribution_growth_rate)
        self.balance += growth + self.annual_contribution
    
    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            return amount
        else:
            actual = self.balance
            self.balance = 0
            return actual

@dataclass
class Liability:
    name: str
    balance: float
    annual_interest_rate: float
    monthly_payment: float
    category: str = "Debt"

    def pay_down_year(self):
        for _ in range(12):
            if self.balance <= 0: break
            interest = self.balance * (self.annual_interest_rate / 12)
            self.balance += interest
            self.balance -= self.monthly_payment
        if self.balance < 0: self.balance = 0
