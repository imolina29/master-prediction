import pandas as pd
import streamlit as st

from backend.subscriptions.channel import ChannelManager
from dashboard.auth import require_admin
from dashboard.components.theme import section_header, stat_card
from dashboard.data_access import (
    get_payments,
    get_subscription_kpis,
    get_subscriptions,
    get_supabase_client,
)

if not require_admin():
    st.stop()

st.markdown(
    '<h1 style="font-size:1.8rem; font-weight:800; letter-spacing:-0.03em;">'
    "💳 Suscripciones</h1>",
    unsafe_allow_html=True,
)

subscriptions = get_subscriptions()
payments = get_payments()
kpis = get_subscription_kpis(subscriptions, payments)

# ── KPIs ──
st.markdown(section_header("📊", "Indicadores"), unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        stat_card("MRR", f"${kpis['mrr']:,.0f} COP", "ingreso recurrente mensual"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        stat_card("Activos", str(kpis["active_count"]), "suscriptores"),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        stat_card("Nuevos", str(kpis["new_this_month"]), "este mes"),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        stat_card("Churn", f"{kpis['churn_rate']:.1f}%", "tasa de cancelacion"),
        unsafe_allow_html=True,
    )

# ── Suscriptores ──
st.markdown(section_header("👥", "Suscriptores"), unsafe_allow_html=True)

if subscriptions:
    status_filter = st.selectbox(
        "Filtrar por estado",
        ["Todos", "active", "cancelled", "past_due", "expired"],
        key="sub_status_filter",
    )

    filtered = subscriptions
    if status_filter != "Todos":
        filtered = [s for s in subscriptions if s["status"] == status_filter]

    STATUS_ICONS = {
        "active": "🟢",
        "cancelled": "🔴",
        "past_due": "🟡",
        "expired": "⚫",
    }

    rows = []
    for s in filtered:
        icon = STATUS_ICONS.get(s["status"], "")
        end_date = s.get("current_period_end", "")[:10] if s.get("current_period_end") else "—"
        rows.append(
            {
                "Usuario": f"@{s.get('telegram_username') or s['telegram_user_id']}",
                "Plan": s["plan"].capitalize(),
                "Estado": f"{icon} {s['status']}",
                "Inicio": s.get("created_at", "")[:10],
                "Proximo Cobro": end_date,
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Actions ──
    st.markdown(section_header("🔧", "Acciones"), unsafe_allow_html=True)

    active_subs = [s for s in subscriptions if s["status"] == "active"]
    if active_subs:
        usernames = [f"@{s.get('telegram_username') or s['telegram_user_id']}" for s in active_subs]
        selected = st.selectbox("Seleccionar suscriptor", usernames, key="sub_action_select")
        selected_sub = active_subs[usernames.index(selected)]

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("❌ Revocar Acceso", use_container_width=True):
                try:
                    channel_mgr = ChannelManager()
                    channel_mgr.revoke_user_access(selected_sub["telegram_user_id"])
                except Exception as e:
                    st.warning(f"No se pudo revocar en Telegram: {e}")
                client = get_supabase_client()
                client.table("subscriptions").update({"status": "cancelled"}).eq(
                    "id", selected_sub["id"]
                ).execute()
                st.success(f"Acceso revocado para {selected}")
                st.rerun()
        with col_b:
            if st.button("📅 Extender 7 dias", use_container_width=True):
                from datetime import datetime, timedelta, timezone

                current_end = selected_sub.get("current_period_end")
                if current_end:
                    new_end = datetime.fromisoformat(
                        current_end.replace("Z", "+00:00")
                    ) + timedelta(days=7)
                else:
                    new_end = datetime.now(timezone.utc) + timedelta(days=7)

                client = get_supabase_client()
                client.table("subscriptions").update(
                    {"current_period_end": new_end.isoformat()}
                ).eq("id", selected_sub["id"]).execute()
                st.success(f"Suscripcion extendida 7 dias para {selected}")
                st.rerun()
    else:
        st.info("No hay suscriptores activos.")
else:
    st.info("No hay suscripciones registradas.")

# ── Historial de Pagos ──
st.markdown(section_header("💰", "Historial de Pagos"), unsafe_allow_html=True)

if payments:
    pay_status_filter = st.selectbox(
        "Filtrar por estado",
        ["Todos", "succeeded", "failed", "refunded"],
        key="pay_status_filter",
    )

    filtered_payments = payments
    if pay_status_filter != "Todos":
        filtered_payments = [p for p in payments if p["status"] == pay_status_filter]

    pay_rows = []
    for p in filtered_payments:
        sub_info = p.get("subscriptions") or {}
        username = sub_info.get("telegram_username", "—")
        plan = sub_info.get("plan", "—")

        STATUS_PAY_ICONS = {"succeeded": "✅", "failed": "❌", "refunded": "↩️"}
        icon = STATUS_PAY_ICONS.get(p["status"], "")

        pay_rows.append(
            {
                "Fecha": p.get("paid_at", "")[:10],
                "Usuario": f"@{username}" if username != "—" else "—",
                "Monto": f"${float(p['amount']):,.0f} COP",
                "Plan": plan.capitalize() if plan != "—" else "—",
                "Estado": f"{icon} {p['status']}",
            }
        )

    st.dataframe(pd.DataFrame(pay_rows), use_container_width=True, hide_index=True)

    total_revenue = sum(float(p["amount"]) for p in payments if p["status"] == "succeeded")
    st.markdown(
        stat_card("Ingresos Totales", f"${total_revenue:,.0f} COP", "todos los pagos exitosos"),
        unsafe_allow_html=True,
    )
else:
    st.info("No hay pagos registrados.")
