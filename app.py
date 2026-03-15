import streamlit as st
import pandas as pd
import json
import os
import math
from datetime import datetime, date, timedelta

st.set_page_config(page_title="Commercial Project Identification", layout="wide", page_icon="🏢")

# --- Data Directory ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helper: Load/Save JSON ---
def load_json(filename, default):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

# --- Load All Data ---
if "targets" not in st.session_state:
    st.session_state.targets = load_json("targets.json", [])
if "bids" not in st.session_state:
    st.session_state.bids = load_json("bids.json", [])
if "outreach" not in st.session_state:
    st.session_state.outreach = load_json("outreach.json", [])
if "competitors" not in st.session_state:
    st.session_state.competitors = load_json("competitors.json", [])
if "vendor_registrations" not in st.session_state:
    st.session_state.vendor_registrations = load_json("vendor_registrations.json", [])

def save_all():
    save_json("targets.json", st.session_state.targets)
    save_json("bids.json", st.session_state.bids)
    save_json("outreach.json", st.session_state.outreach)
    save_json("competitors.json", st.session_state.competitors)
    save_json("vendor_registrations.json", st.session_state.vendor_registrations)

# ============================================================
# PRIORITY SCORING & REVENUE ESTIMATION ENGINE
# ============================================================
def estimate_revenue(target):
    """Estimate annual contract revenue based on target type and details."""
    t = target.get("type", "")
    notes = target.get("notes", "").lower()

    # Extract building count from notes
    buildings = 1
    for phrase in ["18 schools", "18 buildings"]:
        if phrase in notes: buildings = 18; break
    for phrase in ["13 schools", "13 buildings"]:
        if phrase in notes: buildings = 13; break
    for phrase in ["11 schools", "11 buildings"]:
        if phrase in notes: buildings = 11; break
    for phrase in ["24 school", "24 buildings", "24+"]:
        if phrase in notes: buildings = 24; break
    import re
    bldg_match = re.search(r'(\d+)\s*(?:schools|buildings|facilities|campuses|fire station|locations|branches|centers)', notes)
    if bldg_match:
        buildings = max(buildings, int(bldg_match.group(1)))

    # Extract population
    pop = 0
    pop_match = re.search(r'pop[ulation]*[\s~:]*([0-9,]+)', notes)
    if pop_match:
        pop = int(pop_match.group(1).replace(",", ""))

    # Base revenue by type
    revenue_map = {
        "Municipality": 3000 + (buildings * 2500),
        "School District": buildings * 3500,
        "Park District": buildings * 2000,
        "Library District": buildings * 2500,
        "Township": 2000 + (buildings * 1500),
        "HOA/Condo Association": 4000,
        "Property Manager": 15000,
        "Shopping Center": 12000,
        "Office Park": 10000,
        "Industrial Park": 8000,
        "Apartment Complex": 5000,
        "Church/Religious": 2500,
        "Hospital/Medical": 15000,
        "Car Dealership": 4000,
        "Hotel/Hospitality": 5000,
        "Senior Living": 5000,
        "Self-Storage": 3000,
        "Other Commercial": 5000,
    }
    base = revenue_map.get(t, 3000)

    # Boost for large municipalities
    if t == "Municipality" and pop > 50000:
        base = base * 1.5
    elif t == "Municipality" and pop > 25000:
        base = base * 1.2

    # Boost for large HOA/property managers
    if "properties" in notes or "portfolio" in notes:
        base = base * 2

    # Boost for keywords suggesting large facilities
    if any(w in notes for w in ["massive", "large", "major", "huge", "biggest", "largest"]):
        base = base * 1.3

    return round(base)

def calculate_priority_score(target):
    """Score targets 0-100 based on revenue potential, accessibility, and win likelihood."""
    score = 0
    t = target.get("type", "")
    notes = target.get("notes", "").lower()
    rev = estimate_revenue(target)

    # Revenue potential (0-40 points)
    if rev >= 20000: score += 40
    elif rev >= 10000: score += 32
    elif rev >= 5000: score += 22
    elif rev >= 3000: score += 15
    else: score += 8

    # Accessibility — how easy to get in (0-25 points)
    # Private entities are easier (no formal bid process)
    private_types = ["HOA/Condo Association", "Property Manager", "Shopping Center",
                     "Apartment Complex", "Church/Religious", "Car Dealership",
                     "Hotel/Hospitality", "Senior Living", "Self-Storage", "Office Park", "Industrial Park"]
    if t in private_types:
        score += 25
    elif t == "Municipality":
        score += 12
    elif t in ["School District", "Park District"]:
        score += 15
    else:
        score += 10

    # Procurement portal exists (0-15 points) — means bids are findable
    website = target.get("website", "")
    vendor_reg = target.get("vendor_reg", "")
    if website and ("bid" in website.lower() or "procurement" in website.lower() or "purchasing" in website.lower()):
        score += 15
    elif website:
        score += 8
    elif vendor_reg in ["Registered"]:
        score += 15
    else:
        score += 3

    # Recurring revenue potential (0-20 points)
    recurring_types = ["Property Manager", "HOA/Condo Association", "Shopping Center",
                       "Apartment Complex", "Municipality", "School District", "Park District"]
    if t in recurring_types:
        score += 20
    else:
        score += 10

    return min(score, 100)

def get_priority_tier(score):
    if score >= 75: return "A"
    elif score >= 55: return "B"
    elif score >= 35: return "C"
    else: return "D"

# ============================================================
# OUTREACH CALENDAR DATA
# ============================================================
OUTREACH_CALENDAR = {
    "January": {
        "focus": "Prep & Planning",
        "targets": ["Update all insurance certificates", "Refresh bid package documents", "Register on procurement portals you haven't joined yet"],
        "types": []
    },
    "February": {
        "focus": "Municipality & School Outreach",
        "targets": ["Contact municipal facilities directors — budgets being planned NOW", "Send vendor intro emails to all municipalities", "Register on approved vendor lists"],
        "types": ["Municipality", "Township"]
    },
    "March": {
        "focus": "School Districts & Parks",
        "targets": ["Contact school district facilities directors about summer work", "Reach out to park districts for spring/summer cleaning", "Submit proposals for summer maintenance contracts", "Start cold outreach to HOAs — spring cleaning season"],
        "types": ["School District", "Park District", "HOA/Condo Association"]
    },
    "April": {
        "focus": "HOAs & Property Managers",
        "targets": ["HOA boards meet Q1/Q2 — attend meetings or submit proposals", "Contact property managers about seasonal contracts", "Follow up on all March outreach"],
        "types": ["HOA/Condo Association", "Property Manager", "Apartment Complex"]
    },
    "May": {
        "focus": "Commercial Properties",
        "targets": ["Shopping centers want clean exteriors for summer traffic", "Office parks need spring cleaning", "Contact car dealerships — lot and building washing"],
        "types": ["Shopping Center", "Office Park", "Car Dealership"]
    },
    "June": {
        "focus": "Execute Summer Work & Upsell",
        "targets": ["Schools are empty — execute summer contracts", "Upsell existing clients on additional services", "Contact churches about summer campus cleaning"],
        "types": ["School District", "Church/Religious"]
    },
    "July": {
        "focus": "Mid-Season Push",
        "targets": ["Follow up on all pending proposals", "Target apartment complexes for fall prep", "Contact senior living facilities"],
        "types": ["Apartment Complex", "Senior Living", "Hospital/Medical"]
    },
    "August": {
        "focus": "Fall Contract Planning",
        "targets": ["Contact municipalities about fall gutter cleaning", "Reach out to HOAs for fall maintenance packages", "Back-to-school building wash follow-ups"],
        "types": ["Municipality", "HOA/Condo Association", "School District"]
    },
    "September": {
        "focus": "Fall Services Push",
        "targets": ["Gutter cleaning season starting — push to all targets", "Shopping center fall maintenance", "Industrial park seasonal cleaning"],
        "types": ["Shopping Center", "Industrial Park", "Library District"]
    },
    "October": {
        "focus": "Year-End Contracts",
        "targets": ["Municipalities spending remaining budget — contact now", "Propose annual contracts starting January", "Follow up on all outstanding proposals"],
        "types": ["Municipality", "Park District", "Township"]
    },
    "November": {
        "focus": "Renewals & Relationship Building",
        "targets": ["Contact existing clients about contract renewals", "Send thank-you notes to current clients", "Prepare proposals for next year"],
        "types": ["Property Manager"]
    },
    "December": {
        "focus": "Planning & FOIA",
        "targets": ["Send FOIA requests to all municipalities for bid history", "Analyze competitor data from the year", "Plan Q1 outreach strategy", "Update target database with new intel"],
        "types": []
    },
}

# --- Styling ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background: #0f1b2d; }
    [data-testid="stSidebar"] * { color: #e0e6ed !important; }
    .main-header { font-size: 2rem; font-weight: 800; color: #1a365d; margin-bottom: 0; }
    .sub-header { font-size: 1rem; color: #64748b; margin-top: 0; }
    .stat-card {
        background: linear-gradient(135deg, #1e3a5f, #2563eb);
        padding: 18px 20px; border-radius: 12px; color: white; text-align: center;
    }
    .stat-card h1 { margin: 0; font-size: 2.2rem; font-weight: 800; }
    .stat-card p { margin: 0; font-size: 0.85rem; opacity: 0.85; }
    .tier-a { background: #10b981; color: white; padding: 3px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85rem; }
    .tier-b { background: #3b82f6; color: white; padding: 3px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85rem; }
    .tier-c { background: #f59e0b; color: white; padding: 3px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85rem; }
    .tier-d { background: #94a3b8; color: white; padding: 3px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85rem; }
    .status-new { background: #3b82f6; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; }
    .status-applied { background: #f59e0b; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; }
    .status-won { background: #10b981; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; }
    .status-lost { background: #ef4444; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; }
    .status-pending { background: #8b5cf6; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; }
    .month-card {
        border: 2px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 12px;
    }
    .month-active { border-color: #2563eb; background: #eff6ff; }
    .reg-done { color: #10b981; font-weight: bold; }
    .reg-pending { color: #f59e0b; font-weight: bold; }
    .reg-not { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("## Commercial Project ID")
    st.markdown("*Northern Suburbs Chicago*")
    st.divider()
    page = st.radio("Navigation", [
        "Dashboard",
        "Priority Rankings",
        "Target Database",
        "Outreach Calendar",
        "Active Bids",
        "Competitor Intel",
        "Cold Outreach",
        "Email Sender",
        "Proposal Generator",
        "Service Packages",
        "Bid Package",
        "Company Profile",
        "Contract Template",
        "Vendor Registration",
        "Municipal Guide",
        "Procurement Portals",
        "Knowledge Base",
        "Email Templates",
    ], label_visibility="collapsed")
    st.divider()
    st.caption("Data auto-saves to disk")

# ============================================================
# DASHBOARD
# ============================================================
if page == "Dashboard":
    st.markdown('<p class="main-header">Commercial Project Identification</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Northern Suburbs of Chicago — Bid Tracking & Outreach Platform</p>', unsafe_allow_html=True)
    st.markdown("")

    total_targets = len(st.session_state.targets)
    total_bids = len(st.session_state.bids)
    active_bids = len([b for b in st.session_state.bids if b.get("status") in ["New", "Applied", "Pending"]])
    won_bids = len([b for b in st.session_state.bids if b.get("status") == "Won"])
    outreach_sent = len([o for o in st.session_state.outreach if o.get("status") != "Draft"])
    outreach_responses = len([o for o in st.session_state.outreach if o.get("status") == "Responded"])

    # Estimated total pipeline value
    total_pipeline = sum(estimate_revenue(t) for t in st.session_state.targets)
    tier_a_targets = [t for t in st.session_state.targets if get_priority_tier(calculate_priority_score(t)) == "A"]
    tier_a_revenue = sum(estimate_revenue(t) for t in tier_a_targets)

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in [
        (c1, total_targets, "Total Targets"),
        (c2, len(tier_a_targets), "Tier A Targets"),
        (c3, f"${tier_a_revenue:,.0f}", "Tier A Pipeline"),
        (c4, f"${total_pipeline:,.0f}", "Total Pipeline Value"),
    ]:
        with col:
            st.markdown(f'<div class="stat-card"><h1>{val}</h1><p>{label}</p></div>', unsafe_allow_html=True)

    st.markdown("")
    c5, c6, c7, c8 = st.columns(4)
    for col, val, label in [
        (c5, total_bids, "Bids Tracked"),
        (c6, active_bids, "Active Bids"),
        (c7, outreach_sent, "Outreach Sent"),
        (c8, outreach_responses, "Responses"),
    ]:
        with col:
            st.markdown(f'<div class="stat-card"><h1>{val}</h1><p>{label}</p></div>', unsafe_allow_html=True)

    st.markdown("")

    # Target breakdown by type
    if st.session_state.targets:
        st.markdown("### Target Breakdown")
        type_counts = {}
        type_revenue = {}
        for t in st.session_state.targets:
            tp = t.get("type", "Unknown")
            type_counts[tp] = type_counts.get(tp, 0) + 1
            type_revenue[tp] = type_revenue.get(tp, 0) + estimate_revenue(t)

        breakdown_data = []
        for tp in sorted(type_counts.keys()):
            breakdown_data.append({"Type": tp, "Count": type_counts[tp], "Est. Annual Revenue": f"${type_revenue[tp]:,.0f}"})
        st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)

    # Current month actions
    current_month = date.today().strftime("%B")
    if current_month in OUTREACH_CALENDAR:
        cal = OUTREACH_CALENDAR[current_month]
        st.markdown(f"### This Month: {cal['focus']}")
        for action in cal["targets"]:
            st.markdown(f"- {action}")

    # Recent Activity
    st.markdown("### Recent Activity")
    all_activity = []
    for b in st.session_state.bids[-5:]:
        all_activity.append(f"**Bid**: {b.get('entity', 'Unknown')} — {b.get('service', '')} — Status: {b.get('status', 'New')}")
    for o in st.session_state.outreach[-5:]:
        all_activity.append(f"**Outreach**: {o.get('entity', 'Unknown')} — {o.get('contact', '')} — Status: {o.get('status', 'Draft')}")
    if all_activity:
        for a in reversed(all_activity):
            st.markdown(f"- {a}")
    else:
        st.info("No activity yet. Check Priority Rankings to see where to start.")

# ============================================================
# PRIORITY RANKINGS
# ============================================================
elif page == "Priority Rankings":
    st.markdown("## Priority Rankings & Revenue Estimator")
    st.markdown("Every target scored and ranked by estimated revenue, accessibility, and win probability.")

    if not st.session_state.targets:
        st.info("No targets loaded. Go to Target Database to load data.")
    else:
        # Calculate scores for all targets
        scored = []
        for t in st.session_state.targets:
            score = calculate_priority_score(t)
            rev = estimate_revenue(t)
            tier = get_priority_tier(score)
            scored.append({
                "entity": t.get("entity", ""),
                "type": t.get("type", ""),
                "town": t.get("town", ""),
                "county": t.get("county", ""),
                "score": score,
                "tier": tier,
                "est_revenue": rev,
                "notes": t.get("notes", ""),
                "website": t.get("website", ""),
                "contact": t.get("contact", ""),
            })

        df = pd.DataFrame(scored).sort_values("score", ascending=False).reset_index(drop=True)
        df.index = df.index + 1
        df.index.name = "Rank"

        # Summary by tier
        st.markdown("### Pipeline Summary")
        tc1, tc2, tc3, tc4 = st.columns(4)
        for col, tier, label, css in [
            (tc1, "A", "Tier A (75-100)", "tier-a"),
            (tc2, "B", "Tier B (55-74)", "tier-b"),
            (tc3, "C", "Tier C (35-54)", "tier-c"),
            (tc4, "D", "Tier D (0-34)", "tier-d"),
        ]:
            tier_df = df[df["tier"] == tier]
            with col:
                st.markdown(f'<span class="{css}">{label}</span>', unsafe_allow_html=True)
                st.metric("Targets", len(tier_df))
                st.metric("Est. Revenue", f"${tier_df['est_revenue'].sum():,.0f}")

        st.divider()

        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            filter_tier = st.multiselect("Filter by Tier", ["A", "B", "C", "D"], default=["A", "B"])
        with f2:
            filter_type = st.multiselect("Filter by Type", sorted(df["type"].unique()))
        with f3:
            filter_county = st.multiselect("Filter by County", sorted(df["county"].dropna().unique()))

        filtered = df
        if filter_tier:
            filtered = filtered[filtered["tier"].isin(filter_tier)]
        if filter_type:
            filtered = filtered[filtered["type"].isin(filter_type)]
        if filter_county:
            filtered = filtered[filtered["county"].isin(filter_county)]

        # Display
        def color_tier(val):
            colors = {"A": "background-color: #10b981; color: white",
                      "B": "background-color: #3b82f6; color: white",
                      "C": "background-color: #f59e0b; color: white",
                      "D": "background-color: #94a3b8; color: white"}
            return colors.get(val, "")

        display_cols = ["entity", "type", "town", "county", "score", "tier", "est_revenue", "contact"]
        styled = filtered[display_cols].style.applymap(color_tier, subset=["tier"]).format({
            "est_revenue": "${:,.0f}",
            "score": "{:.0f}/100"
        })
        st.dataframe(styled, use_container_width=True)
        st.markdown(f"**Showing {len(filtered)} targets | Est. Total Revenue: ${filtered['est_revenue'].sum():,.0f}/year**")

        # Top 20 chart
        st.markdown("### Top 20 Revenue Opportunities")
        top20 = df.head(20).sort_values("est_revenue", ascending=True)
        import plotly.express as px
        fig = px.bar(top20, x="est_revenue", y="entity", orientation="h",
                     color="tier", color_discrete_map={"A": "#10b981", "B": "#3b82f6", "C": "#f59e0b", "D": "#94a3b8"},
                     labels={"est_revenue": "Estimated Annual Revenue", "entity": ""},
                     title="")
        fig.update_layout(xaxis_tickprefix="$", xaxis_tickformat=",", height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

        # Revenue by type
        st.markdown("### Revenue Potential by Target Type")
        type_rev = df.groupby("type")["est_revenue"].sum().sort_values(ascending=False).reset_index()
        fig2 = px.bar(type_rev, x="type", y="est_revenue", color="type",
                      labels={"est_revenue": "Total Est. Revenue", "type": ""},
                      title="")
        fig2.update_layout(xaxis_tickangle=-45, yaxis_tickprefix="$", yaxis_tickformat=",", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

        # Export
        csv = df.to_csv(index=True)
        st.download_button("Download Rankings as CSV", csv, "priority_rankings.csv", "text/csv")

# ============================================================
# TARGET DATABASE
# ============================================================
elif page == "Target Database":
    st.markdown("## Target Database")
    st.markdown("Every potential client in the northern suburbs.")

    with st.expander("Add New Target", expanded=False):
        with st.form("add_target", clear_on_submit=True):
            tc1, tc2 = st.columns(2)
            with tc1:
                t_name = st.text_input("Entity Name")
                t_type = st.selectbox("Type", [
                    "Municipality", "School District", "Park District", "Library District",
                    "Township", "HOA/Condo Association", "Property Manager",
                    "Shopping Center", "Office Park", "Industrial Park",
                    "Apartment Complex", "Church/Religious", "Hospital/Medical",
                    "Car Dealership", "Hotel/Hospitality", "Senior Living",
                    "Self-Storage", "Other Commercial"
                ])
                t_town = st.text_input("Town/City")
                t_county = st.selectbox("County", ["Cook", "Lake", "DuPage", "McHenry", "Kane"])
            with tc2:
                t_contact = st.text_input("Contact Name")
                t_title = st.text_input("Contact Title")
                t_phone = st.text_input("Phone")
                t_email = st.text_input("Email")
            tc3, tc4 = st.columns(2)
            with tc3:
                t_website = st.text_input("Website/Procurement URL")
                t_vendor_reg = st.selectbox("Vendor Registration", ["Unknown", "Required - Not Registered", "Registered", "Not Required"])
            with tc4:
                t_services = st.multiselect("Services Needed", ["Power Washing", "Window Cleaning", "Gutter Cleaning", "Roof Cleaning", "Graffiti Removal", "Concrete Cleaning", "Fleet Washing"])
                t_notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Add Target", use_container_width=True)
            if submitted and t_name:
                st.session_state.targets.append({
                    "entity": t_name, "type": t_type, "town": t_town, "county": t_county,
                    "contact": t_contact, "contact_title": t_title, "phone": t_phone,
                    "email": t_email, "website": t_website, "vendor_reg": t_vendor_reg,
                    "services": t_services, "notes": t_notes, "date_added": date.today().isoformat(),
                    "status": "Prospect"
                })
                save_all()
                st.success(f"Added {t_name}")
                st.rerun()

    # Filters
    if st.session_state.targets:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            filter_type = st.multiselect("Filter by Type", sorted(set(t["type"] for t in st.session_state.targets)))
        with f2:
            filter_county = st.multiselect("Filter by County", sorted(set(t.get("county", "") for t in st.session_state.targets)))
        with f3:
            all_towns = sorted(set(t.get("town", "") for t in st.session_state.targets if t.get("town")))
            filter_town = st.multiselect("Filter by Town", all_towns)
        with f4:
            search = st.text_input("Search", placeholder="Search by name...")

        filtered = st.session_state.targets
        if filter_type:
            filtered = [t for t in filtered if t["type"] in filter_type]
        if filter_county:
            filtered = [t for t in filtered if t.get("county") in filter_county]
        if filter_town:
            filtered = [t for t in filtered if t.get("town") in filter_town]
        if search:
            filtered = [t for t in filtered if search.lower() in t.get("entity", "").lower() or search.lower() in t.get("notes", "").lower()]

        df = pd.DataFrame(filtered)
        display_cols = [c for c in ["entity", "type", "town", "county", "contact", "phone", "email", "vendor_reg", "status"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        st.markdown(f"**Showing {len(filtered)} of {len(st.session_state.targets)} targets**")

        csv = df.to_csv(index=False)
        st.download_button("Download as CSV", csv, "targets.csv", "text/csv")
    else:
        st.info("No targets loaded yet.")

# ============================================================
# OUTREACH CALENDAR
# ============================================================
elif page == "Outreach Calendar":
    st.markdown("## Outreach Calendar")
    st.markdown("Month-by-month plan for when to contact each target type.")

    current_month = date.today().strftime("%B")

    for month, cal in OUTREACH_CALENDAR.items():
        is_current = month == current_month
        css_class = "month-active" if is_current else ""
        marker = " (NOW)" if is_current else ""

        with st.expander(f"**{month}{marker}** — {cal['focus']}", expanded=is_current):
            st.markdown(f"### Focus: {cal['focus']}")
            st.markdown("**Action Items:**")
            for action in cal["targets"]:
                st.markdown(f"- {action}")

            if cal["types"] and st.session_state.targets:
                matching = [t for t in st.session_state.targets if t.get("type") in cal["types"]]
                if matching:
                    st.markdown(f"**Matching targets to contact: {len(matching)}**")
                    type_breakdown = {}
                    for t in matching:
                        tp = t.get("type", "")
                        type_breakdown[tp] = type_breakdown.get(tp, 0) + 1
                    for tp, count in sorted(type_breakdown.items()):
                        st.markdown(f"- {tp}: {count}")

    st.divider()
    st.markdown("### Weekly Outreach Targets")
    st.markdown("""
    To systematically work through your database:
    - **Week 1**: Contact all Tier A targets for the month's focus types
    - **Week 2**: Contact all Tier B targets for the month's focus types
    - **Week 3**: Follow up on Week 1 outreach + contact Tier C targets
    - **Week 4**: Follow up on all outreach + prep for next month
    """)

    # Generate this month's hit list
    if st.session_state.targets and current_month in OUTREACH_CALENDAR:
        cal = OUTREACH_CALENDAR[current_month]
        if cal["types"]:
            st.markdown(f"### This Month's Hit List ({current_month})")
            matching = [t for t in st.session_state.targets if t.get("type") in cal["types"]]
            scored_list = []
            for t in matching:
                scored_list.append({
                    "entity": t.get("entity"),
                    "type": t.get("type"),
                    "town": t.get("town"),
                    "score": calculate_priority_score(t),
                    "tier": get_priority_tier(calculate_priority_score(t)),
                    "est_revenue": estimate_revenue(t),
                    "contact": t.get("contact"),
                    "phone": t.get("phone"),
                })
            hit_df = pd.DataFrame(scored_list).sort_values("score", ascending=False)
            st.dataframe(hit_df, use_container_width=True, hide_index=True)

# ============================================================
# ACTIVE BIDS
# ============================================================
elif page == "Active Bids":
    st.markdown("## Active Bids Tracker")
    st.markdown("Track every bid from discovery to award.")

    with st.expander("Log New Bid", expanded=False):
        with st.form("add_bid", clear_on_submit=True):
            b1, b2 = st.columns(2)
            with b1:
                b_entity = st.text_input("Entity / Agency")
                b_service = st.selectbox("Service", ["Power Washing", "Window Cleaning", "Gutter Cleaning", "Roof Cleaning", "Multiple Services", "Other"])
                b_source = st.selectbox("Source", ["DemandStar", "BidNet", "Cook County Bonfire", "Lake County Portal", "BidBuy IL", "Municipality Website", "Cold Outreach", "Referral", "Other"])
                b_url = st.text_input("Bid URL / Link")
            with b2:
                b_deadline = st.date_input("Bid Deadline", value=date.today() + timedelta(days=30))
                b_amount = st.number_input("Our Bid Amount ($)", min_value=0, value=0, step=500)
                b_status = st.selectbox("Status", ["New", "Reviewing", "Applied", "Pending", "Won", "Lost", "No Bid"])
                b_notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Log Bid", use_container_width=True)
            if submitted and b_entity:
                st.session_state.bids.append({
                    "entity": b_entity, "service": b_service, "source": b_source,
                    "url": b_url, "deadline": b_deadline.isoformat(), "amount": b_amount,
                    "status": b_status, "notes": b_notes, "date_added": date.today().isoformat()
                })
                save_all()
                st.success(f"Bid logged for {b_entity}")
                st.rerun()

    if st.session_state.bids:
        status_filter = st.multiselect("Filter by Status", ["New", "Reviewing", "Applied", "Pending", "Won", "Lost", "No Bid"], default=["New", "Reviewing", "Applied", "Pending"])
        filtered_bids = [b for b in st.session_state.bids if b["status"] in status_filter] if status_filter else st.session_state.bids

        for i, bid in enumerate(filtered_bids):
            with st.container():
                bc1, bc2, bc3, bc4, bc5 = st.columns([3, 2, 2, 1.5, 1.5])
                with bc1:
                    st.markdown(f"**{bid['entity']}**")
                    st.caption(f"{bid['service']} | Source: {bid['source']}")
                with bc2:
                    st.markdown(f"Deadline: **{bid['deadline']}**")
                with bc3:
                    if bid['amount'] > 0:
                        st.markdown(f"Our Bid: **${bid['amount']:,.0f}**")
                with bc4:
                    st.markdown(f"**{bid['status']}**")
                with bc5:
                    actual_idx = st.session_state.bids.index(bid)
                    new_status = st.selectbox("Update", ["New", "Reviewing", "Applied", "Pending", "Won", "Lost", "No Bid"],
                                            index=["New", "Reviewing", "Applied", "Pending", "Won", "Lost", "No Bid"].index(bid["status"]),
                                            key=f"bid_status_{i}", label_visibility="collapsed")
                    if new_status != bid["status"]:
                        st.session_state.bids[actual_idx]["status"] = new_status
                        save_all()
                        st.rerun()
                st.divider()

        won_total = sum(b["amount"] for b in st.session_state.bids if b["status"] == "Won")
        pending_total = sum(b["amount"] for b in st.session_state.bids if b["status"] in ["Applied", "Pending"])
        st.markdown(f"**Won Revenue: ${won_total:,.0f}** | **Pending Revenue: ${pending_total:,.0f}**")
    else:
        st.info("No bids logged yet.")

# ============================================================
# COMPETITOR INTEL
# ============================================================
elif page == "Competitor Intel":
    st.markdown("## Competitor Intelligence")
    st.markdown("Track competing bids on public contracts. In Illinois, government bid tabulations are public record after award.")

    st.markdown("""
    ### How to Get Competitor Bid Info
    1. **After award**, request the **bid tabulation sheet** from the awarding entity
    2. File a **FOIA request** — municipalities must respond within 5 business days
    3. Many entities post bid tabs on their procurement page automatically
    4. DemandStar sometimes shows awarded amounts
    """)

    with st.expander("Log Competitor Bid", expanded=False):
        with st.form("add_competitor", clear_on_submit=True):
            cc1, cc2 = st.columns(2)
            with cc1:
                c_entity = st.text_input("Contract / Entity")
                c_competitor = st.text_input("Competitor Name")
                c_amount = st.number_input("Their Bid ($)", min_value=0, value=0, step=500)
            with cc2:
                c_our_bid = st.number_input("Our Bid ($)", min_value=0, value=0, step=500)
                c_winner = st.selectbox("Winner?", ["Unknown", "They Won", "We Won", "Someone Else"])
                c_notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Log Competitor", use_container_width=True)
            if submitted and c_competitor:
                st.session_state.competitors.append({
                    "entity": c_entity, "competitor": c_competitor, "their_bid": c_amount,
                    "our_bid": c_our_bid, "winner": c_winner, "notes": c_notes,
                    "date_added": date.today().isoformat()
                })
                save_all()
                st.success("Competitor logged")
                st.rerun()

    if st.session_state.competitors:
        df = pd.DataFrame(st.session_state.competitors)
        df_display = df[["entity", "competitor", "their_bid", "our_bid", "winner", "date_added"]].copy()
        df_display["their_bid"] = df_display["their_bid"].apply(lambda x: f"${x:,.0f}" if x > 0 else "—")
        df_display["our_bid"] = df_display["our_bid"].apply(lambda x: f"${x:,.0f}" if x > 0 else "—")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        all_competitors = [c["competitor"] for c in st.session_state.competitors if c["competitor"]]
        if all_competitors:
            st.markdown("### Known Competitors")
            for comp in sorted(set(all_competitors)):
                count = all_competitors.count(comp)
                wins = len([c for c in st.session_state.competitors if c["competitor"] == comp and c["winner"] == "They Won"])
                st.markdown(f"- **{comp}** — seen in {count} bids, won {wins}")
    else:
        st.info("No competitor data logged yet.")

    st.markdown("""
    ### FOIA Template
    > *Dear [Municipality] Clerk,*
    >
    > *Pursuant to the Illinois Freedom of Information Act (5 ILCS 140), I am requesting copies of the bid tabulation sheets and award documents for [Contract Name/Number] related to exterior building maintenance services.*
    >
    > *Please provide this information in electronic format if available.*
    >
    > *Thank you,*
    > *[Your Name, Company]*
    """)

# ============================================================
# COLD OUTREACH
# ============================================================
elif page == "Cold Outreach":
    st.markdown("## Cold Outreach Tracker")
    st.markdown("Reach private entities that don't post public bids.")

    with st.expander("New Outreach", expanded=False):
        with st.form("add_outreach", clear_on_submit=True):
            o1, o2 = st.columns(2)
            with o1:
                o_entity = st.text_input("Entity / Property Name")
                o_type = st.selectbox("Type", [
                    "Apartment Complex", "HOA/Condo", "Shopping Center", "Office Building",
                    "Industrial Park", "Medical Complex", "Property Manager", "Church",
                    "Car Dealership", "Hotel/Hospitality", "Senior Living", "Self-Storage",
                    "Restaurant/Retail", "Other"
                ])
                o_contact = st.text_input("Contact Name")
                o_title = st.text_input("Contact Title")
            with o2:
                o_email = st.text_input("Email")
                o_phone = st.text_input("Phone")
                o_town = st.text_input("Town")
                o_status = st.selectbox("Status", ["Draft", "Sent", "Follow-Up Needed", "Responded", "Meeting Set", "Quoted", "Won", "Lost", "No Response"])
            o_services = st.multiselect("Services to Pitch", ["Power Washing", "Window Cleaning", "Gutter Cleaning", "Roof Cleaning", "Concrete/Parking Lot", "Graffiti Removal"])
            o_notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Log Outreach", use_container_width=True)
            if submitted and o_entity:
                st.session_state.outreach.append({
                    "entity": o_entity, "type": o_type, "contact": o_contact,
                    "contact_title": o_title, "email": o_email, "phone": o_phone,
                    "town": o_town, "status": o_status, "services": o_services,
                    "notes": o_notes, "date_added": date.today().isoformat(),
                    "last_contact": date.today().isoformat(), "follow_up_date": (date.today() + timedelta(days=7)).isoformat()
                })
                save_all()
                st.success(f"Outreach logged for {o_entity}")
                st.rerun()

    if st.session_state.outreach:
        today = date.today().isoformat()
        follow_ups = [o for o in st.session_state.outreach if o.get("follow_up_date", "") <= today and o["status"] in ["Sent", "Follow-Up Needed"]]
        if follow_ups:
            st.warning(f"**{len(follow_ups)} follow-ups due today or overdue!**")
            for fu in follow_ups:
                st.markdown(f"- **{fu['entity']}** ({fu['town']}) — {fu['contact']} — {fu['email']}")

        o_status_filter = st.multiselect("Filter", ["Draft", "Sent", "Follow-Up Needed", "Responded", "Meeting Set", "Quoted", "Won", "Lost", "No Response"])
        filtered_o = [o for o in st.session_state.outreach if o["status"] in o_status_filter] if o_status_filter else st.session_state.outreach

        df = pd.DataFrame(filtered_o)
        display_cols = [c for c in ["entity", "type", "town", "contact", "email", "status", "services", "follow_up_date"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        # Pipeline summary
        st.divider()
        pipeline = {}
        for o in st.session_state.outreach:
            pipeline[o["status"]] = pipeline.get(o["status"], 0) + 1
        st.markdown("### Outreach Pipeline")
        for status, count in sorted(pipeline.items()):
            st.markdown(f"- **{status}**: {count}")
    else:
        st.info("No outreach logged yet.")

# ============================================================
# EMAIL SENDER
# ============================================================
elif page == "Email Sender":
    st.markdown("## Auto Email Sender")
    st.markdown("Queue cold outreach emails and send them with random delays (10-60 sec) to avoid spam filters.")

    # Email config
    email_config = load_json("email_config.json", {})

    with st.expander("Email Account Setup", expanded=not bool(email_config.get("email"))):
        with st.form("email_setup"):
            st.markdown("**Connect your email account to send outreach.**")
            st.markdown("For Gmail: Use an [App Password](https://myaccount.google.com/apppasswords), NOT your regular password.")
            es1, es2 = st.columns(2)
            with es1:
                e_provider = st.selectbox("Provider", ["gmail", "outlook", "yahoo", "custom"])
                e_email = st.text_input("Email Address", value=email_config.get("email", ""))
                e_password = st.text_input("App Password", type="password", value=email_config.get("password", ""))
            with es2:
                e_from_name = st.text_input("Your Name", value=email_config.get("from_name", ""))
                e_company = st.text_input("Company Name", value=email_config.get("company", ""))
                e_phone = st.text_input("Your Phone", value=email_config.get("phone", ""))
            submitted = st.form_submit_button("Save Email Config", use_container_width=True)
            if submitted and e_email:
                email_config = {
                    "provider": e_provider, "email": e_email, "password": e_password,
                    "from_name": e_from_name, "company": e_company, "phone": e_phone
                }
                save_json("email_config.json", email_config)
                st.success("Email config saved!")
                st.rerun()

    if email_config.get("email"):
        st.success(f"Connected: **{email_config['email']}**")

    st.divider()

    # Queue emails from targets
    st.markdown("### Queue Emails from Target Database")
    st.markdown("Select targets that have email addresses and queue outreach emails.")

    # Template selection
    template_choice = st.selectbox("Email Template", [
        "Property Manager — Introduction",
        "Apartment Complex — Seasonal Services",
        "HOA/Condo Board — Annual Maintenance",
        "Shopping Center — Exterior Maintenance",
        "Municipality — Vendor Introduction",
        "School District — Summer Maintenance",
        "Car Dealership — Lot & Building",
        "Senior Living — Campus Maintenance",
        "Hotel — Exterior Services",
        "Custom Message",
    ])

    if template_choice == "Custom Message":
        custom_subject = st.text_input("Subject Line")
        custom_body = st.text_area("Email Body", height=300, placeholder="Write your email here. Use [Contact Name], [Property Name], [Company Name], [Your Name], [Phone] as placeholders.")
    else:
        custom_subject = ""
        custom_body = ""

    # Get targets with emails
    targets_with_email = [t for t in st.session_state.targets if t.get("email") and "@" in t.get("email", "")]
    all_outreach_with_email = [o for o in st.session_state.outreach if o.get("email") and "@" in o.get("email", "")]

    st.markdown(f"**{len(targets_with_email)} targets** and **{len(all_outreach_with_email)} outreach contacts** have email addresses.")

    # Manual email queue
    st.markdown("### Add to Queue Manually")
    with st.form("manual_queue", clear_on_submit=True):
        mq1, mq2 = st.columns(2)
        with mq1:
            mq_email = st.text_input("Recipient Email")
            mq_name = st.text_input("Recipient Name")
        with mq2:
            mq_entity = st.text_input("Entity / Property Name")
            mq_subject = st.text_input("Subject (or leave blank for template)")

        submitted = st.form_submit_button("Add to Queue", use_container_width=True)
        if submitted and mq_email:
            queue = load_json("email_queue.json", [])

            # Build email from template
            company = email_config.get("company", "[Your Company Name]")
            from_name = email_config.get("from_name", "[Your Name]")
            phone = email_config.get("phone", "[Phone]")

            # Simple template bodies
            template_bodies = {
                "Property Manager — Introduction": f"Hi {mq_name or '[Contact Name]'},\n\nI'm reaching out from {company}. We provide commercial power washing, window cleaning, and gutter maintenance for properties across the northern suburbs of Chicago.\n\nWe currently service commercial properties in the area and would love the opportunity to provide a competitive quote for your portfolio.\n\nOur services include:\n- Building exterior power washing\n- Window cleaning (interior & exterior)\n- Gutter cleaning & maintenance\n- Parking lot & sidewalk cleaning\n- Graffiti removal\n\nWould you be open to a quick call this week? I'd also be happy to provide a free on-site assessment.\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "Apartment Complex — Seasonal Services": f"Hi {mq_name or '[Contact Name]'},\n\nSpring is around the corner and I wanted to reach out about exterior maintenance for {mq_entity or 'your property'}.\n\nWe specialize in commercial power washing for multi-unit residential properties across the northern suburbs.\n\nFor apartment communities, we typically handle:\n- Building exterior washing\n- Parking garage & lot cleaning\n- Sidewalk & entryway power washing\n- Window cleaning\n- Gutter cleaning & downspout flushing\n\nWe offer annual maintenance contracts with preferred pricing.\n\nCan I put together a no-obligation quote? Happy to do a free walk-through.\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "HOA/Condo Board — Annual Maintenance": f"Dear {mq_name or 'Board President'},\n\nI'd like to introduce {company} as a resource for {mq_entity or 'your community'}'s exterior building maintenance needs.\n\nWe work with several HOA and condo communities in the area providing:\n- Annual building power washing\n- Window cleaning schedules\n- Gutter cleaning (spring & fall)\n- Common area maintenance\n- Concrete & walkway cleaning\n\nI'd be happy to attend your next board meeting to present our services, or put together a written proposal based on a quick property walk-through.\n\nWould either option work for you?\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "Municipality — Vendor Introduction": f"Dear {mq_name or 'Facilities Director'},\n\nI'd like to introduce {company} as a qualified vendor for exterior building maintenance services.\n\nWe specialize in:\n- Commercial power washing\n- Window cleaning\n- Gutter cleaning & maintenance\n- Concrete restoration cleaning\n\nWe are fully insured, environmentally compliant (IL EPA water containment protocols), and experienced in government contracts.\n\nI would like to register on your approved vendor list and learn about upcoming maintenance contracts.\n\nCould you point me to the right person or process for vendor registration?\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "Shopping Center — Exterior Maintenance": f"Hi {mq_name or '[Contact Name]'},\n\nI'm reaching out regarding exterior maintenance for {mq_entity or 'your property'}.\n\nClean storefronts and walkways directly impact foot traffic. We provide:\n- Storefront & facade power washing\n- Window cleaning\n- Sidewalk & parking lot cleaning\n- Dumpster pad cleaning\n- Gum & stain removal\n- Graffiti removal\n\nWe offer flexible scheduling with zero disruption to tenants.\n\nWhen would be a good time to walk the property?\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "School District — Summer Maintenance": f"Dear {mq_name or 'Facilities Director'},\n\nSummer break is the ideal window for exterior building maintenance. I'd like to offer {company}'s services to {mq_entity or 'your district'}.\n\nWe can handle:\n- Full building exterior power washing\n- Window cleaning (all floors)\n- Gutter cleaning & inspection\n- Sidewalk & entryway cleaning\n- Playground equipment cleaning\n\nWe work on compressed summer timelines. Is there an upcoming bid cycle, or would you accept a proposal?\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "Car Dealership — Lot & Building": f"Hi {mq_name or '[Contact Name]'},\n\nFirst impressions matter in car sales. I'd like to offer {company}'s exterior cleaning services for {mq_entity or 'your dealership'}.\n\nWe provide:\n- Showroom & building exterior power washing\n- Lot and sidewalk cleaning\n- Service bay area cleaning\n- Window cleaning\n- Sign and canopy cleaning\n\nWe offer early morning scheduling with no disruption during business hours.\n\nCan I provide a quick quote?\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "Senior Living — Campus Maintenance": f"Dear {mq_name or 'Facilities Director'},\n\nCurb appeal and safety are critical for senior living communities. I'd like to offer {company}'s exterior cleaning services for {mq_entity or 'your facility'}.\n\nWe specialize in:\n- Building exterior power washing\n- Window cleaning\n- Walkway and patio cleaning (slip prevention)\n- Gutter cleaning & maintenance\n\nWe understand senior community needs - quiet operation, safety barriers, and flexible scheduling.\n\nWould you be open to a walk-through?\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
                "Hotel — Exterior Services": f"Hi {mq_name or '[Contact Name]'},\n\nGuest experience starts at the curb. I'd like to offer exterior cleaning for {mq_entity or 'your hotel'}.\n\nWe provide:\n- Building facade power washing\n- Window cleaning\n- Parking structure cleaning\n- Pool deck and patio cleaning\n- Dumpster area cleaning\n\nWe offer overnight scheduling with zero guest disruption.\n\nCan I provide a competitive quote?\n\nBest regards,\n{from_name}\n{phone}\n{email_config.get('email', '')}",
            }

            if template_choice == "Custom Message":
                body = custom_body
                subject = custom_subject or f"Commercial Exterior Maintenance — {company}"
            else:
                body = template_bodies.get(template_choice, template_bodies["Property Manager — Introduction"])
                subject_map = {
                    "Property Manager — Introduction": f"Commercial Exterior Maintenance — Northern Suburbs",
                    "Apartment Complex — Seasonal Services": f"Spring Exterior Cleaning — {mq_entity or 'Your Property'}",
                    "HOA/Condo Board — Annual Maintenance": f"Exterior Maintenance Proposal for {mq_entity or 'Your Community'}",
                    "Municipality — Vendor Introduction": f"Vendor Introduction — Exterior Building Maintenance Services",
                    "Shopping Center — Exterior Maintenance": f"Exterior Cleaning Services — {mq_entity or 'Your Property'}",
                    "School District — Summer Maintenance": f"Summer Building Maintenance — {mq_entity or 'Your District'}",
                    "Car Dealership — Lot & Building": f"Dealership Exterior Cleaning — {mq_entity or 'Your Dealership'}",
                    "Senior Living — Campus Maintenance": f"Exterior Maintenance Services — {mq_entity or 'Your Facility'}",
                    "Hotel — Exterior Services": f"Exterior Maintenance — {mq_entity or 'Your Hotel'}",
                }
                subject = mq_subject or subject_map.get(template_choice, f"Commercial Exterior Maintenance — {company}")

            queue.append({
                "to_email": mq_email,
                "to_name": mq_name,
                "entity": mq_entity,
                "subject": subject,
                "body": body,
                "status": "queued",
                "queued_at": datetime.now().isoformat()
            })
            save_json("email_queue.json", queue)
            st.success(f"Added to queue: {mq_email}")
            st.rerun()

    # Show queue
    st.divider()
    st.markdown("### Email Queue")
    queue = load_json("email_queue.json", [])
    if queue:
        queued = [e for e in queue if e["status"] == "queued"]
        sent = [e for e in queue if e["status"] == "sent"]
        errors = [e for e in queue if e["status"] == "error"]

        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            st.metric("Queued", len(queued))
        with qc2:
            st.metric("Sent", len(sent))
        with qc3:
            st.metric("Errors", len(errors))

        if queued:
            st.markdown("**Pending Emails:**")
            for q in queued:
                st.markdown(f"- **{q['entity']}** — {q['to_email']} — *{q['subject']}*")

        if sent:
            with st.expander(f"Sent Emails ({len(sent)})", expanded=False):
                for s in reversed(sent[-20:]):
                    st.markdown(f"- **{s.get('entity', '')}** — {s['to_email']} — {s.get('sent_at', '')}")

        st.divider()
        st.markdown("### How to Send")
        st.code("python3 ~/Desktop/commercial-project-identification/email_sender.py send", language="bash")
        st.markdown("This sends all queued emails with **random 10-60 second delays** between each one.")
        st.markdown("")
        st.markdown("**First time? Set up your email:**")
        st.code("python3 ~/Desktop/commercial-project-identification/email_sender.py setup", language="bash")

        if st.button("Clear Queue", type="secondary"):
            save_json("email_queue.json", [])
            st.rerun()
    else:
        st.info("No emails queued. Use the form above to add recipients.")

# ============================================================
# PROPOSAL GENERATOR
# ============================================================
elif page == "Proposal Generator":
    st.markdown("## Proposal Generator")
    st.markdown("Generate a professional proposal in seconds. Fill in the details and download a ready-to-send document.")

    company_config = load_json("email_config.json", {})

    st.markdown("### Company Info")
    with st.expander("Your Company Details (saved for future proposals)", expanded=not bool(company_config.get("company"))):
        with st.form("company_info"):
            ci1, ci2 = st.columns(2)
            with ci1:
                co_name = st.text_input("Company Name", value=company_config.get("company", ""))
                co_contact = st.text_input("Your Name", value=company_config.get("from_name", ""))
                co_phone = st.text_input("Phone", value=company_config.get("phone", ""))
                co_email = st.text_input("Email", value=company_config.get("email", ""))
            with ci2:
                co_address = st.text_input("Business Address", value=company_config.get("address", ""))
                co_insurance = st.text_input("Insurance Coverage", value=company_config.get("insurance", "$2,000,000 General Liability / $1,000,000 Workers' Comp"))
                co_license = st.text_input("License #", value=company_config.get("license", ""))
                co_website = st.text_input("Website", value=company_config.get("website", ""))
            submitted = st.form_submit_button("Save Company Info", use_container_width=True)
            if submitted:
                company_config.update({
                    "company": co_name, "from_name": co_contact, "phone": co_phone,
                    "email": co_email, "address": co_address, "insurance": co_insurance,
                    "license": co_license, "website": co_website
                })
                save_json("email_config.json", company_config)
                st.success("Saved!")
                st.rerun()

    st.divider()
    st.markdown("### Generate Proposal")

    with st.form("generate_proposal"):
        st.markdown("**Client Details**")
        pc1, pc2 = st.columns(2)
        with pc1:
            p_client = st.text_input("Client Name / Entity")
            p_contact = st.text_input("Attention (Contact Name)")
            p_address = st.text_input("Property Address")
            p_type = st.selectbox("Property Type", [
                "Municipal Building", "School Campus", "Park District Facility",
                "HOA / Condo Community", "Apartment Complex", "Shopping Center",
                "Office Building", "Industrial Facility", "Car Dealership",
                "Hotel", "Senior Living", "Church Campus", "Medical Facility", "Other"
            ])
        with pc2:
            p_date = st.date_input("Proposal Date", value=date.today())
            p_valid = st.text_input("Proposal Valid For", value="30 days")
            p_start = st.text_input("Proposed Start Date", value="Upon Approval")
            p_contract_type = st.selectbox("Contract Type", [
                "One-Time Service", "Annual Maintenance Contract",
                "Multi-Year Contract (2 years)", "Multi-Year Contract (3 years)",
                "Seasonal Package (Spring + Fall)"
            ])

        st.markdown("**Services & Pricing**")
        st.markdown("Add each service line item:")

        services_data = []
        for i in range(8):
            sc1, sc2, sc3 = st.columns([3, 1, 1])
            with sc1:
                svc = st.text_input(f"Service {i+1}", key=f"svc_{i}",
                    placeholder="e.g., Building exterior power washing - 3 buildings")
            with sc2:
                qty = st.text_input(f"Frequency", key=f"qty_{i}", placeholder="e.g., 2x/year")
            with sc3:
                price = st.number_input(f"Price ($)", key=f"price_{i}", min_value=0, value=0, step=100)
            if svc and price > 0:
                services_data.append({"service": svc, "frequency": qty, "price": price})

        st.markdown("**Additional Terms**")
        p_notes = st.text_area("Special Notes / Scope Details", height=100,
            placeholder="Include specific details about the property, access requirements, scheduling preferences, etc.")
        p_warranty = st.text_input("Satisfaction Guarantee", value="100% satisfaction guarantee. If you're not happy with any service, we'll re-do it at no charge.")
        p_payment = st.selectbox("Payment Terms", ["Net 30", "Net 15", "Due Upon Completion", "50% Deposit / 50% Completion"])
        p_escalator = st.text_input("Annual Price Escalator (for multi-year)", value="3% annual increase")

        submitted = st.form_submit_button("Generate Proposal", use_container_width=True, type="primary")

        if submitted and p_client and services_data:
            total = sum(s["price"] for s in services_data)

            # Annual value for multi-year
            annual_note = ""
            if "Annual" in p_contract_type or "Multi-Year" in p_contract_type:
                annual_note = f"\n\nANNUAL CONTRACT VALUE: ${total:,.2f}/year"
                if "2 year" in p_contract_type:
                    annual_note += f"\nTOTAL 2-YEAR VALUE: ${total * 2:,.2f} (with {p_escalator})"
                elif "3 year" in p_contract_type:
                    annual_note += f"\nTOTAL 3-YEAR VALUE: ${total * 3:,.2f} (with {p_escalator})"
            elif "Seasonal" in p_contract_type:
                annual_note = f"\n\nSEASONAL PACKAGE VALUE: ${total:,.2f}"

            # Build service table
            svc_lines = ""
            for j, s in enumerate(services_data, 1):
                svc_lines += f"  {j}. {s['service']}"
                if s['frequency']:
                    svc_lines += f" ({s['frequency']})"
                svc_lines += f" — ${s['price']:,.2f}\n"

            proposal = f"""
{'='*60}
COMMERCIAL EXTERIOR MAINTENANCE PROPOSAL
{'='*60}

FROM:
  {company_config.get('company', '[Your Company]')}
  {company_config.get('address', '')}
  {company_config.get('from_name', '')}
  {company_config.get('phone', '')} | {company_config.get('email', '')}
  {company_config.get('website', '')}

TO:
  {p_client}
  Attn: {p_contact}
  {p_address}

DATE: {p_date.strftime('%B %d, %Y')}
PROPOSAL VALID: {p_valid}
CONTRACT TYPE: {p_contract_type}

{'='*60}
SCOPE OF SERVICES
{'='*60}

{svc_lines}
{'-'*40}
  TOTAL: ${total:,.2f}
{annual_note}

PROPOSED START DATE: {p_start}
PAYMENT TERMS: {p_payment}
{f'ANNUAL ESCALATOR: {p_escalator}' if 'Multi-Year' in p_contract_type else ''}

{'='*60}
PROPERTY DETAILS & NOTES
{'='*60}

Property Type: {p_type}
{p_notes if p_notes else 'Standard scope as described above.'}

{'='*60}
WHAT'S INCLUDED
{'='*60}

- All labor, equipment, and cleaning materials
- Full environmental compliance (IL EPA water containment)
- Before and after photo documentation for every service visit
- Flexible scheduling (early morning, evening, or weekend options)
- Dedicated account manager for your property
- 24-hour emergency service availability

{'='*60}
INSURANCE & QUALIFICATIONS
{'='*60}

- General Liability: {company_config.get('insurance', '$2,000,000')}
- Workers' Compensation: Fully compliant with Illinois requirements
- Commercial Auto: Full coverage on all vehicles
- Bonded and insured for commercial work
- IL Business Registration: {company_config.get('license', 'On file')}
- Environmental compliance: IL EPA certified water containment protocols

{'='*60}
SATISFACTION GUARANTEE
{'='*60}

{p_warranty}

{'='*60}
ACCEPTANCE
{'='*60}

By signing below, you authorize {company_config.get('company', '[Company]')} to
perform the services described above under the terms outlined.

Client Signature: _________________________ Date: ___________

Print Name: _________________________

Title: _________________________


{company_config.get('company', '[Company]')} Representative:

Signature: _________________________ Date: ___________

{company_config.get('from_name', '')}
{company_config.get('phone', '')}
{company_config.get('email', '')}
"""
            st.markdown("### Generated Proposal")
            st.code(proposal, language=None)

            # Download
            st.download_button(
                "Download Proposal (.txt)",
                proposal,
                f"proposal_{p_client.replace(' ', '_')}_{p_date.isoformat()}.txt",
                "text/plain",
                use_container_width=True
            )

            # Save to proposals log
            proposals = load_json("proposals.json", [])
            proposals.append({
                "client": p_client, "contact": p_contact, "address": p_address,
                "type": p_type, "contract_type": p_contract_type,
                "total": total, "date": p_date.isoformat(),
                "services": services_data, "status": "Sent"
            })
            save_json("proposals.json", proposals)

    # Proposals history
    proposals = load_json("proposals.json", [])
    if proposals:
        st.divider()
        st.markdown("### Proposal History")
        for p in reversed(proposals[-10:]):
            st.markdown(f"- **{p['client']}** — ${p['total']:,.0f} — {p['contract_type']} — {p['date']}")

# ============================================================
# SERVICE PACKAGES
# ============================================================
elif page == "Service Packages":
    st.markdown("## Service Packages")
    st.markdown("Pre-built bundles that increase contract value and lock in recurring revenue.")

    st.markdown("### Annual Maintenance Packages")
    st.markdown("These are designed to present to HOAs, property managers, and commercial buildings as turnkey annual contracts.")

    packages = {
        "Essential Clean": {
            "description": "Basic annual exterior maintenance",
            "services": [
                ("Building exterior power wash", "1x/year (spring)", "$0.25-0.50/sq ft"),
                ("Gutter cleaning & flush", "2x/year (spring + fall)", "$1.00-1.50/lin ft"),
                ("Sidewalk & entryway wash", "1x/year", "$0.30-0.60/sq ft"),
            ],
            "ideal_for": "Small HOAs, churches, single commercial buildings",
            "example_price": "$3,000 - $8,000/year",
            "discount": "10% vs one-time pricing"
        },
        "Professional Maintenance": {
            "description": "Comprehensive exterior care package",
            "services": [
                ("Building exterior power wash", "2x/year (spring + fall)", "$0.20-0.40/sq ft"),
                ("Window cleaning (all floors)", "2x/year", "$8-15/pane"),
                ("Gutter cleaning & flush", "2x/year", "$0.75-1.25/lin ft"),
                ("Sidewalk & parking lot cleaning", "2x/year", "$0.15-0.35/sq ft"),
                ("Dumpster pad cleaning", "4x/year (quarterly)", "$75-125/pad"),
            ],
            "ideal_for": "HOAs 50+ units, apartment complexes, office buildings, shopping centers",
            "example_price": "$8,000 - $25,000/year",
            "discount": "15% vs one-time pricing"
        },
        "Premium Full-Service": {
            "description": "Everything, top to bottom, year-round",
            "services": [
                ("Building exterior power wash", "3x/year", "$0.18-0.35/sq ft"),
                ("Window cleaning (all floors)", "4x/year (quarterly)", "$6-12/pane"),
                ("Gutter cleaning & flush", "2x/year", "$0.75-1.00/lin ft"),
                ("Sidewalk, parking lot & garage cleaning", "4x/year", "$0.10-0.25/sq ft"),
                ("Dumpster pad cleaning", "Monthly", "$50-100/pad"),
                ("Graffiti removal", "As needed (24-hour response)", "Included"),
                ("Roof cleaning / soft wash", "1x/year", "$0.25-0.50/sq ft"),
                ("Sign & canopy cleaning", "2x/year", "$150-300/sign"),
            ],
            "ideal_for": "Large HOAs, multi-building complexes, shopping centers, corporate campuses, school districts",
            "example_price": "$25,000 - $75,000+/year",
            "discount": "20% vs one-time pricing + priority scheduling"
        },
    }

    for pkg_name, pkg in packages.items():
        with st.expander(f"**{pkg_name}** — {pkg['description']}", expanded=True):
            st.markdown(f"**Ideal for:** {pkg['ideal_for']}")
            st.markdown(f"**Example annual price range:** {pkg['example_price']}")
            st.markdown(f"**Discount vs one-time:** {pkg['discount']}")
            st.markdown("")
            st.markdown("| Service | Frequency | Rate |")
            st.markdown("|---------|-----------|------|")
            for svc, freq, rate in pkg["services"]:
                st.markdown(f"| {svc} | {freq} | {rate} |")

    st.divider()
    st.markdown("### Seasonal Packages")

    seasonal = {
        "Spring Clean Package": {
            "timing": "March - May",
            "services": ["Full building exterior wash", "Window cleaning", "Gutter cleaning & flush",
                        "Sidewalk & parking lot cleaning", "Winter salt/stain removal"],
            "pitch": "Get your property looking great after winter. Schedule before peak season.",
        },
        "Summer Shine Package": {
            "timing": "June - August",
            "services": ["School building summer wash (while empty)", "Pool deck & patio cleaning",
                        "Parking structure cleaning", "Graffiti removal", "Playground equipment cleaning"],
            "pitch": "Perfect for schools and park districts during summer break.",
        },
        "Fall Prep Package": {
            "timing": "September - November",
            "services": ["Gutter cleaning & downspout flush", "Building exterior touch-up wash",
                        "Leaf debris removal from walkways", "Window cleaning before winter"],
            "pitch": "Protect your property before winter. Prevent gutter damage and ice dams.",
        },
    }

    for pkg_name, pkg in seasonal.items():
        with st.expander(f"**{pkg_name}** ({pkg['timing']})"):
            st.markdown(f"**Pitch:** *{pkg['pitch']}*")
            st.markdown("**Services included:**")
            for svc in pkg["services"]:
                st.markdown(f"- {svc}")

    st.divider()
    st.markdown("### Multi-Year Contract Structure")
    st.markdown("""
    **Why push multi-year contracts?**
    - Locks in recurring revenue
    - Client gets rate protection (fixed price with small escalator)
    - Reduces your sales effort — one close, 2-3 years of revenue
    - Shows stability to other prospects ("we have multi-year contracts with...")

    **Recommended structure:**
    - **Year 1**: Full price
    - **Year 2**: 3% increase
    - **Year 3**: 3% increase
    - **Early termination**: 60-day written notice
    - **Annual review**: Meet to discuss scope adjustments

    **How to present it:**
    > "We offer a 3-year maintenance agreement that locks in your pricing with just a 3% annual adjustment.
    > Most of our clients prefer this because it simplifies budgeting and guarantees priority scheduling.
    > You can cancel with 60 days notice, so there's no risk."

    **This works especially well for:**
    - HOA boards (they budget annually and hate price surprises)
    - Property managers (they want set-it-and-forget-it vendors)
    - Municipalities (multi-year contracts reduce procurement overhead)
    - School districts (budget predictability is everything)
    """)

    st.divider()
    st.markdown("### Quick Quote Calculator")
    st.markdown("Estimate a project price quickly.")

    qq1, qq2 = st.columns(2)
    with qq1:
        q_sqft = st.number_input("Building sq ft (exterior)", min_value=0, value=0, step=1000)
        q_windows = st.number_input("Number of windows/panes", min_value=0, value=0, step=10)
        q_gutters = st.number_input("Linear feet of gutters", min_value=0, value=0, step=50)
    with qq2:
        q_parking = st.number_input("Parking lot sq ft", min_value=0, value=0, step=1000)
        q_dumpsters = st.number_input("Dumpster pads", min_value=0, value=0, step=1)
        q_stories = st.selectbox("Stories", [1, 2, 3, 4, 5])

    story_mult = {1: 1.0, 2: 1.15, 3: 1.3, 4: 1.5, 5: 1.75}
    mult = story_mult.get(q_stories, 1.0)

    if st.button("Calculate Estimate", type="primary"):
        pw_low = q_sqft * 0.20 * mult
        pw_high = q_sqft * 0.50 * mult
        win_low = q_windows * 8 * mult
        win_high = q_windows * 15 * mult
        gut_low = q_gutters * 0.75 * mult
        gut_high = q_gutters * 1.50 * mult
        park_low = q_parking * 0.05
        park_high = q_parking * 0.15
        dump_low = q_dumpsters * 75
        dump_high = q_dumpsters * 125

        total_low = pw_low + win_low + gut_low + park_low + dump_low
        total_high = pw_high + win_high + gut_high + park_high + dump_high

        st.markdown("### Estimate")
        st.markdown(f"| Service | Low | High |")
        st.markdown(f"|---------|-----|------|")
        if q_sqft > 0:
            st.markdown(f"| Power Washing ({q_sqft:,} sq ft) | ${pw_low:,.0f} | ${pw_high:,.0f} |")
        if q_windows > 0:
            st.markdown(f"| Window Cleaning ({q_windows} panes) | ${win_low:,.0f} | ${win_high:,.0f} |")
        if q_gutters > 0:
            st.markdown(f"| Gutter Cleaning ({q_gutters} lin ft) | ${gut_low:,.0f} | ${gut_high:,.0f} |")
        if q_parking > 0:
            st.markdown(f"| Parking Lot ({q_parking:,} sq ft) | ${park_low:,.0f} | ${park_high:,.0f} |")
        if q_dumpsters > 0:
            st.markdown(f"| Dumpster Pads ({q_dumpsters}) | ${dump_low:,.0f} | ${dump_high:,.0f} |")
        st.markdown(f"| **TOTAL (one-time)** | **${total_low:,.0f}** | **${total_high:,.0f}** |")
        st.markdown(f"| **Annual Contract (2x/yr, 15% discount)** | **${total_low * 2 * 0.85:,.0f}** | **${total_high * 2 * 0.85:,.0f}** |")

# ============================================================
# BID PACKAGE
# ============================================================
elif page == "Bid Package":
    st.markdown("## Bid Package — Document Prep")
    st.markdown("Pre-assemble everything you need so you can respond to bids in hours, not days.")

    st.markdown("""
    ### Your Advantage as a National Brand

    Being an established national company gives you a **significant edge**:

    - **Insurance**: You likely already carry $2M-$5M GL — many small competitors can't match this
    - **References**: National portfolio = stronger bid scoring (20-30% of evaluation)
    - **Financial Stability**: Lower risk perception = municipalities prefer you
    - **Bonding Capacity**: Easier to get bid bonds and performance bonds
    - **Scoring Bonus**: Some IL municipalities give 5-10% preference to established businesses
    - **Vendor List Fast-Track**: Well-documented companies get approved faster

    ### How to Minimize Paperwork

    **Build ONE universal bid package** that covers 90%+ of what every municipality asks for:
    """)

    # Document checklist
    st.markdown("### Universal Bid Package Checklist")

    bid_docs = load_json("bid_docs.json", {
        "General Liability Insurance Certificate": {"status": "Not Started", "notes": "Need $1M/$2M minimum. $5M preferred. Add each entity as Additional Insured when bidding."},
        "Workers' Compensation Certificate": {"status": "Not Started", "notes": "Mandatory in IL with 1+ employees. No exceptions."},
        "Commercial Auto Insurance Certificate": {"status": "Not Started", "notes": "Required for any business vehicles."},
        "Umbrella/Excess Liability Certificate": {"status": "Not Started", "notes": "$1M-$5M. Required for larger contracts."},
        "W-9 Form": {"status": "Not Started", "notes": "Keep a current signed copy ready."},
        "Illinois Business Registration": {"status": "Not Started", "notes": "IL Secretary of State registration."},
        "Company Capabilities Statement": {"status": "Not Started", "notes": "1-2 page overview: services, equipment, coverage area, insurance summary, certifications."},
        "Reference List (5+ Commercial)": {"status": "Not Started", "notes": "Include municipality/government refs if you have them. Name, title, phone, email, description of work."},
        "Before & After Photo Portfolio": {"status": "Not Started", "notes": "10-15 commercial jobs. Buildings, parking lots, storefronts."},
        "Safety Plan / OSHA Documentation": {"status": "Not Started", "notes": "Written safety program. OSHA 10/30 certs if you have them."},
        "Environmental Compliance Plan": {"status": "Not Started", "notes": "Water containment/recovery procedures for power washing. IL EPA compliance."},
        "Equipment List": {"status": "Not Started", "notes": "Major equipment with specs. Shows you're properly equipped."},
        "PWNA Certification": {"status": "Not Started", "notes": "Optional but strengthens bids. Power Washers of North America."},
        "MBE/WBE/VBE Certification": {"status": "Not Started", "notes": "If applicable. Some bids give 5-10% preference."},
        "Bid Bond Template": {"status": "Not Started", "notes": "Have your bonding company pre-approve a template. Usually 5-10% of bid."},
        "Rate Sheet / Pricing Schedule": {"status": "Not Started", "notes": "Standard rates by service. Customize per bid but have baseline ready."},
    })

    completed = 0
    for doc_name, doc_info in bid_docs.items():
        dc1, dc2, dc3 = st.columns([4, 2, 3])
        with dc1:
            st.markdown(f"**{doc_name}**")
            st.caption(doc_info["notes"])
        with dc2:
            new_status = st.selectbox("Status",
                                     ["Not Started", "In Progress", "Ready"],
                                     index=["Not Started", "In Progress", "Ready"].index(doc_info["status"]),
                                     key=f"doc_{doc_name}", label_visibility="collapsed")
            if new_status != doc_info["status"]:
                bid_docs[doc_name]["status"] = new_status
                save_json("bid_docs.json", bid_docs)
        with dc3:
            if doc_info["status"] == "Ready":
                st.markdown('<span class="reg-done">READY</span>', unsafe_allow_html=True)
                completed += 1
            elif doc_info["status"] == "In Progress":
                st.markdown('<span class="reg-pending">IN PROGRESS</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="reg-not">NOT STARTED</span>', unsafe_allow_html=True)
        st.divider()

    total = len(bid_docs)
    pct = int(completed / total * 100) if total > 0 else 0
    st.markdown(f"### Bid Package: {completed}/{total} documents ready ({pct}%)")
    st.progress(pct / 100)

    st.markdown("""
    ### Streamlining the Process

    **For Public Entities (Municipalities, Schools, Parks):**
    1. Get your bid package to 100% ready
    2. Register on all procurement portals (see Vendor Registration page)
    3. When a bid drops, you just customize pricing and add the entity as Additional Insured on your insurance cert (your agent can do this same-day)
    4. Submit through the portal — most of your docs are already uploaded

    **For Private Entities (HOAs, Apartments, Property Managers):**
    1. Send cold outreach email (see Email Sender page)
    2. Wait for response — NO paperwork until they're interested
    3. When they respond, send your Capabilities Statement + Insurance Cert
    4. Do a free walk-through and submit a simple proposal
    5. Paperwork only happens after they say yes

    **Bottom Line:** You don't need to do ANY paperwork until:
    - A public bid you want to respond to drops (then it's mostly just pricing)
    - A private entity responds to your outreach (then it's just a simple proposal)
    """)

    st.markdown("""
    ### Illinois Municipal Purchasing Thresholds

    Under Illinois law, municipalities have different requirements based on contract size:

    | Amount | Requirement |
    |--------|-------------|
    | **Under $1,000** | Can purchase directly, no quotes needed |
    | **$1,000 - $25,000** | Informal quotes (usually 3 quotes) |
    | **$25,000 - $40,000** | Written quotes, may require board approval |
    | **Over $40,000** | Formal sealed bid / RFP process required |

    **This means:** For many exterior cleaning jobs under $25K, a municipality can just hire you directly. No formal bid needed. That's why cold outreach to facilities directors works — they can sign off on smaller jobs themselves.
    """)

# ============================================================
# COMPANY PROFILE
# ============================================================
elif page == "Company Profile":
    st.markdown("## Company Profile — Fill Once, Use Everywhere")
    st.markdown("Enter your company info here ONE TIME. It auto-fills into proposals, emails, vendor forms, and bid responses.")

    profile = load_json("company_profile.json", {})

    with st.form("company_profile_form"):
        st.markdown("### Business Information")
        bp1, bp2 = st.columns(2)
        with bp1:
            bp_company = st.text_input("Company Legal Name", value=profile.get("company_name", ""))
            bp_dba = st.text_input("DBA (if different)", value=profile.get("dba", ""))
            bp_address = st.text_input("Business Address", value=profile.get("address", ""))
            bp_city = st.text_input("City", value=profile.get("city", ""))
            bp_state = st.text_input("State", value=profile.get("state", "IL"))
            bp_zip = st.text_input("ZIP", value=profile.get("zip", ""))
        with bp2:
            bp_phone = st.text_input("Main Phone", value=profile.get("phone", ""))
            bp_fax = st.text_input("Fax (if any)", value=profile.get("fax", ""))
            bp_website = st.text_input("Website", value=profile.get("website", ""))
            bp_email = st.text_input("Main Business Email", value=profile.get("email", ""))
            bp_fein = st.text_input("FEIN / Tax ID", value=profile.get("fein", ""))
            bp_duns = st.text_input("DUNS Number (if any)", value=profile.get("duns", ""))

        st.markdown("### Primary Contact")
        pc1, pc2 = st.columns(2)
        with pc1:
            bp_contact_name = st.text_input("Contact Name", value=profile.get("contact_name", ""))
            bp_contact_title = st.text_input("Title", value=profile.get("contact_title", ""))
        with pc2:
            bp_contact_phone = st.text_input("Direct Phone", value=profile.get("contact_phone", ""))
            bp_contact_email = st.text_input("Direct Email", value=profile.get("contact_email", ""))

        st.markdown("### Business Details")
        bd1, bd2 = st.columns(2)
        with bd1:
            bp_entity_type = st.selectbox("Entity Type", ["LLC", "Corporation", "S-Corp", "Sole Proprietor", "Partnership", "Other"],
                                         index=["LLC", "Corporation", "S-Corp", "Sole Proprietor", "Partnership", "Other"].index(profile.get("entity_type", "LLC")))
            bp_state_inc = st.text_input("State of Incorporation", value=profile.get("state_incorporated", "IL"))
            bp_year_est = st.text_input("Year Established", value=profile.get("year_established", ""))
            bp_employees = st.text_input("Number of Employees", value=profile.get("employees", ""))
        with bd2:
            bp_naics = st.text_input("NAICS Code", value=profile.get("naics", "561790"))
            bp_sic = st.text_input("SIC Code (if known)", value=profile.get("sic", ""))
            bp_annual_rev = st.text_input("Annual Revenue Range", value=profile.get("annual_revenue", ""))
            bp_service_area = st.text_input("Service Area", value=profile.get("service_area", "Northern Suburbs of Chicago — Cook County, Lake County"))

        st.markdown("### Insurance Information")
        ins1, ins2 = st.columns(2)
        with ins1:
            bp_gl_carrier = st.text_input("GL Insurance Carrier", value=profile.get("gl_carrier", ""))
            bp_gl_policy = st.text_input("GL Policy Number", value=profile.get("gl_policy", ""))
            bp_gl_limit = st.text_input("GL Per Occurrence Limit", value=profile.get("gl_limit", "$1,000,000"))
            bp_gl_aggregate = st.text_input("GL Aggregate Limit", value=profile.get("gl_aggregate", "$2,000,000"))
            bp_gl_expiration = st.text_input("GL Expiration Date", value=profile.get("gl_expiration", ""))
        with ins2:
            bp_wc_carrier = st.text_input("Workers' Comp Carrier", value=profile.get("wc_carrier", ""))
            bp_wc_policy = st.text_input("WC Policy Number", value=profile.get("wc_policy", ""))
            bp_wc_expiration = st.text_input("WC Expiration Date", value=profile.get("wc_expiration", ""))
            bp_auto_carrier = st.text_input("Auto Insurance Carrier", value=profile.get("auto_carrier", ""))
            bp_auto_policy = st.text_input("Auto Policy Number", value=profile.get("auto_policy", ""))

        st.markdown("### Umbrella / Excess Liability")
        um1, um2 = st.columns(2)
        with um1:
            bp_umbrella_carrier = st.text_input("Umbrella Carrier", value=profile.get("umbrella_carrier", ""))
            bp_umbrella_limit = st.text_input("Umbrella Limit", value=profile.get("umbrella_limit", ""))
        with um2:
            bp_umbrella_policy = st.text_input("Umbrella Policy Number", value=profile.get("umbrella_policy", ""))
            bp_umbrella_expiration = st.text_input("Umbrella Expiration", value=profile.get("umbrella_expiration", ""))

        st.markdown("### Certifications & Licenses")
        cl1, cl2 = st.columns(2)
        with cl1:
            bp_il_reg = st.text_input("IL Secretary of State Registration #", value=profile.get("il_registration", ""))
            bp_pwna = st.text_input("PWNA Certification(s)", value=profile.get("pwna_cert", ""))
            bp_osha = st.text_input("OSHA Certification(s)", value=profile.get("osha_cert", ""))
        with cl2:
            bp_epa = st.text_input("EPA Lead-Safe Cert #", value=profile.get("epa_cert", ""))
            bp_mbe = st.text_input("MBE/WBE/VBE Certification", value=profile.get("mbe_cert", ""))
            bp_other_cert = st.text_input("Other Certifications", value=profile.get("other_certs", ""))

        st.markdown("### Services Offered")
        bp_services = st.text_area("List of Services", value=profile.get("services_description",
            "Commercial Power Washing, Window Cleaning, Gutter Cleaning & Maintenance, Roof Soft Washing, Concrete & Parking Lot Cleaning, Graffiti Removal, Fleet Washing, Building Exterior Maintenance"), height=100)

        st.markdown("### References (Top 3-5)")
        refs = profile.get("references", [{"name":"","company":"","phone":"","email":"","description":""}]*3)
        for i in range(3):
            ref = refs[i] if i < len(refs) else {"name":"","company":"","phone":"","email":"","description":""}
            st.markdown(f"**Reference {i+1}**")
            r1, r2, r3 = st.columns(3)
            with r1:
                st.text_input(f"Name", value=ref.get("name",""), key=f"ref_name_{i}")
                st.text_input(f"Company", value=ref.get("company",""), key=f"ref_company_{i}")
            with r2:
                st.text_input(f"Phone", value=ref.get("phone",""), key=f"ref_phone_{i}")
                st.text_input(f"Email", value=ref.get("email",""), key=f"ref_email_{i}")
            with r3:
                st.text_input(f"Description of Work", value=ref.get("description",""), key=f"ref_desc_{i}")

        st.markdown("### W-9 Information")
        w9_1, w9_2 = st.columns(2)
        with w9_1:
            bp_w9_name = st.text_input("Name (as shown on tax return)", value=profile.get("w9_name", ""))
            bp_w9_type = st.selectbox("Federal Tax Classification",
                ["LLC - C", "LLC - S", "LLC - P", "C Corporation", "S Corporation", "Sole Proprietor", "Partnership", "Trust/Estate"],
                index=0)
        with w9_2:
            bp_w9_address = st.text_input("W-9 Address", value=profile.get("w9_address", ""))
            bp_w9_city_state = st.text_input("W-9 City, State, ZIP", value=profile.get("w9_city_state", ""))

        submitted = st.form_submit_button("Save Company Profile", use_container_width=True, type="primary")

        if submitted:
            # Gather references
            saved_refs = []
            for i in range(3):
                saved_refs.append({
                    "name": st.session_state.get(f"ref_name_{i}", ""),
                    "company": st.session_state.get(f"ref_company_{i}", ""),
                    "phone": st.session_state.get(f"ref_phone_{i}", ""),
                    "email": st.session_state.get(f"ref_email_{i}", ""),
                    "description": st.session_state.get(f"ref_desc_{i}", ""),
                })

            profile = {
                "company_name": bp_company, "dba": bp_dba, "address": bp_address,
                "city": bp_city, "state": bp_state, "zip": bp_zip,
                "phone": bp_phone, "fax": bp_fax, "website": bp_website,
                "email": bp_email, "fein": bp_fein, "duns": bp_duns,
                "contact_name": bp_contact_name, "contact_title": bp_contact_title,
                "contact_phone": bp_contact_phone, "contact_email": bp_contact_email,
                "entity_type": bp_entity_type, "state_incorporated": bp_state_inc,
                "year_established": bp_year_est, "employees": bp_employees,
                "naics": bp_naics, "sic": bp_sic, "annual_revenue": bp_annual_rev,
                "service_area": bp_service_area,
                "gl_carrier": bp_gl_carrier, "gl_policy": bp_gl_policy,
                "gl_limit": bp_gl_limit, "gl_aggregate": bp_gl_aggregate,
                "gl_expiration": bp_gl_expiration,
                "wc_carrier": bp_wc_carrier, "wc_policy": bp_wc_policy,
                "wc_expiration": bp_wc_expiration,
                "auto_carrier": bp_auto_carrier, "auto_policy": bp_auto_policy,
                "umbrella_carrier": bp_umbrella_carrier, "umbrella_limit": bp_umbrella_limit,
                "umbrella_policy": bp_umbrella_policy, "umbrella_expiration": bp_umbrella_expiration,
                "il_registration": bp_il_reg, "pwna_cert": bp_pwna,
                "osha_cert": bp_osha, "epa_cert": bp_epa,
                "mbe_cert": bp_mbe, "other_certs": bp_other_cert,
                "services_description": bp_services,
                "references": saved_refs,
                "w9_name": bp_w9_name, "w9_type": bp_w9_type,
                "w9_address": bp_w9_address, "w9_city_state": bp_w9_city_state,
            }
            save_json("company_profile.json", profile)

            # Also update the email config so proposals/emails use this info
            email_config = load_json("email_config.json", {})
            email_config.update({
                "company": bp_company, "from_name": bp_contact_name,
                "phone": bp_contact_phone or bp_phone, "email": bp_contact_email or bp_email,
                "address": f"{bp_address}, {bp_city}, {bp_state} {bp_zip}",
                "insurance": f"{bp_gl_limit} per occurrence / {bp_gl_aggregate} aggregate",
                "website": bp_website,
            })
            save_json("email_config.json", email_config)
            st.success("Company Profile saved! This info now auto-fills into proposals, emails, and vendor forms.")
            st.rerun()

    # Show what's populated
    if profile.get("company_name"):
        st.divider()
        st.markdown("### Profile Status")
        sections = {
            "Business Info": bool(profile.get("company_name") and profile.get("address") and profile.get("fein")),
            "Primary Contact": bool(profile.get("contact_name") and profile.get("contact_email")),
            "Insurance - GL": bool(profile.get("gl_carrier") and profile.get("gl_policy")),
            "Insurance - WC": bool(profile.get("wc_carrier") and profile.get("wc_policy")),
            "Insurance - Auto": bool(profile.get("auto_carrier")),
            "Certifications": bool(profile.get("il_registration") or profile.get("pwna_cert")),
            "References": bool(profile.get("references") and profile["references"][0].get("name")),
            "W-9 Info": bool(profile.get("w9_name") and profile.get("fein")),
        }
        complete = sum(1 for v in sections.values() if v)
        total = len(sections)
        st.progress(complete / total)
        st.markdown(f"**{complete}/{total} sections complete**")
        for section, done in sections.items():
            icon = "done" if done else "not"
            css = "reg-done" if done else "reg-not"
            st.markdown(f'<span class="{css}">{"COMPLETE" if done else "INCOMPLETE"}</span> — {section}', unsafe_allow_html=True)

        st.divider()
        st.markdown("### Where This Info Is Used")
        st.markdown("""
        - **Proposals** → Company name, address, insurance, contact info auto-fill
        - **Cold Outreach Emails** → Your name, phone, email, company name auto-fill
        - **Vendor Registration Forms** → Copy/paste all required fields from here
        - **Bid Responses** → Insurance details, certifications, references ready to go
        - **W-9 Requests** → All tax info in one place
        """)

        # Generate a printable vendor info sheet
        st.markdown("### Download Vendor Info Sheet")
        st.markdown("Pre-filled sheet you can attach to any vendor application or bid response.")
        vendor_sheet = f"""
VENDOR INFORMATION SHEET
========================

COMPANY INFORMATION
Company Legal Name: {profile.get('company_name', '')}
DBA: {profile.get('dba', '')}
Address: {profile.get('address', '')}
City/State/ZIP: {profile.get('city', '')}, {profile.get('state', '')} {profile.get('zip', '')}
Phone: {profile.get('phone', '')}
Fax: {profile.get('fax', '')}
Website: {profile.get('website', '')}
Email: {profile.get('email', '')}
FEIN: {profile.get('fein', '')}
DUNS: {profile.get('duns', '')}
NAICS: {profile.get('naics', '')}
Entity Type: {profile.get('entity_type', '')}
State of Incorporation: {profile.get('state_incorporated', '')}
Year Established: {profile.get('year_established', '')}
Employees: {profile.get('employees', '')}
Annual Revenue: {profile.get('annual_revenue', '')}
Service Area: {profile.get('service_area', '')}

PRIMARY CONTACT
Name: {profile.get('contact_name', '')}
Title: {profile.get('contact_title', '')}
Phone: {profile.get('contact_phone', '')}
Email: {profile.get('contact_email', '')}

INSURANCE
General Liability Carrier: {profile.get('gl_carrier', '')}
GL Policy #: {profile.get('gl_policy', '')}
GL Per Occurrence: {profile.get('gl_limit', '')}
GL Aggregate: {profile.get('gl_aggregate', '')}
GL Expiration: {profile.get('gl_expiration', '')}

Workers' Compensation Carrier: {profile.get('wc_carrier', '')}
WC Policy #: {profile.get('wc_policy', '')}
WC Expiration: {profile.get('wc_expiration', '')}

Auto Insurance Carrier: {profile.get('auto_carrier', '')}
Auto Policy #: {profile.get('auto_policy', '')}

Umbrella Carrier: {profile.get('umbrella_carrier', '')}
Umbrella Limit: {profile.get('umbrella_limit', '')}
Umbrella Policy #: {profile.get('umbrella_policy', '')}

CERTIFICATIONS & LICENSES
IL Registration: {profile.get('il_registration', '')}
PWNA: {profile.get('pwna_cert', '')}
OSHA: {profile.get('osha_cert', '')}
EPA Lead-Safe: {profile.get('epa_cert', '')}
MBE/WBE/VBE: {profile.get('mbe_cert', '')}
Other: {profile.get('other_certs', '')}

SERVICES
{profile.get('services_description', '')}

REFERENCES
"""
        refs = profile.get("references", [])
        for i, ref in enumerate(refs, 1):
            if ref.get("name"):
                vendor_sheet += f"""
Reference {i}:
  Name: {ref.get('name', '')}
  Company: {ref.get('company', '')}
  Phone: {ref.get('phone', '')}
  Email: {ref.get('email', '')}
  Work: {ref.get('description', '')}
"""

        vendor_sheet += f"""
W-9 INFORMATION
Name (tax return): {profile.get('w9_name', '')}
Tax Classification: {profile.get('w9_type', '')}
Address: {profile.get('w9_address', '')}
City/State/ZIP: {profile.get('w9_city_state', '')}
FEIN: {profile.get('fein', '')}
"""

        st.download_button("Download Vendor Info Sheet (.txt)", vendor_sheet,
                          "vendor_info_sheet.txt", "text/plain", use_container_width=True)

# ============================================================
# CONTRACT TEMPLATE
# ============================================================
elif page == "Contract Template":
    st.markdown("## Service Agreement Template")
    st.markdown("Generate a ready-to-sign contract when a client says yes.")

    profile = load_json("company_profile.json", {})
    company = profile.get("company_name", "[YOUR COMPANY NAME]")
    contact = profile.get("contact_name", "[YOUR NAME]")
    phone = profile.get("contact_phone", profile.get("phone", "[PHONE]"))
    email = profile.get("contact_email", profile.get("email", "[EMAIL]"))
    address = f"{profile.get('address', '')}, {profile.get('city', '')}, {profile.get('state', '')} {profile.get('zip', '')}"
    insurance = f"{profile.get('gl_limit', '$1,000,000')} per occurrence / {profile.get('gl_aggregate', '$2,000,000')} aggregate"

    with st.form("contract_form"):
        st.markdown("### Client Information")
        ct1, ct2 = st.columns(2)
        with ct1:
            ct_client = st.text_input("Client Name / Entity")
            ct_contact = st.text_input("Client Contact Person")
            ct_address = st.text_input("Property Address")
        with ct2:
            ct_phone = st.text_input("Client Phone")
            ct_email_ct = st.text_input("Client Email")
            ct_start = st.date_input("Start Date", value=date.today() + timedelta(days=14))

        st.markdown("### Contract Terms")
        ct3, ct4 = st.columns(2)
        with ct3:
            ct_term = st.selectbox("Contract Term", ["1 Year", "2 Years", "3 Years", "6 Months", "Per Service"])
            ct_payment = st.selectbox("Payment Terms", ["Net 30", "Net 15", "Due Upon Completion", "Monthly Invoice", "Quarterly Invoice"])
            ct_escalator = st.text_input("Annual Price Increase", value="3%")
        with ct4:
            ct_termination = st.text_input("Termination Notice", value="60 days written notice")
            ct_renewal = st.selectbox("Auto-Renewal", ["Yes — auto-renews unless cancelled", "No — requires new agreement"])
            ct_guarantee = st.text_input("Satisfaction Guarantee", value="100% satisfaction guarantee — we re-do any unsatisfactory work at no charge")

        st.markdown("### Services & Pricing")
        contract_services = []
        for i in range(6):
            cs1, cs2, cs3 = st.columns([3, 1.5, 1.5])
            with cs1:
                svc = st.text_input(f"Service {i+1}", key=f"ct_svc_{i}")
            with cs2:
                freq = st.text_input(f"Frequency", key=f"ct_freq_{i}", placeholder="e.g., 2x/year")
            with cs3:
                price = st.number_input(f"Price ($)", key=f"ct_price_{i}", min_value=0, value=0, step=100)
            if svc and price > 0:
                contract_services.append({"service": svc, "frequency": freq, "price": price})

        submitted = st.form_submit_button("Generate Contract", use_container_width=True, type="primary")

        if submitted and ct_client and contract_services:
            total = sum(s["price"] for s in contract_services)

            svc_table = ""
            for j, s in enumerate(contract_services, 1):
                svc_table += f"   {j}. {s['service']}"
                if s['frequency']:
                    svc_table += f" — {s['frequency']}"
                svc_table += f" — ${s['price']:,.2f}\n"

            contract = f"""
{'='*65}
COMMERCIAL EXTERIOR MAINTENANCE SERVICE AGREEMENT
{'='*65}

This Service Agreement ("Agreement") is entered into as of
{ct_start.strftime('%B %d, %Y')} by and between:

CONTRACTOR:
   {company}
   {address}
   Contact: {contact}
   Phone: {phone} | Email: {email}

CLIENT:
   {ct_client}
   {ct_address}
   Contact: {ct_contact}
   Phone: {ct_phone} | Email: {ct_email_ct}

{'='*65}
1. SCOPE OF SERVICES
{'='*65}

Contractor agrees to perform the following services at the
property located at {ct_address}:

{svc_table}
   TOTAL ANNUAL VALUE: ${total:,.2f}

{'='*65}
2. TERM
{'='*65}

This Agreement shall commence on {ct_start.strftime('%B %d, %Y')}
and continue for a period of {ct_term}.

{'ct_renewal'}

Annual price adjustment: {ct_escalator} per year.

{'='*65}
3. PAYMENT TERMS
{'='*65}

Payment terms: {ct_payment}

Invoices will be submitted upon completion of each scheduled
service visit. Late payments (over 30 days) may be subject to
a 1.5% monthly finance charge.

{'='*65}
4. INSURANCE & LIABILITY
{'='*65}

Contractor maintains the following insurance coverage:

   General Liability: {insurance}
   Workers' Compensation: Per Illinois state requirements
   Commercial Auto: Full coverage on all vehicles
   {'Umbrella: ' + profile.get('umbrella_limit', '') if profile.get('umbrella_limit') else ''}

Contractor will add Client as Additional Insured upon request
and provide current certificates of insurance.

{'='*65}
5. SATISFACTION GUARANTEE
{'='*65}

{ct_guarantee}

If Client is not satisfied with any service, Client must notify
Contractor within 48 hours of service completion. Contractor
will re-perform the service at no additional cost within 5
business days.

{'='*65}
6. ENVIRONMENTAL COMPLIANCE
{'='*65}

Contractor agrees to comply with all applicable federal, state,
and local environmental regulations, including:

   - Illinois EPA water discharge requirements
   - Clean Water Act storm drain protection
   - Proper containment and disposal of wash water
   - Use of approved, biodegradable cleaning agents

{'='*65}
7. SCHEDULING & ACCESS
{'='*65}

   - Contractor will provide 48-hour advance notice before
     each scheduled service visit
   - Client will provide reasonable access to the property
   - Services may be rescheduled due to weather without penalty
   - Before/after photo documentation will be provided for
     each service visit

{'='*65}
8. TERMINATION
{'='*65}

Either party may terminate this Agreement with {ct_termination}
to the other party. Upon termination, Client shall pay for all
services performed through the termination date.

{'='*65}
9. INDEMNIFICATION
{'='*65}

Contractor shall indemnify and hold Client harmless from any
claims, damages, or liabilities arising from Contractor's
performance of services under this Agreement, except to the
extent caused by Client's negligence.

{'='*65}
10. GOVERNING LAW
{'='*65}

This Agreement shall be governed by the laws of the State of
Illinois.

{'='*65}
ACCEPTANCE
{'='*65}

By signing below, both parties agree to the terms of this
Service Agreement.


CONTRACTOR: {company}

Signature: _________________________  Date: ___________

Print Name: {contact}
Title: {profile.get('contact_title', '')}


CLIENT: {ct_client}

Signature: _________________________  Date: ___________

Print Name: {ct_contact}
Title: _________________________
"""

            st.markdown("### Generated Contract")
            st.code(contract, language=None)

            st.download_button("Download Contract (.txt)", contract,
                             f"contract_{ct_client.replace(' ', '_')}_{ct_start.isoformat()}.txt",
                             "text/plain", use_container_width=True)

    st.divider()
    st.markdown("""
    ### How It Works

    1. **Fill out your Company Profile first** (one-time) — it auto-fills the contractor section
    2. **Enter the client details and services** when they say yes
    3. **Download and send** — they sign, you sign, work begins
    4. **The contract covers:** scope, payment, insurance, environmental compliance, scheduling, termination, satisfaction guarantee

    **For larger municipal contracts**, they'll usually provide their own contract. But for HOAs, property managers, apartment complexes, and other private entities, YOU provide the contract. Having it ready shows professionalism and speeds up the close.
    """)

# ============================================================
# VENDOR REGISTRATION TRACKER
# ============================================================
elif page == "Vendor Registration":
    st.markdown("## Vendor Registration Tracker")
    st.markdown("Track which portals and municipalities you've registered with.")

    # Pre-built list of portals to register on
    required_portals = [
        {"portal": "DemandStar", "url": "https://www.demandstar.com", "priority": "Critical", "notes": "Wilmette & Glenview ONLY accept bids here. Covers most north suburban entities."},
        {"portal": "Cook County Bonfire", "url": "https://cookcountyil.bonfirehub.com/portal/", "priority": "Critical", "notes": "All Cook County contracts. Paper bids no longer accepted."},
        {"portal": "Lake County Purchasing Portal", "url": "https://www.lakecountypurchasingportal.com", "priority": "Critical", "notes": "All Lake County contracts."},
        {"portal": "Illinois Procurement Gateway", "url": "https://ipg.illinois.gov", "priority": "High", "notes": "Required before using BidBuy."},
        {"portal": "Illinois BidBuy", "url": "https://www.bidbuy.illinois.gov", "priority": "High", "notes": "State-level contracts."},
        {"portal": "BidNet Direct", "url": "https://www.bidnetdirect.com/illinois", "priority": "High", "notes": "934+ IL agencies."},
        {"portal": "PublicPurchase", "url": "https://www.publicpurchase.com", "priority": "Medium", "notes": "Supplemental coverage."},
        {"portal": "SAM.gov", "url": "https://sam.gov", "priority": "Medium", "notes": "Federal contracts. NAICS 561790."},
        {"portal": "GovQuote", "url": "https://govquote.us", "priority": "Low", "notes": "Small purchases below RFP threshold."},
    ]

    # Initialize registrations if needed
    if not st.session_state.vendor_registrations:
        st.session_state.vendor_registrations = [
            {"portal": p["portal"], "url": p["url"], "priority": p["priority"],
             "status": "Not Started", "date_registered": "", "username": "", "notes": p["notes"]}
            for p in required_portals
        ]
        save_all()

    st.markdown("### Procurement Portal Registrations")
    for i, reg in enumerate(st.session_state.vendor_registrations):
        rc1, rc2, rc3, rc4 = st.columns([3, 2, 2, 1])
        with rc1:
            status_icon = {"Registered": "reg-done", "In Progress": "reg-pending", "Not Started": "reg-not"}
            css = status_icon.get(reg["status"], "reg-not")
            st.markdown(f'<span class="{css}">●</span> **{reg["portal"]}**', unsafe_allow_html=True)
            st.caption(reg["notes"])
        with rc2:
            st.markdown(f"Priority: **{reg['priority']}**")
            if reg["date_registered"]:
                st.caption(f"Registered: {reg['date_registered']}")
        with rc3:
            new_status = st.selectbox("Status", ["Not Started", "In Progress", "Registered"],
                                     index=["Not Started", "In Progress", "Registered"].index(reg["status"]),
                                     key=f"vreg_{i}", label_visibility="collapsed")
            if new_status != reg["status"]:
                st.session_state.vendor_registrations[i]["status"] = new_status
                if new_status == "Registered":
                    st.session_state.vendor_registrations[i]["date_registered"] = date.today().isoformat()
                save_all()
                st.rerun()
        with rc4:
            st.link_button("Open", reg["url"], use_container_width=True)
        st.divider()

    # Summary
    registered = len([r for r in st.session_state.vendor_registrations if r["status"] == "Registered"])
    total = len(st.session_state.vendor_registrations)
    st.markdown(f"**{registered} of {total} portals registered** ({int(registered/total*100) if total > 0 else 0}% complete)")

    # Add custom portal
    st.markdown("### Add Custom Portal / Vendor List")
    with st.form("add_portal", clear_on_submit=True):
        vr1, vr2 = st.columns(2)
        with vr1:
            vr_name = st.text_input("Portal / Entity Name")
            vr_url = st.text_input("URL")
        with vr2:
            vr_priority = st.selectbox("Priority", ["Critical", "High", "Medium", "Low"])
            vr_notes = st.text_input("Notes")
        submitted = st.form_submit_button("Add Portal", use_container_width=True)
        if submitted and vr_name:
            st.session_state.vendor_registrations.append({
                "portal": vr_name, "url": vr_url, "priority": vr_priority,
                "status": "Not Started", "date_registered": "", "username": "", "notes": vr_notes
            })
            save_all()
            st.rerun()

# ============================================================
# MUNICIPAL GUIDE
# ============================================================
elif page == "Municipal Guide":
    st.markdown("## Municipal Vendor Guide")
    st.markdown("How each municipality's bidding process works — platform, contacts, thresholds, and required docs.")

    st.markdown("""
    ### Illinois Purchasing Thresholds (State Law)

    Under **65 ILCS 5/8-9-1**:

    | Amount | What's Required |
    |--------|----------------|
    | Under ~$5,000 | Direct purchase, no quotes |
    | $5,000 - $25,000 | Informal quotes (usually 3) |
    | Over $25,000 | Formal sealed competitive bid |

    **Home rule municipalities** (most larger suburbs) can set their own thresholds.
    Schaumburg and Northbrook set theirs at **$20,000**.

    **What this means for you:** Most exterior cleaning jobs under $25K don't require a formal bid. The facilities director can just hire you.
    """)

    st.divider()

    # Load municipal guide
    muni_guide = load_json("municipal_vendor_guide.json", {})
    municipalities = muni_guide.get("municipalities", []) if isinstance(muni_guide, dict) else muni_guide

    if not municipalities and isinstance(muni_guide, dict):
        # Try the structured format
        municipalities = []
        for key in muni_guide:
            if isinstance(muni_guide[key], dict) and "platform" in str(muni_guide[key]):
                municipalities.append(muni_guide[key])

    # Hardcoded guide data
    guide_data = [
        {"town": "Evanston", "platform": "DemandStar", "threshold": "Not posted", "contact": "purchasing@cityofevanston.org / 847-866-2935", "docs": "DBE Certification, W-9, AvidXchange registration", "notes": "Free DemandStar registration"},
        {"town": "Skokie", "platform": "Own website only", "threshold": "$25,000", "contact": "michael.aleksic@skokie.org / 847-933-8240", "docs": "Per bid specs", "notes": "No third-party platform"},
        {"town": "Arlington Heights", "platform": "Munis Self Service (own)", "threshold": "$25,000", "contact": "lsubrin@vah.com", "docs": "W-9, contractor reg ($130/yr)", "notes": "$130/yr contractor registration fee"},
        {"town": "Palatine", "platform": "eSuite OpenBidder", "threshold": "Not posted", "contact": "847-358-7500", "docs": "Portal registration", "notes": "Custom eSuite system"},
        {"town": "Schaumburg", "platform": "ProcureNow / OpenGov", "threshold": "$20,000", "contact": "bids@schaumburg.com", "docs": "Portal registration, vendor demographics", "notes": "Lower threshold than most"},
        {"town": "Glenview", "platform": "DemandStar (EXCLUSIVE)", "threshold": "Not posted", "contact": "purchasing@glenview.il.us / 847-724-1700", "docs": "DemandStar registration only", "notes": "ONLY accepts bids through DemandStar"},
        {"town": "Wilmette", "platform": "DemandStar (exclusive)", "threshold": "Not posted", "contact": "ruemmlerc@wilmette.com / 847-853-7619", "docs": "DemandStar registration", "notes": "All solicitations through DemandStar only"},
        {"town": "Northbrook", "platform": "Own website + DemandStar", "threshold": "$20,000", "contact": "847-272-5050", "docs": "Vendor Info Form, diversity data", "notes": "Lower threshold — $20K"},
        {"town": "Highland Park", "platform": "BidNet Direct / MITN", "threshold": "Not posted", "contact": "847-432-0800", "docs": "Per bid specs", "notes": "Must notify PM when bid downloaded"},
        {"town": "Deerfield", "platform": "Own website + OpenGov", "threshold": "Not posted", "contact": "847-945-5000", "docs": "Account creation, plan holder reg", "notes": "Closed noon-1PM"},
        {"town": "Des Plaines", "platform": "Own website", "threshold": "Not posted", "contact": "847-391-5300", "docs": "Per bid specs", "notes": "desplainesil.gov (not desplaines.org)"},
        {"town": "Mount Prospect", "platform": "DemandStar + BidNet", "threshold": "Not posted", "contact": "847-392-6000", "docs": "Vendor Reg Form, demographics", "notes": "On both platforms"},
        {"town": "Buffalo Grove", "platform": "BidNet / Vendor Registry", "threshold": "Not posted", "contact": "info@vbg.org / 847-459-2500", "docs": "Vendor Registry, diversity info", "notes": "Free BidNet limited access"},
        {"town": "Vernon Hills", "platform": "Own website", "threshold": "$25,000", "contact": "847-367-3700", "docs": "Per bid specs", "notes": ""},
        {"town": "Libertyville", "platform": "Own website (CivicEngage)", "threshold": "Not posted", "contact": "847-362-2430", "docs": "Per bid specs, sealed bids", "notes": ""},
        {"town": "Waukegan", "platform": "DemandStar + own site", "threshold": "Not posted", "contact": "wkpurchasing@waukeganil.gov / 847-599-2500", "docs": "W-9, Certificate of Good Standing, business reg, certs", "notes": "Most detailed vendor form"},
        {"town": "Lake Forest", "platform": "QuestCDN", "threshold": "Not posted", "contact": "cityhall@cityoflakeforest.com / 847-234-2600", "docs": "QuestCDN registration", "notes": "Only town using QuestCDN"},
        {"town": "Mundelein", "platform": "Own website", "threshold": "$25,000", "contact": "info@mundelein.org / 847-949-3200", "docs": "Per bid specs", "notes": ""},
        {"town": "Gurnee", "platform": "DemandStar + own site", "threshold": "Not posted", "contact": "finance@village.gurnee.il.us / 847-599-7500", "docs": "W-9, DemandStar registration", "notes": "Craig Lambrecht (fleet 847-599-6881)"},
        {"town": "Park Ridge", "platform": "DemandStar / OpenBids", "threshold": "Not posted", "contact": "procurement@parkridge.us / 847-318-7948", "docs": "Vendor Info Form, W-9", "notes": ""},
    ]

    # Search
    search = st.text_input("Search by town name", placeholder="Type a town name...")

    filtered_guide = guide_data
    if search:
        filtered_guide = [g for g in guide_data if search.lower() in g["town"].lower()]

    for g in filtered_guide:
        with st.expander(f"**{g['town']}** — {g['platform']}", expanded=False):
            gc1, gc2 = st.columns(2)
            with gc1:
                st.markdown(f"**Platform:** {g['platform']}")
                st.markdown(f"**Bid Threshold:** {g['threshold']}")
                st.markdown(f"**Required Docs:** {g['docs']}")
            with gc2:
                st.markdown(f"**Contact:** {g['contact']}")
                if g['notes']:
                    st.markdown(f"**Notes:** {g['notes']}")

    st.divider()
    st.markdown("""
    ### Platform Coverage Summary

    Register on these platforms to cover the most municipalities:

    | Platform | Municipalities Covered |
    |----------|----------------------|
    | **DemandStar** | Evanston, Glenview, Wilmette, Northbrook, Mt Prospect, Waukegan, Gurnee, Park Ridge |
    | **BidNet Direct** | Highland Park, Buffalo Grove, Mount Prospect |
    | **ProcureNow/OpenGov** | Schaumburg |
    | **QuestCDN** | Lake Forest |
    | **Own website only** | Skokie, Palatine, Deerfield, Des Plaines, Vernon Hills, Libertyville, Mundelein |

    **For the "own website only" towns:** You need to check their bid pages manually or call their purchasing department to get on their vendor notification list.
    """)

# ============================================================
# PROCUREMENT PORTALS
# ============================================================
elif page == "Procurement Portals":
    st.markdown("## Procurement Portals — Where to Find & Submit Bids")
    st.markdown("Register on these platforms to get notified when bids go live.")

    st.markdown("### Priority Registration (Do These First)")
    portals_priority = [
        {"name": "DemandStar", "url": "https://www.demandstar.com", "cost": "Free single-agency; $99-299/mo for full access",
         "covers": "Most north suburban municipalities, school districts, park districts. Wilmette & Glenview ONLY accept bids here.", "priority": "1"},
        {"name": "Cook County Bonfire", "url": "https://cookcountyil.bonfirehub.com/portal/", "cost": "FREE",
         "covers": "All Cook County contracts. Paper bids no longer accepted.", "priority": "2"},
        {"name": "Lake County Purchasing Portal", "url": "https://www.lakecountypurchasingportal.com", "cost": "FREE",
         "covers": "All Lake County contracts and bid notifications.", "priority": "3"},
        {"name": "Illinois BidBuy", "url": "https://www.bidbuy.illinois.gov", "cost": "FREE",
         "covers": "State-level contracts. Register through Illinois Procurement Gateway first.", "priority": "4"},
        {"name": "BidNet Direct (Illinois)", "url": "https://www.bidnetdirect.com/illinois", "cost": "Free limited access",
         "covers": "934+ Illinois government agencies including school districts.", "priority": "5"},
        {"name": "PublicPurchase", "url": "https://www.publicpurchase.com", "cost": "FREE",
         "covers": "1,940+ government agencies nationwide. Supplemental coverage.", "priority": "6"},
    ]
    for p in portals_priority:
        with st.container():
            pc1, pc2 = st.columns([3, 1])
            with pc1:
                st.markdown(f"**{p['priority']}. [{p['name']}]({p['url']})**")
                st.markdown(f"*{p['covers']}*")
                st.caption(f"Cost: {p['cost']}")
            with pc2:
                st.link_button("Open Portal", p['url'], use_container_width=True)
            st.divider()

    st.markdown("### Additional Portals")
    additional = [
        {"name": "SAM.gov", "url": "https://sam.gov", "note": "Federal contracts — free, register under NAICS 561790"},
        {"name": "GovQuote", "url": "https://govquote.us", "note": "Small purchases below RFP threshold — free"},
        {"name": "Illinois Procurement Gateway", "url": "https://ipg.illinois.gov", "note": "Required before using BidBuy — free"},
        {"name": "RFP School Watch", "url": "https://www.rfpschoolwatch.com/illinois-schools", "note": "Aggregates K-12 school district bids in IL"},
        {"name": "BidPrime", "url": "https://www.bidprime.com", "note": "Aggregates 110,000+ agencies — paid"},
        {"name": "FindRFP", "url": "https://www.findrfp.com", "note": "Building maintenance specific bids — paid"},
    ]
    for a in additional:
        st.markdown(f"- **[{a['name']}]({a['url']})** — {a['note']}")

    st.markdown("### Direct Municipal Bid Pages")
    direct = [
        ("Evanston", "https://www.cityofevanston.org/business/bids-proposals"),
        ("Northbrook", "https://www.northbrook.il.us/Bids.aspx"),
        ("Wilmette", "https://www.wilmette.gov/Bids.aspx"),
        ("Glenview", "https://www.glenview.il.us/purchasing"),
    ]
    for name, url in direct:
        st.markdown(f"- **[{name}]({url})**")

    st.markdown("### Park District Bid Pages")
    parks = [
        ("Northbrook Park District", "https://www.nbparks.org/about/bids/"),
        ("Wilmette Park District", "https://wilmettepark.org/bids-rfps/"),
        ("Highland Park Park District", "https://www.pdhp.org/bids-rfps/"),
        ("Hoffman Estates Park District", "https://www.heparks.org/general-information/bid-information/"),
    ]
    for name, url in parks:
        st.markdown(f"- **[{name}]({url})**")

    st.markdown("### NAICS Code")
    st.markdown("Register under **561790** — Other Services to Buildings and Dwellings. Small business threshold: $9M revenue.")

# ============================================================
# KNOWLEDGE BASE
# ============================================================
elif page == "Knowledge Base":
    st.markdown("## Knowledge Base")

    kb_tab1, kb_tab2, kb_tab3, kb_tab4, kb_tab5, kb_tab6, kb_tab7, kb_tab8 = st.tabs(["Bidding Process", "Requirements & Docs", "IL Regulations", "Pricing Guide", "FOIA & Public Records", "Winning Playbook", "Certifications", "Networking"])

    with kb_tab1:
        st.markdown("""
        ### How Commercial Bidding Works

        **Types of Solicitations:**
        - **IFB (Invitation for Bid)** — Price is the main factor. Lowest bidder wins.
        - **RFP (Request for Proposal)** — They evaluate quality, experience, AND price.
        - **RFQ (Request for Qualifications)** — Pre-qualifies you before the real bid.

        **The Process:**
        1. Entity identifies a need
        2. Scope of work is drafted
        3. Posted on procurement portals or sent to approved vendor list
        4. Pre-bid meeting or site walk-through (sometimes mandatory)
        5. Submit sealed bid by deadline
        6. Evaluation committee reviews
        7. Award made, contract executed
        8. Notice of award posted publicly

        **How Winners Are Picked:**
        - **Lowest Price**: Meet all requirements, cheapest wins
        - **Best Value**: Price (40-60%) + Experience (20-30%) + Technical (15-25%) + Certifications (5-10%)

        **Typical Contract Length:** 1 year base + four 1-year renewals with 2-4% annual escalation

        **Best Time to Pursue:** February-March (budget planning season)
        """)

    with kb_tab2:
        st.markdown("""
        ### Required Documents for Bidding

        **Always Required:**
        - General Liability Insurance ($1M per occurrence / $2M aggregate minimum)
        - Workers' Compensation Insurance (mandatory in IL with 1+ employees)
        - Commercial Auto Insurance
        - W-9 Form
        - Business License (state + local)
        - References (3-5 commercial/government clients)

        **Often Required:**
        - Bid Bond or Performance Bond (5-10% of bid amount)
        - Safety Plan & OSHA Compliance
        - Environmental Compliance Plan (power washing water containment)
        - Proof of Experience (project history, before/after photos)
        - Umbrella/Excess Liability ($1M-$5M for larger contracts)

        **Nice to Have (Strengthens Bids):**
        - PWNA Certification (Power Washers of North America)
        - OSHA 10/30 Certification
        - Minority/Woman/Veteran-Owned Business Certification
        - EPA Lead-Safe Certification (for older buildings)

        **Keep a "Bid Package" Ready:**
        Pre-assemble a folder with all docs so you can respond to bids quickly.
        """)

    with kb_tab3:
        st.markdown("""
        ### Illinois Regulations

        **Licensing:**
        - No state license required for power washing, window cleaning, or gutter cleaning
        - General business registration with IL Secretary of State required
        - Local municipal business licenses required (check each village clerk)
        - Chicago requires specific BACP business license

        **Environmental Rules (CRITICAL for Power Washing):**
        - **You CANNOT let wash water flow into storm drains** — Clean Water Act violation
        - Collect and contain ALL wash water (use berms or vacuum recovery)
        - Discharging to waterways requires NPDES permit from IL EPA
        - Discharging to sanitary sewer — contact local treatment works
        - IL EPA Helpline: **(888) EPA-1996**

        **Insurance Minimums:**
        - Workers' Comp: Mandatory with 1+ employees
        - General Liability: $1M/$2M minimum (some want $5M)
        - Commercial Auto: Required for business vehicles

        **Prevailing Wage:**
        - Government contracts may require prevailing wage rates
        - Illinois Prevailing Wage Act (820 ILCS 130)
        - This can significantly increase labor costs on government jobs

        **IL EPA Power Washing Guide:**
        https://epa.illinois.gov/content/dam/soi/en/web/epa/topics/small-business/publications/documents/mobile-power-washing.pdf
        """)

    with kb_tab4:
        st.markdown("""
        ### Pricing Guide

        **Power Washing:**
        | Service | Rate Range |
        |---------|-----------|
        | Building exteriors | $0.15 - $0.75/sq ft |
        | Parking lots/concrete | $0.03 - $0.20/sq ft |
        | Sidewalks/walkways | $0.20 - $0.90/sq ft |
        | Dumpster pads | $50 - $150 each |
        | Parking spaces | $8 - $20/space |
        | Commercial day rate | $1,000 - $2,500/day |

        **Window Cleaning:**
        | Service | Rate Range |
        |---------|-----------|
        | Commercial panes | $10 - $20/pane |
        | Storefront panes | $4 - $8/pane |
        | Hourly commercial | $50 - $100/hour |
        | Per sq ft (building) | $0.50 - $2.50/sq ft |

        **Gutter Cleaning:**
        | Service | Rate Range |
        |---------|-----------|
        | Per linear foot | $0.75 - $2.50 |
        | Multi-story multipliers apply |

        **Margins:** Gross 40-50% | Net 20-30% for well-run ops

        **Bidding Tips:**
        - Always visit the site before bidding
        - Maintenance contracts priced 15-25% below one-time rates
        - Factor in prevailing wage for government work
        - Build in 5-10% contingency
        - IL active season: March-November (9 months)
        """)

    with kb_tab5:
        st.markdown("""
        ### FOIA & Public Records

        **Illinois Freedom of Information Act (5 ILCS 140)**

        All government bid tabulations are public record. Municipalities must respond within **5 business days**.

        **What You Can Request:**
        - Bid tabulation sheets (every bidder and their price)
        - Award letters and executed contracts
        - Vendor lists
        - Previous years' maintenance budgets

        **FOIA Request Template:**

        > Dear [Municipality Name] FOIA Officer,
        >
        > Pursuant to the Illinois Freedom of Information Act (5 ILCS 140), I respectfully request:
        >
        > 1. Bid tabulation sheets for any exterior building maintenance, power washing, window cleaning, or gutter cleaning contracts awarded in the past 24 months
        > 2. The names and bid amounts of all responding vendors
        > 3. The awarded contract amount and vendor name
        >
        > Please provide these records in electronic format if available.
        >
        > Thank you,
        > [Your Name / Company / Email / Phone]

        **Pro tip:** Send FOIA requests to EVERY municipality in your service area.
        """)

    with kb_tab6:
        st.markdown("""
        ### What Wins Commercial Contracts

        **The bar is LOW.** Most competitors fail at basic reliability. Here's what decision-makers actually care about:

        **#1 Reliability** — Show up, do the job right, don't create problems. Property managers' biggest headache is vendors who no-show or cancel last-minute.

        **#2 Responsiveness** — Answer the phone. Return calls same-day. Provide quotes within 24-48 hours. Most competitors take a week.

        **#3 Documentation** — Before/after photos with GPS timestamps. This protects the property manager when their boss asks "did the vendor actually do the work?"

        **#4 Single Point of Contact** — They want ONE person to call, not a rotating cast.

        **#5 Environmental Compliance** — They don't want fines because your crew washed chemicals into a storm drain.

        **#6 References from Similar Properties** — School districts want school references. HOAs want HOA references.

        ---

        **What Makes Them SWITCH to You:**
        - Proactive communication (automated arrival/completion notifications)
        - Guaranteed response times in writing
        - Dedicated account manager
        - Digital photo documentation portal
        - Price lock guarantees (no surprise increases)
        - Bundled services that reduce number of vendors they manage

        **Pain Points That Make Them LEAVE Their Current Vendor:**
        - No-shows or last-minute cancellations
        - Having to re-explain scope every time
        - Poor communication
        - Property damage with no accountability
        - Surprise charges
        - Inconsistent quality
        - No proof work was completed

        ---

        **Your National Brand Advantage — USE IT:**
        - Consistency across multiple properties
        - Bench depth (backup crews if someone's sick)
        - 24/7 emergency dispatch
        - Serve multi-location property managers with ONE contract
        - Financial stability = lower risk for the client
        - Higher insurance limits than local operators

        ---

        **The Winning Proposal Structure:**
        1. Lead with THEIR problems, not your history
        2. Offer THREE pricing tiers (Good/Better/Best)
        3. Include SLA with response time guarantees
        4. Before/after case studies from similar property types
        5. Clear scope, clear pricing, clear timeline
        6. Satisfaction guarantee
        7. Multi-year option with price lock

        **Technology Differentiators:**
        - ServiceTitan or Housecall Pro for scheduling/dispatch
        - GPS-tagged, timestamped before/after photos (table stakes for commercial)
        - Customer portal where property managers can see photos, approve quotes, pay invoices
        - Automated arrival/completion notifications
        """)

    with kb_tab7:
        st.markdown("""
        ### Certifications That Win Contracts

        **Tier 1 — Must-Haves (Table Stakes):**
        | Certification | Why |
        |--------------|-----|
        | General Liability ($1M-$2M+) | Required by every commercial client |
        | Workers' Comp | Legally required in IL |
        | ACORD 25 Certificate | Standard proof-of-insurance form |
        | IL Business License | Legal requirement |

        **Tier 2 — Competitive Advantage:**
        | Certification | Impact on Bidding |
        |--------------|------------------|
        | OSHA 10-Hour | Some RFPs give 5-10 points for safety training |
        | OSHA 30-Hour (supervisors) | Differentiator in proposals |
        | PWNA Certified Technician | Demonstrates professional competence |
        | PWNA Environmental Cert | Critical for municipal work near waterways |
        | EPA Lead-Safe Certified Firm | Required for buildings built before 1978 |

        **Tier 3 — Point Boosters:**
        | Certification | Impact |
        |--------------|--------|
        | MBE/WBE/VBE Status | 5-15 bonus points on many municipal RFPs |
        | PWNA Chemical Safety | Prerequisite for other PWNA certs |
        | BBB Accreditation | Trust signal for HOAs |
        | UAMCC Membership | Industry credibility |

        **How Municipal RFPs Score:**
        - Price: 30-40%
        - Qualifications/Experience: 25-35%
        - Approach/Methodology: 15-25%
        - References: 10-15%
        - MBE/WBE/DBE: 5-15% bonus in some jurisdictions

        Certifications boost your Qualifications score. Environmental certs boost Approach score. Safety certs boost both.
        """)

    with kb_tab8:
        st.markdown("""
        ### Networking — Where the Deals Happen

        **JOIN THESE THREE ORGANIZATIONS:**

        **1. CAI Illinois (Community Associations Institute)**
        - Phone: (847) 301-7505
        - Email: info@cai-illinois.org
        - Address: 1821 Walden Office Square, Schaumburg, IL
        - **Why:** Business Partner membership gets you in front of every HOA board and property manager in the suburbs
        - Annual conference is the single best event for HOA business
        - Directory listing puts you in front of boards looking for vendors

        **2. BOMA Chicago (Building Owners & Managers Association)**
        - Website: bomachicago.org
        - **Why:** Allied Membership connects you with commercial building owners and managers
        - Events and networking with the people who hire exterior maintenance vendors for office buildings, retail centers, industrial properties

        **3. IREM Chicago Chapter #23 (Institute of Real Estate Management)**
        - Phone: 630-954-4400
        - Website: iremchicago.org
        - **Why:** Industry Partner Program gets you networking with commercial property managers
        - Directory listing, event sponsorship opportunities
        - These are the people who manage apartment complexes, office buildings, and commercial portfolios

        ---

        **Key Property Manager Contacts Found:**

        | Company | Email | Phone | Manages |
        |---------|-------|-------|---------|
        | Associa Chicagoland | HelpMeChicagoland@associa.us | 847-490-3833 | HOAs, condos, high-rises |
        | Foster Premier | info@fosterpremier.com | 847-459-1222 | HOAs across 6 counties |
        | Inland Real Estate | propertymanagement@inlandgroup.com | (630) 218-8000 | Apartments, commercial, storage |
        | NAI Hiffman | info@hiffman.com | 630-932-1234 | 137M SF, 982 buildings |
        | RealManage | info@realmanage.com | 1-866-473-2573 | IL HOAs and condos |
        | FirstService Residential | (call) | 847-459-0000 | North Shore suburbs |
        | Cushman & Wakefield | (call) | +1 312 470 1800 | Commercial properties |
        | Draper and Kramer | (contact form) | (312) 346-8600 | High-rise residential |
        | Sudler Property Mgmt | (call) | 312-751-0900 | Chicago condos/HOAs |

        **Strategy:** Landing ONE property management company gives you access to dozens of properties. Associa alone manages 8,000+ units. NAI Hiffman manages 982 buildings.
        """)

# ============================================================
# EMAIL TEMPLATES
# ============================================================
elif page == "Email Templates":
    st.markdown("## Cold Outreach Email Templates")
    st.markdown("Copy and customize these for different target types.")

    template_type = st.selectbox("Select Template", [
        "Property Manager — Introduction",
        "Apartment Complex — Seasonal Services",
        "HOA/Condo Board — Annual Maintenance",
        "Shopping Center — Exterior Maintenance",
        "Municipality — Vendor Introduction",
        "School District — Summer Maintenance",
        "Car Dealership — Lot & Building",
        "Senior Living — Campus Maintenance",
        "Hotel — Exterior Services",
        "Follow-Up — No Response",
        "Follow-Up — After Meeting",
    ])

    templates = {
        "Property Manager — Introduction": """Subject: Commercial Exterior Maintenance — Northern Suburbs

Hi [Contact Name],

I'm reaching out from [Your Company Name]. We provide commercial power washing, window cleaning, and gutter maintenance for properties across the northern suburbs of Chicago.

We currently service [X] commercial properties in [nearby towns] and would love the opportunity to provide a competitive quote for your portfolio.

Our services include:
- Building exterior power washing
- Window cleaning (interior & exterior)
- Gutter cleaning & maintenance
- Parking lot & sidewalk cleaning
- Graffiti removal

We carry $[X]M in general liability coverage and are fully insured and bonded.

Would you be open to a quick call this week? I'd also be happy to provide a free on-site assessment of any property in your portfolio.

Best regards,
[Your Name]
[Phone]
[Email]""",

        "Apartment Complex — Seasonal Services": """Subject: Spring Exterior Cleaning — [Property Name]

Hi [Contact Name],

Spring is around the corner and I wanted to reach out about exterior maintenance for [Property Name].

We specialize in commercial power washing for multi-unit residential properties across the northern suburbs.

For apartment communities, we typically handle:
- Building exterior washing (siding, brick, stucco)
- Parking garage & lot cleaning
- Sidewalk & entryway power washing
- Window cleaning (common areas + unit exteriors)
- Gutter cleaning & downspout flushing

We offer annual maintenance contracts with seasonal scheduling — and maintenance contracts come with preferred pricing.

Can I put together a no-obligation quote? I'm happy to do a free walk-through.

Best regards,
[Your Name]
[Phone]
[Email]""",

        "HOA/Condo Board — Annual Maintenance": """Subject: Exterior Maintenance Proposal for [Community Name]

Dear [Board President / Property Manager],

I'd like to introduce [Your Company Name] as a resource for [Community Name]'s exterior building maintenance needs.

We work with several HOA and condo communities in [nearby area] providing:
- Annual building power washing
- Window cleaning schedules
- Gutter cleaning (spring & fall)
- Common area maintenance
- Concrete & walkway cleaning

I'd be happy to attend your next board meeting to present our services, or put together a written proposal based on a quick property walk-through.

Would either option work for you?

Best regards,
[Your Name]
[Phone]
[Email]""",

        "Shopping Center — Exterior Maintenance": """Subject: Exterior Cleaning Services — [Center Name]

Hi [Contact Name],

I'm reaching out regarding exterior maintenance for [Shopping Center Name].

Clean storefronts and walkways directly impact foot traffic and tenant satisfaction. We provide:
- Storefront & facade power washing
- Window cleaning (tenant storefronts + common areas)
- Sidewalk & parking lot cleaning
- Dumpster pad cleaning
- Gum & stain removal
- Graffiti removal (24-hour response)

We offer flexible scheduling (early morning/after hours) so there's zero disruption.

When would be a good time to walk the property?

Best regards,
[Your Name]
[Phone]
[Email]""",

        "Municipality — Vendor Introduction": """Subject: Vendor Introduction — Exterior Building Maintenance Services

Dear [Facilities Director / Public Works Director],

I'd like to introduce [Your Company Name] as a qualified vendor for exterior building maintenance services for the [Village/City of X].

We specialize in:
- Commercial power washing (buildings, sidewalks, parking structures)
- Window cleaning
- Gutter cleaning & maintenance
- Concrete restoration cleaning

We are fully insured ($[X]M general liability, workers' compensation, commercial auto), environmentally compliant (Illinois EPA water containment protocols), and experienced in government contracts.

I would like to:
1. Register on your approved vendor list
2. Learn about upcoming maintenance contracts or bid opportunities
3. Provide a capabilities overview for your files

Could you point me to the right person or process for vendor registration?

Best regards,
[Your Name]
[Phone]
[Email]""",

        "School District — Summer Maintenance": """Subject: Summer Building Maintenance — [District Name]

Dear [Facilities Director],

Summer break is the ideal window for exterior building maintenance. With [X] school buildings in the district, maintaining clean exteriors protects your investment.

We can handle:
- Full building exterior power washing
- Window cleaning (all floors)
- Gutter cleaning & inspection
- Sidewalk & entryway cleaning
- Playground equipment cleaning

We work on compressed summer timelines and can schedule around summer programs.

Is there an upcoming bid cycle, or would you accept a proposal for this summer?

Best regards,
[Your Name]
[Phone]
[Email]""",

        "Car Dealership — Lot & Building": """Subject: Dealership Exterior Cleaning — [Dealership Name]

Hi [Contact Name],

First impressions matter in car sales. I'd like to offer [Your Company Name]'s exterior cleaning services to keep [Dealership Name] looking its best.

We provide:
- Showroom & building exterior power washing
- Lot and sidewalk cleaning
- Drive-through/service bay area cleaning
- Window cleaning (showroom + offices)
- Sign and canopy cleaning

Clean lots and buildings directly impact customer perception. We offer flexible early morning scheduling so there's no disruption during business hours.

We work with several dealerships in the northern suburbs. Can I provide a quick quote?

Best regards,
[Your Name]
[Phone]
[Email]""",

        "Senior Living — Campus Maintenance": """Subject: Exterior Maintenance Services — [Facility Name]

Dear [Facilities Director],

Curb appeal and safety are critical for senior living communities. I'd like to offer [Your Company Name]'s exterior cleaning services for [Facility Name].

We specialize in:
- Building exterior power washing
- Window cleaning (all floors)
- Walkway and patio cleaning (slip prevention)
- Gutter cleaning & maintenance
- Entrance and common area cleaning

We understand the unique needs of senior communities — quiet operation, safety barriers, and flexible scheduling around resident activities.

Would you be open to a walk-through so I can put together a proposal?

Best regards,
[Your Name]
[Phone]
[Email]""",

        "Hotel — Exterior Services": """Subject: Exterior Maintenance — [Hotel Name]

Hi [Contact Name],

Guest experience starts at the curb. I'd like to offer exterior cleaning services for [Hotel Name].

We provide:
- Building facade and entrance power washing
- Window cleaning (all floors)
- Parking structure cleaning
- Pool deck and patio cleaning
- Dumpster area cleaning
- Graffiti removal

We offer early morning and overnight scheduling so there's zero guest disruption. Several hotels in the northern suburbs trust us for ongoing maintenance.

Can I provide a competitive quote?

Best regards,
[Your Name]
[Phone]
[Email]""",

        "Follow-Up — No Response": """Subject: Re: [Original Subject Line]

Hi [Contact Name],

I wanted to follow up on my email from [date]. I'll keep this short.

We'd love the chance to provide a free, no-obligation quote for exterior cleaning services at [Property/Entity Name].

If now isn't the right time, could you let me know when your maintenance contracts typically come up for renewal? I'll follow up then.

Best regards,
[Your Name]
[Phone]""",

        "Follow-Up — After Meeting": """Subject: Great Meeting — Next Steps for [Property/Entity Name]

Hi [Contact Name],

Thanks for taking the time to walk the property with me today.

Based on what we discussed, I'll put together a detailed proposal covering:
- [Service 1]
- [Service 2]
- [Service 3]

I'll have that to you by [date]. In the meantime, I've attached our insurance certificate and references.

Looking forward to working together.

Best regards,
[Your Name]
[Phone]"""
    }

    st.markdown("---")
    st.code(templates[template_type], language=None)
    st.download_button("Download Template", templates[template_type],
                       f"template_{template_type.lower().replace(' ', '_').replace('—', '')}.txt", "text/plain")
