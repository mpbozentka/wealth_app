import streamlit as st
import pandas as pd
import plotly.express as px
from dataclasses import dataclass
from typing import Literal
import datetime

# ==========================================
# 1. THE BLUEPRINTS (Math Engine)
# ==========================================

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
        # 1. Grow the existing balance
        growth = self.balance * self.annual_growth_rate
        
        # 2. Increase the annual contribution (The "Raise")
        self.annual_contribution *= (1 + contribution_growth_rate)
        
        # 3. Add to balance
        self.balance += growth + self.annual_contribution
        return self.balance

@dataclass
class Liability:
    name: str
    balance: float
    annual_interest_rate: float
    monthly_payment: float
    category: str = "Debt"

    def pay_down_year(self):
        # We assume debt payments are fixed (like a 30-year mortgage) 
        # so we do NOT apply growth to the payment amount.
        for _ in range(12):
            if self.balance <= 0: break
            interest = self.balance * (self.annual_interest_rate / 12)
            self.balance += interest
            self.balance -= self.monthly_payment
        if self.balance < 0: self.balance = 0
        return self.balance

# ==========================================
# 2. STREAMLIT PAGE CONFIG & STATE MANAGEMENT
# ==========================================

st.set_page_config(page_title="FIRE Lifetime Planner", layout="wide")
st.title("🔥 Lifetime Wealth Forecaster")
st.markdown("Projection runs until **Age 85**.")

def reset_portfolio():
    st.session_state.portfolio = []
    st.rerun()

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

if st.session_state.portfolio and not isinstance(st.session_state.portfolio[0], dict):
    st.session_state.portfolio = []

# ==========================================
# 3. SIDEBAR: INPUTS
# ==========================================
with st.sidebar:
    st.header("1. Your Details")
    
    # --- AGE INPUT ---
    user_age = st.number_input("Current Age", 18, 84, 30)
    retirement_age = 59 
    
    # CALCULATE TIME HORIZON (Max Age 85)
    current_year_date = datetime.date.today().year
    years_to_project = 85 - user_age
    
    # Prevent negative range if user types 85+
    if years_to_project < 1: years_to_project = 1
    
    st.divider()
    st.header("2. Your Assets")
    
    with st.expander("➕ Add Asset / Debt", expanded=False):
        new_name = st.text_input("Name", placeholder="e.g. Taxable Brokerage")
        new_cat = st.selectbox("Category", ["Stock Market", "Cash", "Real Estate", "Crypto", "Debt/Liability"])
        
        c1, c2 = st.columns(2)
        new_balance = c1.number_input("Balance", 0.0, step=1000.0)
        new_monthly = c2.number_input("Monthly Add/Pay", 0.0, step=100.0)
        
        if new_cat == "Debt/Liability":
            new_rate = st.number_input("Interest Rate (%)", 0.0, value=5.0, step=0.1) / 100
            new_tax = "N/A"
            item_type = "liability"
        else:
            new_rate = st.number_input("Growth Rate (%)", -10.0, value=7.0, step=0.1) / 100
            new_tax = st.selectbox("Tax Type", ["Taxable", "Roth", "Pre-Tax"])
            item_type = "asset"

        if st.button("Add"):
            if new_name:
                st.session_state.portfolio.append({
                    "name": new_name, "balance": new_balance, "rate": new_rate,
                    "monthly": new_monthly, "tax": new_tax, "category": new_cat, "type": item_type
                })
                st.success(f"Added {new_name}")

    if st.session_state.portfolio:
        st.divider()
        st.subheader("Current Portfolio")
        for i, item in enumerate(st.session_state.portfolio):
            c1, c2 = st.columns([4,1])
            val = f"-${item['balance']:,.0f}" if item['type']=='liability' else f"${item['balance']:,.0f}"
            c1.caption(f"**{item['name']}** ({item['tax']}): {val}")
            if c2.button("x", key=f"d{i}"):
                st.session_state.portfolio.pop(i)
                st.rerun()

    st.header("3. Financial Goals")
    
    annual_spend = st.number_input("Net Annual Spending ($)", value=60000, step=1000, 
                                   help="The pure amount you need to live, excluding future taxes.")
    swr = st.slider("Safe Withdrawal Rate (%)", 3.0, 5.0, 4.0, 
                    help="The percentage of your portfolio you safely withdraw each year.") / 100
    
    st.subheader("Tax Assumptions")
    tax_pre_tax = st.slider("Pre-Tax Withdrawal Tax Rate (%)", 0, 50, 20) / 100
    tax_taxable = st.slider("Taxable Capital Gains Rate (%)", 0, 30, 15) / 100

    st.divider()
    st.subheader("Growth Assumptions")
    
    # --- NEW: CONTRIBUTION GROWTH ---
    contrib_growth = st.slider("Annual Contribution Increase (%)", 0.0, 10.0, 3.0, 
                               help="Simulates raises. If you put 3% here and Inflation is 2.5%, you are getting a 0.5% 'Real' raise each year.") / 100
    
    inflation_rate = st.slider("Inflation Assumption (%)", 0.0, 8.0, 2.5) / 100
    
    st.caption(f"Projecting {years_to_project} years (until age 85)")
    
    if st.button("Reset All"):
        reset_portfolio()

# ==========================================
# 4. CALCULATION & FI LOGIC
# ==========================================

if st.session_state.portfolio:
    
    sim_objects = []
    for p in st.session_state.portfolio:
        if p['type'] == 'asset':
            sim_objects.append(Asset(p['name'], p['balance'], p['monthly']*12, p['rate'], p['tax'], p['category']))
        else:
            sim_objects.append(Liability(p['name'], p['balance'], p['rate'], p['monthly']))
            
    data = []
    current_year = current_year_date
    fi_year_achieved = None
    
    fi_number = annual_spend / swr
    
    for year in range(years_to_project + 1):
        row = {"Year": current_year}
        total_taxable_swr_base = 0 
        total_assets_gross = 0      
        
        current_age = user_age + year
        can_access_retirement = current_age >= retirement_age 

        for item in sim_objects:
            if isinstance(item, Asset):
                if year > 0: 
                    # PASS THE GROWTH RATE (Dynamic Contribution)
                    item.project_year(contrib_growth)
                
                real_val = item.balance / ((1 + inflation_rate) ** year)
                
                tax_haircut = 0.0
                if item.tax_status == 'Pre-Tax':
                    tax_haircut = tax_pre_tax
                elif item.tax_status == 'Taxable':
                    tax_haircut = tax_taxable 

                liquid_value = real_val * (1 - tax_haircut)
                total_assets_gross += real_val 
                
                row[item.name] = real_val 
                
                if item.tax_status == 'Taxable' or item.tax_status == 'Roth' or item.category == 'Cash':
                    total_taxable_swr_base += liquid_value
                elif can_access_retirement:
                    total_taxable_swr_base += liquid_value

            elif isinstance(item, Liability):
                if year > 0: item.pay_down_year()
                real_val = item.balance / ((1 + inflation_rate) ** year)
                total_assets_gross += -real_val 
                row[item.name] = -real_val

        safe_annual_withdrawal = total_taxable_swr_base * swr
        
        row["Net Worth (Gross)"] = total_assets_gross
        row["Passive Income (Net)"] = safe_annual_withdrawal
        row["Annual Spending (Net)"] = annual_spend 
        
        if safe_annual_withdrawal >= annual_spend and fi_year_achieved is None:
            fi_year_achieved = current_year
            
        data.append(row)
        current_year += 1
        
    df = pd.DataFrame(data)

    # ==========================================
    # 5. VISUALIZATION
    # ==========================================
    
    st.subheader("🏁 Independence Dashboard")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Net FI Number", f"${fi_number:,.0f}", help="The post-tax portfolio size needed to support your NET spending.")
    
    if fi_year_achieved:
        years_left = fi_year_achieved - current_year_date
        c2.metric("🎉 Freedom Date", f"{fi_year_achieved}", delta=f"In {years_left} Years")
        st.balloons() if years_left == 0 else None
    else:
        c2.metric("Freedom Date", "Not in range", delta="Increase contributions")
        
    current_passive = df.iloc[0]["Passive Income (Net)"] / 12
    c3.metric("Current Safe Monthly Income (Net)", f"${current_passive:,.0f}")

    # --- CHART 1: CROSSOVER ---
    # --- CHART 1: CROSSOVER ---
    st.subheader("The Crossover Point: When you can safely retire")
    
    # 1. Add a Toggle to switch views
    zoom_view = st.toggle("🔍 Zoom in on Crossover Point", value=True, 
                          help="Limits the vertical axis to 3x your spending goal so you can see the intersection clearly.")
    
    fig_fi = px.line(df, x="Year", y=["Passive Income (Net)", "Annual Spending (Net)"], 
                     title="Net Income vs. Net Expenses",
                     color_discrete_map={"Annual Spending (Net)": "red", "Passive Income (Net)": "green"})
    
    # 2. Dynamic Axis Scaling
    if zoom_view:
        # Cap the Y-axis at 3x the annual spending to make the cross-over visible
        fig_fi.update_layout(yaxis_range=[0, annual_spend * 3])
    else:
        # Let it auto-scale to show the massive future wealth
        fig_fi.update_layout(yaxis_range=None)

    # Legend Fix (Bottom Center)
    fig_fi.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    ))
    
    st.plotly_chart(fig_fi, use_container_width=True)
    
    # Legend Fix for Chart 1
    fig_fi.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3, # Push it below the x-axis
        xanchor="center",
        x=0.5
    ))
    
    st.plotly_chart(fig_fi, use_container_width=True)

    # --- CHART 2: STACKED AREA ---
    st.subheader("Gross Portfolio Composition (Real $)")
    asset_cols = [c for c in df.columns if c not in ["Year", "Net Worth (Gross)", "Passive Income (Net)", "Annual Spending (Net)"]]
    chart_data = df.melt('Year', value_vars=asset_cols, var_name='Asset', value_name='Value')
    
    fig_stack = px.area(chart_data, x="Year", y="Value", color="Asset", 
                        title="Net Worth Composition (Adjusted for Inflation, Before Tax Haircut)", 
                        labels={"Value":"Value ($)"})
    
    # Legend Fix for Chart 2
    fig_stack.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3, # Push it below the x-axis
        xanchor="center",
        x=0.5
    ))

    st.plotly_chart(fig_stack, use_container_width=True)

    with st.expander("See Raw Data"):
        st.dataframe(df.style.format("${:,.0f}"))

else:
    st.info("👈 Please enter your age and add assets to begin.")