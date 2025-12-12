import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import Literal
import datetime
import copy

# ==========================================
# 1. HELPER FUNCTIONS & TAX LOGIC
# ==========================================

def calculate_progressive_tax(income, filing_status="Single"):
    """Simplified 2024 IRS Tax Brackets approximation."""
    if income <= 0: return 0
    std_deduction = 14600 if filing_status == "Single" else 29200
    taxable_income = max(0, income - std_deduction)
    
    if filing_status == "Single":
        brackets = [(0.10, 11600), (0.12, 47150), (0.22, 100525), (0.24, 191950), (0.32, 243725), (0.35, 609350)]
    else:
        brackets = [(0.10, 23200), (0.12, 94300), (0.22, 201050), (0.24, 383900), (0.32, 487450), (0.35, 731200)]
        
    tax = 0
    previous_limit = 0
    for rate, limit in brackets:
        if taxable_income > limit:
            tax += (limit - previous_limit) * rate
            previous_limit = limit
        else:
            tax += (taxable_income - previous_limit) * rate
            return tax
    tax += (taxable_income - previous_limit) * 0.37
    return tax

# ==========================================
# 2. THE BLUEPRINTS
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

# ==========================================
# 3. PAGE CONFIG & STATE
# ==========================================
st.set_page_config(page_title="Professional Wealth Planner", layout="wide")
st.title("🔥 Professional Wealth Planner")

if 'portfolio' not in st.session_state: st.session_state.portfolio = []
if 'life_events' not in st.session_state: st.session_state.life_events = []
if 'baseline_scenario' not in st.session_state: st.session_state.baseline_scenario = None

if st.session_state.portfolio and not isinstance(st.session_state.portfolio[0], dict):
    st.session_state.portfolio = []

def reset_portfolio():
    st.session_state.portfolio = []
    st.session_state.life_events = []
    st.session_state.baseline_scenario = None
    st.rerun()

# ==========================================
# 4. SIDEBAR INPUTS
# ==========================================
with st.sidebar:
    st.header("A/B Testing")
    c_base, c_reset = st.columns(2)
    if c_base.button("📸 Snap Baseline", help="Save current settings to compare against changes."):
        st.session_state.trigger_baseline = True 
    if c_reset.button("Reset All"):
        reset_portfolio()
    st.divider()

    st.header("1. Personal Details")
    user_age = st.number_input("Current Age", 18, 84, 30)
    filing_status = st.selectbox("Tax Filing Status", ["Single", "Married (Joint)"])
    retirement_age = 59 
    current_year_date = datetime.date.today().year
    
    # --- NEW: TIMEFRAME SELECTION ---
    st.subheader("Timeframe")
    timeframe_options = {
        "5 Years": 5, "10 Years": 10, "15 Years": 15, 
        "20 Years": 20, "25 Years": 25, "30 Years": 30, 
        "Until Age 85": 85 - user_age
    }
    selected_timeframe = st.selectbox("View Forecast Until", list(timeframe_options.keys()), index=6)
    
    years_to_project = timeframe_options[selected_timeframe]
    if years_to_project < 1: years_to_project = 1
    
    st.divider()
    
    # --- ASSETS ---
    st.header("2. Assets & Liabilities")
    with st.expander("➕ Add Asset / Debt", expanded=False):
        new_name = st.text_input("Name", placeholder="e.g. 401k")
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
        for i, item in enumerate(st.session_state.portfolio):
            c1, c2 = st.columns([4,1])
            val = f"-${item['balance']:,.0f}" if item['type']=='liability' else f"${item['balance']:,.0f}"
            c1.caption(f"**{item['name']}** ({item['tax']}): {val}")
            if c2.button("x", key=f"d{i}"):
                st.session_state.portfolio.pop(i)
                st.rerun()
    st.divider()

    st.header("3. Life Events")
    with st.expander("➕ Add Event", expanded=False):
        ev_name = st.text_input("Event Name", placeholder="e.g. Down Payment")
        # Ensure event age is within the full 85 year range
        max_age_event = 85
        ev_age = st.number_input("Age when event occurs", user_age + 1, max_age_event, user_age + 5)
        ev_cost = st.number_input("Cost ($ Today's Value)", 0.0, step=5000.0)
        if st.button("Add Event"):
            st.session_state.life_events.append({"name": ev_name, "age": ev_age, "cost": ev_cost})
    if st.session_state.life_events:
        for i, ev in enumerate(st.session_state.life_events):
            c1, c2 = st.columns([4,1])
            c1.caption(f"**{ev['name']}** @ Age {ev['age']}: ${ev['cost']:,.0f}")
            if c2.button("x", key=f"ev{i}"):
                st.session_state.life_events.pop(i)
                st.rerun()
    st.divider()

    st.header("4. Forecast Settings")
    annual_spend = st.number_input("Desired Annual Spending ($)", value=60000, step=1000)
    swr = st.slider("Safe Withdrawal Rate (%)", 3.0, 5.0, 4.0) / 100
    st.subheader("Advanced Assumptions")
    use_progressive = st.toggle("Use Progressive Tax Brackets", value=True)
    if not use_progressive:
        tax_flat_rate = st.slider("Flat Tax Rate Estimate (%)", 0, 40, 15) / 100
    contrib_growth = st.slider("Annual Contribution Increase (%)", 0.0, 10.0, 3.0) / 100
    inflation_rate = st.slider("Inflation (%)", 0.0, 8.0, 2.5) / 100

# ==========================================
# 5. SIMULATION ENGINE
# ==========================================
def run_simulation(portfolio_data, life_events_data, total_years_to_project):
    # Use a DEEP COPY to prevent the simulation from changing the sidebar inputs' original values
    sim_objects = []
    for p in portfolio_data:
        if p['type'] == 'asset':
            sim_objects.append(Asset(p['name'], p['balance'], p['monthly']*12, p['rate'], p['tax'], p['category']))
        else:
            sim_objects.append(Liability(p['name'], p['balance'], p['rate'], p['monthly']))
            
    data = []
    current_year = current_year_date
    
    # We must run the full simulation until age 85 internally 
    # to account for Life Events occurring later than the selected time frame.
    max_projection_years = 85 - user_age
    
    for year in range(max_projection_years + 1):
        current_age = user_age + year
        row = {"Year": current_year, "Age": current_age}
        
        # --- A. LIFE EVENTS ---
        for ev in life_events_data:
            if ev['age'] == current_age:
                future_cost = ev['cost'] * ((1 + inflation_rate) ** year)
                remaining_cost = future_cost
                for tax_type in [['Cash', 'Taxable'], ['Roth'], ['Pre-Tax']]:
                    for item in sim_objects:
                        if isinstance(item, Asset) and remaining_cost > 0:
                            is_cash = (tax_type == ['Cash', 'Taxable'] and item.category == 'Cash')
                            is_tax_match = (item.tax_status in tax_type)
                            if is_cash or is_tax_match:
                                remaining_cost -= item.withdraw(remaining_cost)

        # --- B. ANNUAL SIMULATION ---
        total_assets_gross = 0
        gross_swr_base = 0
        can_access_retirement = current_age >= retirement_age

        for item in sim_objects:
            if isinstance(item, Asset):
                if year > 0: item.project_year(contrib_growth)
                real_val = item.balance / ((1 + inflation_rate) ** year)
                total_assets_gross += real_val
                row[item.name] = real_val
                
                if (item.tax_status in ['Taxable', 'Roth', 'Cash']) or can_access_retirement:
                    gross_swr_base += real_val
            elif isinstance(item, Liability):
                if year > 0: item.pay_down_year()
                real_val = item.balance / ((1 + inflation_rate) ** year)
                total_assets_gross += -real_val
                row[item.name] = -real_val

        # --- C. TAX & INCOME CALCULATION ---
        gross_passive_income = gross_swr_base * swr
        
        if use_progressive:
            estimated_tax = calculate_progressive_tax(gross_passive_income, filing_status)
            net_passive_income = gross_passive_income - estimated_tax
        else:
            net_passive_income = gross_passive_income * (1 - tax_flat_rate)

        # --- D. ATTRIBUTE INCOME TO ASSETS ---
        if gross_swr_base > 0:
             for item in sim_objects:
                 income_col_name = f"{item.name} Income"
                 if isinstance(item, Asset) and ((item.tax_status in ['Taxable', 'Roth', 'Cash']) or can_access_retirement):
                     share = row.get(item.name, 0) / gross_swr_base
                     row[income_col_name] = net_passive_income * share
                 else:
                     row[income_col_name] = 0
        else:
             for item in sim_objects:
                 if isinstance(item, Asset): row[f"{item.name} Income"] = 0

        row["Net Worth"] = total_assets_gross
        row["Passive Income"] = net_passive_income
        row["Annual Spending"] = annual_spend
        data.append(row)
        
        current_year += 1
        
    return pd.DataFrame(data)

# EXECUTE
if st.session_state.portfolio:
    df_full = run_simulation(st.session_state.portfolio, st.session_state.life_events, years_to_project)
    
    # Filter for the selected timeframe
    df_current = df_full.head(years_to_project + 1)
    
    if getattr(st.session_state, 'trigger_baseline', False):
        st.session_state.baseline_scenario = df_full.copy()
        st.session_state.trigger_baseline = False
        st.success("Baseline Snapshot Saved!")
    df_baseline = st.session_state.baseline_scenario.head(years_to_project + 1) if st.session_state.baseline_scenario is not None else None

    # Get data for the final year summary
    final_year_data = df_current.iloc[-1]
    
    # ==========================================
    # 6. VISUALIZATION
    # ==========================================
    
    st.subheader("🏁 Financial Independence Dashboard")
    
    # Metrics
    crossover_rows = df_current[df_current["Passive Income"] >= df_current["Annual Spending"]]
    freedom_year = crossover_rows.iloc[0]["Year"] if not crossover_rows.empty else None
    
    base_freedom_year = None
    if df_baseline is not None:
        base_rows = df_baseline[df_baseline["Passive Income"] >= df_baseline["Annual Spending"]]
        base_freedom_year = base_rows.iloc[0]["Year"] if not base_rows.empty else None

    c1, c2, c3 = st.columns(3)
    curr_nw = df_current.iloc[0]["Net Worth"]
    c1.metric("Current Net Worth", f"${curr_nw:,.0f}")
    
    if freedom_year:
        delta_msg = None
        if base_freedom_year:
            diff = base_freedom_year - freedom_year
            if diff > 0: delta_msg = f"{diff} Years Sooner than Baseline"
            elif diff < 0: delta_msg = f"{abs(diff)} Years Later than Baseline"
            else: delta_msg = "Same as Baseline"
        c2.metric("🎉 Freedom Date", f"{freedom_year}", delta=delta_msg)
    else:
        c2.metric("Freedom Date", "Not in range")

    monthly_income = df_current.iloc[0]["Passive Income"] / 12
    c3.metric("Safe Monthly Income (Net)", f"${monthly_income:,.0f}")

    # --- CHART 1: INCOME STACKED AREA ---
    st.subheader("Income Sources vs. Spending Requirement")
    
    col_zoom, col_log = st.columns([1,12])
    zoom = col_zoom.toggle("🔍 Zoom", value=True, key="zoom_toggle")
    log_scale_inc = col_log.toggle("Log Scale Y-Axis", value=False, key="log_inc_toggle")

    income_cols = [c for c in df_current.columns if c.endswith(" Income") and c != "Passive Income"]
    
    fig_inc = go.Figure()
    for col in income_cols:
        asset_name = col.replace(" Income", "")
        fig_inc.add_trace(go.Scatter(x=df_current['Year'], y=df_current[col], mode='lines', stackgroup='one', name=asset_name))
        
    fig_inc.add_trace(go.Scatter(x=df_current['Year'], y=df_current['Annual Spending'], 
                             mode='lines', name='Required Spending', line=dict(color='red', width=3)))

    if df_baseline is not None:
         fig_inc.add_trace(go.Scatter(x=df_baseline['Year'], y=df_baseline['Passive Income'], 
                                 mode='lines', name='Baseline Total Income', line=dict(color='gray', dash='dash')))

    if zoom:
        fig_inc.update_layout(yaxis_range=[0, annual_spend * 3])
    
    if log_scale_inc:
        fig_inc.update_yaxes(type="log", title="Net Annual Income (Log Scale $)")
    else:
         fig_inc.update_yaxes(type="linear", title="Net Annual Income ($)")


    fig_inc.update_layout(
        title=f"Net Passive Income Breakdown (Real $) - Forecast to {final_year_data['Year']}",
        xaxis_title="Year",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        hovermode="x unified"
    )
    st.plotly_chart(fig_inc, use_container_width=True, key="income_stack_chart")
    
    # --- RESULTS 1: INCOME SUMMARY ---
    with st.expander(f"Income Summary for {final_year_data['Year']}"):
        st.subheader(f"Projected Net Annual Income: ${final_year_data['Passive Income']:,.0f}")
        st.caption(f"Spending Requirement: ${final_year_data['Annual Spending']:,.0f}")
        
        income_summary = {}
        for col in income_cols:
            income_summary[col.replace(" Income", "")] = final_year_data[col]
            
        df_inc_summary = pd.DataFrame(list(income_summary.items()), columns=['Asset', 'Projected Net Income'])
        df_inc_summary = df_inc_summary[df_inc_summary['Projected Net Income'] > 0].sort_values(by='Projected Net Income', ascending=False)
        st.dataframe(df_inc_summary.style.format({"Projected Net Income": "${:,.0f}"}), use_container_width=True, hide_index=True)


    # --- CHART 2: NET WORTH STACKED AREA ---
    st.subheader("Net Worth Composition")

    col_log_nw, col_gap = st.columns([1,12])
    log_scale_nw = col_log_nw.toggle("Log Scale Y-Axis", value=False, key="log_nw_toggle")

    excluded_cols = ['Year', 'Age', 'Net Worth', 'Passive Income', 'Annual Spending']
    balance_cols = [c for c in df_current.columns if c not in excluded_cols and not c.endswith(" Income")]
    
    fig_nw_stack = go.Figure()
    for col in balance_cols:
        fig_nw_stack.add_trace(go.Scatter(x=df_current['Year'], y=df_current[col], mode='lines', stackgroup='one', name=col))

    if df_baseline is not None:
         fig_nw_stack.add_trace(go.Scatter(x=df_baseline['Year'], y=df_baseline['Net Worth'], 
                                name='Baseline Total NW', line=dict(color='gray', dash='dash')))

    if log_scale_nw:
        fig_nw_stack.update_yaxes(type="log", title="Net Worth (Log Scale $)")
    else:
         fig_nw_stack.update_yaxes(type="linear", title="Net Worth ($)")
         
    fig_nw_stack.update_layout(
        title=f"Asset Balance Breakdown (Real $) - Forecast to {final_year_data['Year']}",
        xaxis_title="Year",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        hovermode="x unified"
    )
    st.plotly_chart(fig_nw_stack, use_container_width=True, key="nw_stack_chart")
    
    # --- RESULTS 2: NET WORTH SUMMARY ---
    with st.expander(f"Net Worth Summary for {final_year_data['Year']}"):
        st.subheader(f"Projected Total Net Worth: ${final_year_data['Net Worth']:,.0f}")
        
        nw_summary = {}
        for col in balance_cols:
            nw_summary[col] = final_year_data[col]
            
        df_nw_summary = pd.DataFrame(list(nw_summary.items()), columns=['Asset', 'Projected Balance'])
        df_nw_summary = df_nw_summary[df_nw_summary['Projected Balance'].abs() > 0].sort_values(by='Projected Balance', ascending=False)
        st.dataframe(df_nw_summary.style.format({"Projected Balance": "${:,.0f}"}), use_container_width=True, hide_index=True)

else:
    st.info("👈 Please add assets in the sidebar to begin.")