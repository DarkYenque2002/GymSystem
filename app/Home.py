import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import sys
import os

# Ajustar el path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

# Intentar diferentes rutas de importación
try:
    from lib.auth import login_form, has_permission, register_user
    from lib.sp_wrappers import kpis
    from lib.db import query
except ImportError:
    try:
        from app.lib.auth import login_form, has_permission, register_user
        from app.lib.sp_wrappers import kpis
        from app.lib.db import query
    except ImportError:
        try:
            import lib.auth as auth
            import lib.sp_wrappers as sp
            import lib.db as db
            login_form = auth.login_form
            has_permission = auth.has_permission
            register_user = getattr(auth, 'register_user', None)
            kpis = sp.kpis
            query = db.query
        except ImportError as e:
            st.error(f"Error importando módulos: {e}")
            st.error("Verifica que los archivos lib/auth.py, lib/sp_wrappers.py y lib/db.py existan")
            st.stop()

st.set_page_config(page_title="Gym Manager", page_icon="🏋️", layout="wide")

# Función de registro personalizada
def registro_form():
    st.subheader("📝 Registro de Nuevo Usuario")
    
    with st.form("registro_form"):
        st.write("Completa los siguientes datos para crear tu cuenta:")

        email = st.text_input("Email *", placeholder="juan@ejemplo.com")
        password = st.text_input("Contraseña *", type="password", placeholder="Mínimo 6 caracteres")
        password_confirm = st.text_input("Confirmar Contraseña *", type="password")
        
        rol = st.selectbox("Rol", ["admin", "socio", "recepcionista", "entrenador"], index=1)
        sede_id = st.number_input("ID de Sede", min_value=1, value=1)

        submitted = st.form_submit_button("🚀 Registrarse", type="primary", use_container_width=True)

        if submitted:
            # Validaciones
            errores = []
            
            if not email.strip():
                errores.append("El email es obligatorio")
            elif "@" not in email:
                errores.append("Email inválido")
            if not password:
                errores.append("La contraseña es obligatoria")
            elif len(password) < 6:
                errores.append("La contraseña debe tener al menos 6 caracteres")
            if password != password_confirm:
                errores.append("Las contraseñas no coinciden")
            
            if errores:
                for error in errores:
                    st.error(f"❌ {error}")
            else:
                try:
                    # Verificar si el email ya existe
                    existing_user = query("SELECT id FROM auth_user WHERE email = %s", (email,))
                    if existing_user:
                        st.error("❌ Ya existe un usuario con este email")
                        return
                    
                    # Hash de la contraseña
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    
                    # Registrar nuevo usuario
                    query("""
                        INSERT INTO auth_user (email, password_hash, rol, sede_id, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        email, password_hash, rol, sede_id, datetime.now()
                    ))
                    
                    st.success("✅ Usuario registrado exitosamente")
                    st.info("🔐 Ahora puedes iniciar sesión con tu email y contraseña")
                    st.session_state["show_login"] = True
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error al registrar usuario: {e}")

# Llamada a la función de registro
registro_form()

st.divider()
st.caption("""
**📋 Nota:** Al registrarte como socio podrás acceder a funciones básicas. 
Para roles administrativos (recepcionista, entrenador, etc.), contacta al administrador del gimnasio.
""")

# Aquí empieza la parte del dashboard, que solo debería ejecutarse si el usuario está autenticado
if st.session_state.get("user"):
    # Usuario autenticado - mostrar dashboard
    u = st.session_state["user"]
    st.success(f"Hola, {u['email']} ({u.get('rol', 'usuario')})")

    # === KPIs PRINCIPALES ===
    st.header("📊 Resumen Ejecutivo")
    
    try:
        data = kpis()
        d = data[0] if data else {}
        socios = d.get("socios", "—")
        activas = d.get("membresias_activas", "—")
        accesos_hoy = d.get("accesos_hoy", "—")
    except Exception:
        try:
            socios = query("SELECT COUNT(*) c FROM socio")[0]["c"]
            activas = query("SELECT COUNT(*) c FROM membresia WHERE estado='activa' AND fecha_fin>=CURRENT_DATE")[0]["c"]
            accesos_hoy = query("SELECT COUNT(*) c FROM acceso WHERE fecha_entrada::date=CURRENT_DATE")[0]["c"]
        except:
            socios, activas, accesos_hoy = "—", "—", "—"

    # KPIs adicionales
    try:
        # Aforo actual por sede
        aforo_data = query("""
            SELECT s.nombre, sp_aforo_actual(s.id) as aforo_actual
            FROM sede s ORDER BY s.nombre
        """)
        
        # Ventas del día
        ventas_hoy = query("""
            SELECT COALESCE(SUM(total), 0)::numeric(10,2) as total
            FROM venta WHERE fecha::date = CURRENT_DATE
        """)[0]["total"] if query("SELECT COUNT(*) c FROM venta WHERE fecha::date = CURRENT_DATE")[0]["c"] > 0 else 0

        # Próximas clases (hoy)
        clases_hoy = query("""
            SELECT COUNT(*) c FROM clase 
            WHERE fecha_hora::date = CURRENT_DATE AND estado = 'programada'
        """)[0]["c"]

        # Membresías que vencen en 7 días
        vencimientos = query("""
            SELECT COUNT(*) c FROM membresia 
            WHERE estado = 'activa' AND fecha_fin BETWEEN CURRENT_DATE AND CURRENT_DATE + 7
        """)[0]["c"]

    except Exception as e:
        st.error(f"Error obteniendo datos adicionales: {e}")
        aforo_data = []
        ventas_hoy = 0
        clases_hoy = 0
        vencimientos = 0

    # Mostrar KPIs en columnas
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("👥 Socios Totales", socios)
    with col2:
        st.metric("💳 Membresías Activas", activas)
    with col3:
        st.metric("🚪 Accesos Hoy", accesos_hoy)
    with col4:
        st.metric("💰 Ventas Hoy", f"S/. {ventas_hoy}")
    with col5:
        st.metric("📅 Clases Hoy", clases_hoy)

    # === ALERTAS ===
    if vencimientos > 0:
        st.warning(f"⚠️ {vencimientos} membresías vencen en los próximos 7 días")

    # === AFORO POR SEDE ===
    if aforo_data:
        st.subheader("🏢 Aforo Actual por Sede")
        aforo_cols = st.columns(len(aforo_data))
        for i, sede_info in enumerate(aforo_data):
            with aforo_cols[i]:
                st.metric(
                    f"📍 {sede_info['nombre']}", 
                    f"{sede_info['aforo_actual']} personas",
                    help="Personas actualmente en la sede"
                )

    st.divider()
else:
    st.warning("Por favor, inicia sesión para acceder al sistema.")
