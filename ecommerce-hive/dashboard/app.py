# =============================================================================
# app.py  —  Streamlit analytics dashboard
#
# Run from ecommerce-hive/:
#     streamlit run dashboard/app.py
#
# Data source (sidebar):
#   Hive — runs HiveQL on HiveServer2 through PyHive (python/analytics.py)
#   CSV  — runs the same analytics with pandas on data/*.csv (python/analytics_pandas.py)
# =============================================================================

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.express as px

from python.config import DASHBOARD_TITLE, DATA_DIR, HIVE_HOST, HIVE_PORT

st.set_page_config(page_title=DASHBOARD_TITLE, layout="wide")

# Brazilian state codes used in the Olist data -> full names
STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


def with_state_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["state"] = df["state"].map(STATE_NAMES).fillna(df["state"])
    return df


@st.cache_data(ttl=60, show_spinner=False)
def hive_available() -> bool:
    try:
        from python.hive_connection import ping
        return ping()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")

    hive_up = hive_available()
    source = st.radio("Data source", ["Hive", "CSV"], index=0 if hive_up else 1, horizontal=True)
    USE_HIVE = source == "Hive"
    if USE_HIVE and not hive_up:
        st.warning(f"Cannot reach HiveServer2 at {HIVE_HOST}:{HIVE_PORT}.")

    selected_year = st.selectbox("Year", ["All", "2016", "2017", "2018"])
    year_val = None if selected_year == "All" else int(selected_year)

    try:
        categories = sorted(pd.read_csv(DATA_DIR / "products.csv", usecols=["category"])["category"].unique())
        states = sorted(pd.read_csv(DATA_DIR / "customers.csv", usecols=["state"])["state"].unique(),
                        key=lambda s: STATE_NAMES.get(s, s))
    except FileNotFoundError:
        categories, states = [], []

    selected_category = st.selectbox("Product category", ["All"] + categories)
    category_val = None if selected_category == "All" else selected_category

    selected_state = st.selectbox("State", ["All"] + states,
                                  format_func=lambda s: STATE_NAMES.get(s, s))
    state_val = None if selected_state == "All" else selected_state

if USE_HIVE:
    import python.analytics as ana
else:
    import python.analytics_pandas as ana


@st.cache_data(ttl=300, show_spinner="Running query...")
def safe(func_name: str, use_hive: bool, **kwargs):
    """Call ana.<func_name>(**kwargs). use_hive is part of the cache key."""
    try:
        return getattr(ana, func_name)(**kwargs), None
    except Exception as e:
        return None, str(e)


def fmt_brl(v: float) -> str:
    if v >= 1e6:   return f"R$ {v/1e6:.2f} M"
    elif v >= 1e3: return f"R$ {v/1e3:.1f} K"
    return f"R$ {v:,.0f}"


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("E-Commerce Sales Analytics")
st.caption("Olist Brazilian e-commerce orders, 2016–2018. Revenue counts delivered orders; amounts in Brazilian reais.")

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
metrics, err = safe("get_summary_metrics", use_hive=USE_HIVE)
if err:
    st.error(err)
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total revenue",   fmt_brl(metrics["total_revenue"]))
    c2.metric("Orders",          f"{metrics['total_orders']:,}")
    c3.metric("Customers",       f"{metrics['total_customers']:,}")
    c4.metric("Avg order value", fmt_brl(metrics["avg_order_value"]))

# ---------------------------------------------------------------------------
# Monthly revenue
# ---------------------------------------------------------------------------
st.subheader("Monthly revenue")

monthly_df, err = safe("get_monthly_revenue", use_hive=USE_HIVE,
                       year=year_val, category=category_val, state=state_val)
if err:
    st.error(err)
elif monthly_df is not None and not monthly_df.empty:
    monthly_df["month"] = (monthly_df["order_year"].astype(str) + "-"
                           + monthly_df["order_month"].astype(str).str.zfill(2))
    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(monthly_df, x="month", y="monthly_revenue", markers=True,
                      labels={"month": "Month", "monthly_revenue": "Revenue (R$)"},
                      title="Revenue")
        fig.update_layout(plot_bgcolor="white", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(monthly_df, x="month", y="order_count",
                     labels={"month": "Month", "order_count": "Orders"},
                     title="Orders")
        fig.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No orders match the selected filters.")

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
st.subheader("Top products")

t_rev, t_units = st.tabs(["By revenue", "By units sold"])
with t_rev:
    df, err = safe("get_top_products", use_hive=USE_HIVE, by="revenue", limit=10)
    if err:
        st.error(err)
    elif df is not None and not df.empty:
        fig = px.bar(df.sort_values("revenue"), x="revenue", y="product_name",
                     orientation="h", color="category",
                     labels={"revenue": "Revenue (R$)", "product_name": "Product", "category": "Category"})
        fig.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
with t_units:
    df, err = safe("get_top_products", use_hive=USE_HIVE, by="units_sold", limit=10)
    if err:
        st.error(err)
    elif df is not None and not df.empty:
        fig = px.bar(df.sort_values("units_sold"), x="units_sold", y="product_name",
                     orientation="h", color="category",
                     labels={"units_sold": "Units sold", "product_name": "Product", "category": "Category"})
        fig.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
st.subheader("Revenue by category")

cat_df, err = safe("get_revenue_by_category", use_hive=USE_HIVE)
if err:
    st.error(err)
elif cat_df is not None and not cat_df.empty:
    fig = px.bar(cat_df.head(15), x="category", y="revenue",
                 labels={"revenue": "Revenue (R$)", "category": "Category"},
                 title="Top 15 categories")
    fig.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------
st.subheader("Revenue by state")

state_df, err = safe("get_revenue_by_state", use_hive=USE_HIVE)
if err:
    st.error(err)
elif state_df is not None and not state_df.empty:
    col1, col2 = st.columns([3, 2])
    with col1:
        fig = px.bar(with_state_names(state_df).head(15).sort_values("revenue"),
                     x="revenue", y="state", orientation="h",
                     labels={"revenue": "Revenue (R$)", "state": "State"},
                     title="Top 15 states")
        fig.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        city_df, err2 = safe("get_revenue_by_city", use_hive=USE_HIVE, limit=15)
        if err2:
            st.error(err2)
        elif city_df is not None and not city_df.empty:
            st.markdown("**Top 15 cities**")
            st.dataframe(
                with_state_names(city_df).rename(columns={
                    "city": "City", "state": "State",
                    "revenue": "Revenue (R$)", "total_orders": "Orders",
                }),
                use_container_width=True, hide_index=True,
            )

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
st.subheader("Payments")

col1, col2 = st.columns(2)
with col1:
    pay_df, err = safe("get_payment_method_distribution", use_hive=USE_HIVE)
    if err:
        st.error(err)
    elif pay_df is not None and not pay_df.empty:
        fig = px.pie(pay_df, names="payment_method", values="total_transactions",
                     title="Payment method")
        st.plotly_chart(fig, use_container_width=True)
with col2:
    inst_df, err = safe("get_payment_installments", use_hive=USE_HIVE)
    if err:
        st.error(err)
    elif inst_df is not None and not inst_df.empty:
        fig = px.bar(inst_df, x="payment_installments", y="txn_count",
                     labels={"txn_count": "Payments", "payment_installments": "Instalments"},
                     title="Number of instalments")
        fig.update_layout(plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Order status
# ---------------------------------------------------------------------------
st.subheader("Order status")

status_df, err = safe("get_order_status_distribution", use_hive=USE_HIVE)
if err:
    st.error(err)
elif status_df is not None and not status_df.empty:
    st.dataframe(
        status_df.rename(columns={
            "order_status": "Status", "order_count": "Orders",
            "percentage": "Share (%)", "total_value": "Order value (R$)",
        }),
        use_container_width=True, hide_index=True,
    )

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
st.subheader("Top customers by spending")

cust_df, err = safe("get_top_customers", use_hive=USE_HIVE, limit=10)
if err:
    st.error(err)
elif cust_df is not None and not cust_df.empty:
    st.dataframe(
        with_state_names(cust_df).rename(columns={
            "customer_id": "Customer ID", "city": "City", "state": "State",
            "total_spent": "Total spent (R$)", "orders_placed": "Orders",
        }),
        use_container_width=True, hide_index=True,
    )
