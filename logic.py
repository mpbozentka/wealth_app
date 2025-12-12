from models import Asset, Liability
import pandas as pd
import datetime

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

def run_simulation(portfolio_data, life_events_data, user_age, years_to_project, simulation_params):
    """
    Runs the wealth projection simulation.
    
    simulation_params expected keys:
    - annual_spend
    - swr (Safe Withdrawal Rate)
    - inflation_rate
    - contrib_growth
    - filing_status
    - use_progressive
    - tax_flat_rate
    - retirement_age
    """
    
    current_year_date = datetime.date.today().year
    
    # Unpack params
    inflation_rate = simulation_params.get('inflation_rate', 0.025)
    contrib_growth = simulation_params.get('contrib_growth', 0.03)
    swr = simulation_params.get('swr', 0.04)
    annual_spend = simulation_params.get('annual_spend', 60000)
    filing_status = simulation_params.get('filing_status', 'Single')
    use_progressive = simulation_params.get('use_progressive', True)
    tax_flat_rate = simulation_params.get('tax_flat_rate', 0.15)
    retirement_age = simulation_params.get('retirement_age', 65)

    sim_objects = []
    # If portfolio_data is a DataFrame (from data_editor), convert to dict
    if isinstance(portfolio_data, pd.DataFrame):
        records = portfolio_data.to_dict('records')
    else:
        records = portfolio_data

    for p in records:
        # Adapt keys if necessary, assuming new format from st.data_editor might need mapping
        # OLD format: name, balance, rate, monthly, tax, category, type
        # NEW format (DataFrame): Name, Category, Balance, Monthly, Rate, Tax Type
        
        # We need to handle both potentially, or simpler: just stick to one schema.
        # Let's assume we map the new DataFrame schema to the class constructor.
        
        # Try to detect if it's the old dict or new dict
        name = p.get('name') or p.get('Name')
        cat = p.get('category') or p.get('Category')
        bal = p.get('balance') or p.get('Balance')
        monthly = p.get('monthly') or p.get('Monthly')
        rate = p.get('rate') or p.get('Rate') # Could be growth or interest
        tax = p.get('tax') or p.get('Tax Type')
        
        if cat == "Debt/Liability":
             sim_objects.append(Liability(name, float(bal), float(rate), float(monthly)))
        else:
             sim_objects.append(Asset(name, float(bal), float(monthly)*12, float(rate), tax, cat))
            
    data = []
    current_year = current_year_date
    
    # We must run the full simulation until age 85 internally 
    max_projection_years = 85 - user_age
    
    # If using DataFrame for life events
    if isinstance(life_events_data, pd.DataFrame):
        life_events = life_events_data.to_dict('records')
    else:
        life_events = life_events_data

    for year in range(max_projection_years + 1):
        current_age = user_age + year
        row = {"Year": current_year, "Age": current_age}
        
        # --- A. LIFE EVENTS ---
        for ev in life_events:
            ev_name = ev.get('name') or ev.get('Event Name')
            ev_age = ev.get('age') or ev.get('Age')
            ev_cost = ev.get('cost') or ev.get('Cost')
            
            if ev_age == current_age:
                future_cost = float(ev_cost) * ((1 + inflation_rate) ** year)
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
