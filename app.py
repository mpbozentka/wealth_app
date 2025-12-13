import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import copy
from logic import run_simulation
from ui import render_asset_card, render_liability_card, render_event_card
from storage import load_data, save_data

# ==========================================
# 1. PAGE CONFIG & STATE
# ==========================================
st.set_page_config(page_title="Professional Wealth Planner", layout="wide")
st.title("🔥 Professional Wealth Planner")

# Load Data on Startup
if 'data_loaded' not in st.session_state:
    saved_data = load_data()
    st.session_state.portfolio_list = saved_data.get("portfolio", [])
    st.session_state.events_list = saved_data.get("events", [])
    st.session_state.settings = saved_data.get("settings", {})
    st.session_state.data_loaded = True
    st.session_state.baseline_scenario = None

# Ensure lists exist if load failed or was empty
if 'portfolio_list' not in st.session_state: st.session_state.portfolio_list = []
if 'events_list' not in st.session_state: st.session_state.events_list = []
if 'settings' not in st.session_state: st.session_state.settings = {}

def trigger_save():
    """Helper to save current state to file."""
    data = {
        "portfolio": st.session_state.portfolio_list,
        "events": st.session_state.events_list,
        # We need to capture current sidebar values. 
        # Since sidebar widgets write to their own keys or return values, 
        # we might need to update st.session_state.settings before saving.
        "settings": st.session_state.settings 
    }
    if save_data(data):
        st.toast("Data Saved Successfully!", icon="💾")
    else:
        st.error("Failed to save data.")

def reset_portfolio():
    # Only resets lists, not file unless saved
    default_assets = [
        {"Name": "401k", "Category": "Stock Market", "Balance": 50000.0, "Monthly": 1000.0, "Rate": 0.07, "Tax Type": "Pre-Tax"},
        {"Name": "Roth IRA", "Category": "Stock Market", "Balance": 20000.0, "Monthly": 500.0, "Rate": 0.07, "Tax Type": "Roth"},
        {"Name": "Mortgage", "Category": "Debt/Liability", "Balance": 300000.0, "Monthly": 2000.0, "Rate": 0.04, "Tax Type": "N/A"}
    ]
    st.session_state.portfolio_list = default_assets
    st.session_state.events_list = [{"Event Name": "Down Payment", "Age": 35, "Cost": 50000.0}]
    st.session_state.baseline_scenario = None
    trigger_save() # Auto-save on reset
    st.rerun()

# ==========================================
# 2. DIALOGS
# ==========================================

@st.dialog("Manage Asset / Liability")
def asset_dialog(item=None, index=None):
    is_edit = item is not None
    
    name = item.get("Name", "") if is_edit else ""
    cat = item.get("Category", "Stock Market") if is_edit else "Stock Market"
    bal = item.get("Balance", 0.0) if is_edit else 0.0
    monthly = item.get("Monthly", 0.0) if is_edit else 0.0
    rate = item.get("Rate", 0.07) if is_edit else 0.07
    tax = item.get("Tax Type", "Taxable") if is_edit else "Taxable"
    
    with st.form("asset_form"):
        new_name = st.text_input("Name", value=name)
        new_cat = st.selectbox("Category", ["Stock Market", "Cash", "Real Estate", "Crypto", "Debt/Liability"], index=["Stock Market", "Cash", "Real Estate", "Crypto", "Debt/Liability"].index(cat))
        
        c1, c2 = st.columns(2)
        new_bal = c1.number_input("Current Balance ($)", value=float(bal), step=1000.0)
        
        if new_cat == "Debt/Liability":
             new_monthly = c2.number_input("Monthly Payment ($)", value=float(monthly), step=100.0)
             new_rate = st.number_input("Interest Rate (0.05 = 5%)", value=float(rate), step=0.01)
             new_tax = "N/A"
        else:
             new_monthly = c2.number_input("Monthly Contribution ($)", value=float(monthly), step=100.0)
             new_rate = st.number_input("Growth Rate (0.07 = 7%)", value=float(rate), step=0.01)
             if new_cat == "Real Estate":
                 new_tax = st.selectbox("Tax Type", ["Taxable", "Primary Residence"], index=0) 
             else:
                 opts = ["Taxable", "Roth", "Pre-Tax"]
                 try: idx = opts.index(tax)
                 except: idx = 0
                 new_tax = st.selectbox("Tax Type", opts, index=idx)
        
        submitted = st.form_submit_button("Save")
        if submitted:
            new_item = {
                "Name": new_name, "Category": new_cat, "Balance": new_bal, 
                "Monthly": new_monthly, "Rate": new_rate, "Tax Type": new_tax
            }
            if is_edit:
                st.session_state.portfolio_list[index] = new_item
            else:
                st.session_state.portfolio_list.append(new_item)
            trigger_save() # Auto-save
            st.rerun()

def delete_asset(index):
    st.session_state.portfolio_list.pop(index)
    trigger_save() # Auto-save
    st.rerun()

def open_edit_asset(index):
    asset_dialog(item=st.session_state.portfolio_list[index], index=index)
    
def open_add_asset():
    asset_dialog(item=None, index=None)


@st.dialog("Manage Life Event")
def event_dialog(item=None, index=None):
    is_edit = item is not None
    name = item.get("Event Name", "") if is_edit else ""
    age = item.get("Age", 40) if is_edit else 40
    cost = item.get("Cost", 10000.0) if is_edit else 10000.0
    
    with st.form("event_form"):
        new_name = st.text_input("Event Name", value=name)
        new_age = st.number_input("Age Occurring", value=int(age), step=1)
        new_cost = st.number_input("Cost ($ Today)", value=float(cost), step=1000.0)
        
        if st.form_submit_button("Save"):
            new_item = {"Event Name": new_name, "Age": new_age, "Cost": new_cost}
            if is_edit:
                st.session_state.events_list[index] = new_item
            else:
                st.session_state.events_list.append(new_item)
            trigger_save()
            st.rerun()

def delete_event(index):
    st.session_state.events_list.pop(index)
    trigger_save()
    st.rerun()

def open_edit_event(index):
    event_dialog(item=st.session_state.events_list[index], index=index)

def open_add_event():
    event_dialog(item=None, index=None)

# ==========================================
# 3. SIDEBAR INPUTS
# ==========================================
with st.sidebar:
    st.header("Storage")
    c_save, c_reset = st.columns(2)
    if c_save.button("💾 Save Settings"):
         trigger_save()
         
    if c_reset.button("Reset All", type="primary"):
        reset_portfolio()
    st.divider()

    st.header("1. Personal Details")
    s = st.session_state.settings
    
    # We update session state on change
    def update_setting(key):
        def _Callback():
            st.session_state.settings[key] = st.session_state[f"w_{key}"]
        return _Callback

    user_age = st.number_input("Current Age", 18, 84, s.get("user_age", 30), key="w_user_age", on_change=update_setting("user_age"))
    filing_status = st.selectbox("Tax Filing Status", ["Single", "Married (Joint)"], 
                                 index=0 if s.get("filing_status") == "Single" else 1, 
                                 key="w_filing_status", on_change=update_setting("filing_status"))
    retirement_age = 59 
    
    # --- PROJECTION PARAMETERS ---
    st.header("2. Forecast Settings")
    annual_spend = st.number_input("Desired Annual Spending ($)", value=s.get("annual_spend", 60000), step=1000, key="w_annual_spend", on_change=update_setting("annual_spend"))
    swr = st.slider("Safe Withdrawal Rate (%)", 3.0, 5.0, s.get("swr", 0.04)*100) / 100
    # Update SWR manually since slider is *100
    st.session_state.settings["swr"] = swr 
    
    with st.expander("Advanced Assumptions"):
        use_progressive = st.toggle("Use Progressive Tax Brackets", value=s.get("use_progressive", True), key="w_use_progressive", on_change=update_setting("use_progressive"))
        
        if not use_progressive:
            tax_flat_rate = st.slider("Flat Tax Rate Estimate (%)", 0, 40, int(s.get("tax_flat_rate", 0.15)*100)) / 100
            st.session_state.settings["tax_flat_rate"] = tax_flat_rate
        else:
            tax_flat_rate = 0.15
            
        contrib_growth = st.slider("Annual Contribution Increase (%)", 0.0, 10.0, s.get("contrib_growth", 0.03)*100) / 100
        st.session_state.settings["contrib_growth"] = contrib_growth
        
        inflation_rate = st.slider("Inflation (%)", 0.0, 8.0, s.get("inflation_rate", 0.025)*100) / 100
        st.session_state.settings["inflation_rate"] = inflation_rate

    # --- TIMEFRAME ---
    st.subheader("Timeframe")
    timeframe_options = {
        "5 Years": 5, "10 Years": 10, "15 Years": 15, 
        "20 Years": 20, "25 Years": 25, "30 Years": 30, 
        "Until Age 85": 85 - user_age
    }
    
    # Default index
    opts = list(timeframe_options.keys())
    saved_tf = s.get("timeframe", "Until Age 85")
    tf_idx = opts.index(saved_tf) if saved_tf in opts else 6
    
    selected_timeframe = st.selectbox("View Forecast Until", opts, index=tf_idx, key="w_timeframe", on_change=update_setting("timeframe"))
    years_to_project = timeframe_options[selected_timeframe]
    if years_to_project < 1: years_to_project = 1
    
    # Update A/B Testing Baseline button
    st.divider()
    if st.button("📸 Snap Baseline"):
        st.session_state.trigger_baseline = True


# ==========================================
# 4. MAIN AREA - CARDS UI
# ==========================================

st.subheader("📝 Portfolio")

c_title, c_add = st.columns([0.85, 0.15])
c_title.caption("Your Engines of Wealth")
if c_add.button("➕ Add Asset"):
    open_add_asset()

cols = st.columns(3)
for i, item in enumerate(st.session_state.portfolio_list):
    with cols[i % 3]:
        if item.get("Category") == "Debt/Liability":
             render_liability_card(item, i, open_edit_asset, delete_asset)
        else:
             render_asset_card(item, i, open_edit_asset, delete_asset)

st.divider()

# --- EVENTS SECTION ---
c_title_ev, c_add_ev = st.columns([0.85, 0.15])
c_title_ev.subheader("📅 Life Events")
c_title_ev.caption("Big one-time expenses")
if c_add_ev.button("➕ Add Event"):
    open_add_event()

ev_cols = st.columns(3)
for i, item in enumerate(st.session_state.events_list):
    with ev_cols[i % 3]:
        render_event_card(item, i, open_edit_event, delete_event)


# ==========================================
# 5. SIMULATION EXECUTION
# ==========================================

sim_params = {
    "annual_spend": annual_spend,
    "swr": swr,
    "inflation_rate": inflation_rate,
    "contrib_growth": contrib_growth,
    "filing_status": filing_status,
    "use_progressive": use_progressive,
    "tax_flat_rate": tax_flat_rate,
    "retirement_age": retirement_age
}

if st.session_state.portfolio_list:
    df_full = run_simulation(st.session_state.portfolio_list, st.session_state.events_list, user_age, years_to_project, sim_params)
    
    df_current = df_full.head(years_to_project + 1)
    
    if getattr(st.session_state, 'trigger_baseline', False):
        st.session_state.baseline_scenario = df_full.copy()
        st.session_state.trigger_baseline = False
        st.success("Baseline Snapshot Saved!")
    
    df_baseline = None
    if st.session_state.baseline_scenario is not None:
         df_baseline = st.session_state.baseline_scenario.head(years_to_project + 1)

    final_year_data = df_current.iloc[-1]
    
    # ==========================================
    # 6. VISUALIZATION
    # ==========================================
    st.divider()
    st.subheader("🏁 Financial Independence Dashboard")
    
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

    tab_inc, tab_nw, tab_tax = st.tabs(["💵 Income Stream", "📈 Net Worth", "🏛️ Tax Breakdown"])
    
    with tab_inc:
        col_zoom, col_log = st.columns([2,10])
        zoom = col_zoom.toggle("🔍 Zoom", value=True, key="zoom_toggle")
        
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
        
        fig_inc.update_layout(
            title="Net Passive Income Breakdown (Real $)", 
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_inc, use_container_width=True)
        
        st.info("ℹ️ **How to read:** 'Required Spending' is your annual lifestyle cost. 'Passive Income' is the safe withdrawal amount from your invested assets. When **Passive Income > Required Spending**, you are Financially Independent.")
        with st.expander("View Raw Data"):
             st.dataframe(df_current[["Year", "Age", "Passive Income", "Annual Spending"] + income_cols])

    with tab_nw:
        excluded_cols = ['Year', 'Age', 'Net Worth', 'Passive Income', 'Annual Spending']
        balance_cols = [c for c in df_current.columns if c not in excluded_cols and not c.endswith(" Income")]
        
        fig_nw = go.Figure()
        for col in balance_cols:
            fig_nw.add_trace(go.Scatter(x=df_current['Year'], y=df_current[col], mode='lines', stackgroup='one', name=col))
            
        fig_nw.update_layout(
            title="Net Worth Composition (Real $)", 
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_nw, use_container_width=True)
        
        st.info("ℹ️ **How to read:** This tracks your **Net Worth** (Total Assets - Debts) over time. It shows the projected growth of your wealth based on your contributions and market returns.")
        with st.expander("View Raw Data"):
             st.dataframe(df_current[["Year", "Age", "Net Worth"] + balance_cols])
        
    with tab_tax:
        tax_buckets = {"Taxable": [], "Roth": [], "Pre-Tax": []}
        for item in st.session_state.portfolio_list:
            t = item.get("Tax Type", "N/A")
            if t in tax_buckets:
                tax_buckets[t].append(f"{item['Name']} Income")
        
        df_tax = pd.DataFrame()
        df_tax['Year'] = df_current['Year']
        
        for bucket, cols in tax_buckets.items():
            valid_cols = [c for c in cols if c in df_current.columns]
            if valid_cols:
                df_tax[bucket] = df_current[valid_cols].sum(axis=1)
            else:
                df_tax[bucket] = 0.0
                
        fig_tax = go.Figure()
        for bucket in ["Taxable", "Roth", "Pre-Tax"]:
            fig_tax.add_trace(go.Scatter(x=df_tax['Year'], y=df_tax[bucket], mode='lines', stackgroup='one', name=bucket))
            
        fig_tax.update_layout(
            title="Passive Income by Tax Treatment (Net)", 
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_tax, use_container_width=True)

        st.info("ℹ️ **How to read:** This breaks down your passive income by tax treatment. **Roth**: Tax-free. **Pre-Tax**: Taxed as ordinary income. **Taxable**: Taxed on capital gains.")
        with st.expander("View Raw Data"):
             df_tax["Age"] = df_current["Age"]
             cols = ["Year", "Age", "Taxable", "Roth", "Pre-Tax"]
             st.dataframe(df_tax[cols])

else:
    st.info("👈 Please add assets above to begin.")