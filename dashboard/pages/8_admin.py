import streamlit as st
import streamlit_authenticator as stauth

from dashboard.auth import _deep_copy_secrets, require_admin
from dashboard.components.theme import section_header, stat_card

if not require_admin():
    st.stop()

st.markdown(
    '<h1 style="font-size:2rem;">⚙️ Panel de Administracion</h1>',
    unsafe_allow_html=True,
)

# ── Usuarios registrados ──
st.markdown(section_header("👥", "Usuarios Registrados"), unsafe_allow_html=True)

credentials = _deep_copy_secrets("credentials")
if credentials:
    users = []
    for username, data in credentials.items():
        users.append(
            {
                "Usuario": username,
                "Nombre": data.get("name", "—"),
                "Email": data.get("email", "—"),
                "Rol": data.get("role", "viewer"),
            }
        )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            stat_card("Total Usuarios", str(len(users)), "registrados"),
            unsafe_allow_html=True,
        )
    with c2:
        admins = sum(1 for u in users if u["Rol"] == "admin")
        st.markdown(
            stat_card("Administradores", str(admins), f"de {len(users)}"),
            unsafe_allow_html=True,
        )

    st.dataframe(users, use_container_width=True, hide_index=True)
else:
    st.info("No hay credenciales configuradas.")

# ── Generador de hash ──
st.markdown(section_header("🔑", "Generar Hash de Password"), unsafe_allow_html=True)

st.caption("Genera el hash bcrypt para agregar un nuevo usuario en Streamlit Cloud Secrets.")

new_password = st.text_input("Password del nuevo usuario", type="password")
if new_password:
    hashed = stauth.Hasher([new_password]).generate()[0]
    st.code(hashed, language="text")
    st.caption("Copia este hash en tu configuracion de Streamlit Cloud Secrets.")

# ── Instrucciones ──
st.markdown(
    section_header("📖", "Como agregar un nuevo usuario"),
    unsafe_allow_html=True,
)

with st.expander("Ver instrucciones"):
    st.markdown(
        "1. Genera el hash del password usando el campo de arriba\n"
        "2. Ve a **Streamlit Cloud** → tu app → **Settings** → **Secrets**\n"
        "3. Agrega el nuevo usuario al bloque `[credentials]`:\n\n"
        "```toml\n"
        "[credentials.nuevo_usuario]\n"
        'name = "Nombre del Usuario"\n'
        'email = "email@ejemplo.com"\n'
        'password = "$2b$12$hash_generado_aqui"\n'
        'role = "viewer"\n'
        "```\n\n"
        "4. Guarda los cambios. El usuario podra iniciar sesion inmediatamente.\n\n"
        "**Roles disponibles:**\n"
        "- `admin`: Acceso completo + panel de administracion\n"
        "- `viewer`: Acceso de solo lectura a todas las paginas excepto admin"
    )
