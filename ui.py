import streamlit as st
import pandas as pd

def card_container(key=None):
    """Returns a container with a defined style for cards."""
    return st.container(border=True)

def render_asset_card(asset, index, on_edit, on_delete):
    """Renders a single asset card."""
    with card_container(key=f"card_{index}"):
        c1, c2 = st.columns([0.8, 0.2])
        
        # Icon based on category
        icon = "💰"
        if asset.get("Category") == "Stock Market": icon = "📈"
        elif asset.get("Category") == "Real Estate": icon = "🏠"
        elif asset.get("Category") == "Crypto": icon = "🪙"
        elif asset.get("Category") == "Cash": icon = "💵"
        
        with c1:
            st.markdown(f"#### {icon} {asset.get('Name', 'Asset')}")
            st.markdown(f"**${asset.get('Balance', 0):,.0f}**")
            st.caption(f"{asset.get('Tax Type', 'N/A')} • {asset.get('Category')}")
            if asset.get("Monthly", 0) > 0:
                st.caption(f"+${asset.get('Monthly', 0):,.0f}/mo")
            if asset.get("Rate", 0) != 0:
                 st.caption(f"{asset.get('Rate', 0)*100:.1f}% Growth")
        
        with c2:
            if st.button("✏️", key=f"edit_{index}", help="Edit"):
                on_edit(index)
            if st.button("🗑️", key=f"del_{index}", help="Delete"):
                on_delete(index)

def render_liability_card(liability, index, on_edit, on_delete):
    """Renders a single liability card."""
    with card_container(key=f"l_card_{index}"):
        c1, c2 = st.columns([0.8, 0.2])
        
        with c1:
            st.markdown(f"#### 💳 {liability.get('Name', 'Debt')}")
            st.markdown(f"**-${liability.get('Balance', 0):,.0f}**")
            st.caption(f"{liability.get('Category')}")
            if liability.get("Monthly", 0) > 0:
                st.caption(f"PAY: ${liability.get('Monthly', 0):,.0f}/mo")
            if liability.get("Rate", 0) != 0:
                 st.caption(f"{liability.get('Rate', 0)*100:.1f}% APR")

        with c2:
            if st.button("✏️", key=f"edit_l_{index}", help="Edit"):
                on_edit(index)
            if st.button("🗑️", key=f"del_l_{index}", help="Delete"):
                on_delete(index)

def render_event_card(event, index, on_edit, on_delete):
    with card_container(key=f"ev_card_{index}"):
        c1, c2 = st.columns([0.8, 0.2])
        with c1:
             st.markdown(f"#### 📅 {event.get('Event Name')}")
             st.markdown(f"**Usage: ${event.get('Cost', 0):,.0f}**")
             st.caption(f"Age {event.get('Age')}")
        with c2:
            if st.button("✏️", key=f"edit_ev_{index}", help="Edit"):
                on_edit(index)
            if st.button("🗑️", key=f"del_ev_{index}", help="Delete"):
                on_delete(index)
