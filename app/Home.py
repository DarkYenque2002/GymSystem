import streamlit as st
import pandas as pd
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

else:
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

    # === SELECTOR DE MÓDULOS ===
    st.header("🚀 Módulos del Sistema")
    
    # Lista de módulos disponibles según permisos
    modulos_disponibles = []
    
    if has_permission("socios_read"):
        modulos_disponibles.append("👤 Gestión de Socios")
    if has_permission("membership_assign") or has_permission("plans_manage"):
        modulos_disponibles.append("💳 Membresías y Planes")
    if has_permission("classes_publish") or has_permission("reservations_create"):
        modulos_disponibles.append("📆 Clases y Reservas")
    if has_permission("access_entry") or has_permission("access_exit"):
        modulos_disponibles.append("🚪 Control de Acceso")
    if has_permission("products_manage"):
        modulos_disponibles.append("🛒 Inventario")
    if has_permission("sales_read") or has_permission("sales_create"):
        modulos_disponibles.append("💵 Punto de Venta")
    if has_permission("payments_read") or has_permission("payments_create"):
        modulos_disponibles.append("💳 Gestión de Pagos")
    if has_permission("reports_view"):
        modulos_disponibles.append("📊 Reportes")
    if has_permission("users_manage"):
        modulos_disponibles.append("👥 Administración")
    if has_permission("audit_view"):
        modulos_disponibles.append("📑 Auditoría")

    # Nota sobre navegación
    if modulos_disponibles:
        st.info("📝 **Nota:** Para acceder a los módulos específicos, navega usando las páginas del sidebar izquierdo.")
        
        # Mostrar módulos disponibles como información
        cols = st.columns(3)
        for i, modulo in enumerate(modulos_disponibles):
            with cols[i % 3]:
                st.write(f"✅ {modulo}")
    else:
        st.warning("No tienes permisos para acceder a módulos específicos. Contacta al administrador.")

    st.divider()

    # === GRÁFICOS DE TENDENCIAS ===
    st.header("📈 Tendencias")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Accesos por Día (Última Semana)")
        try:
            accesos_semana = query("""
                SELECT 
                    fecha_entrada::date as fecha,
                    COUNT(*) as accesos
                FROM acceso 
                WHERE fecha_entrada >= CURRENT_DATE - 7
                GROUP BY fecha_entrada::date
                ORDER BY fecha
            """)
            if accesos_semana:
                df_accesos = pd.DataFrame(accesos_semana)
                st.line_chart(df_accesos.set_index('fecha'))
            else:
                st.info("No hay datos de accesos en la última semana")
        except Exception as e:
            st.error(f"Error cargando gráfico de accesos: {e}")

    with chart_col2:
        st.subheader("Ventas por Día (Última Semana)")
        try:
            ventas_semana = query("""
                SELECT 
                    fecha::date as fecha,
                    SUM(total) as total_ventas
                FROM venta 
                WHERE fecha >= CURRENT_DATE - 7
                GROUP BY fecha::date
                ORDER BY fecha
            """)
            if ventas_semana:
                df_ventas = pd.DataFrame(ventas_semana)
                st.line_chart(df_ventas.set_index('fecha'))
            else:
                st.info("No hay datos de ventas en la última semana")
        except Exception as e:
            st.error(f"Error cargando gráfico de ventas: {e}")

    st.divider()

    # === INFORMACIÓN DETALLADA ===
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Próximas Clases", "⏰ Actividad Reciente", "📋 Membresías por Vencer", "🏆 Top Productos"])

    with tab1:
        st.subheader("Clases Programadas (Próximas 48 horas)")
        try:
            clases = query("""
                SELECT 
                    c.id,
                    c.nombre,
                    s.nombre AS sede,
                    c.fecha_hora,
                    c.capacidad,
                    COUNT(r.id) as reservas,
                    (c.capacidad - COUNT(r.id)) as disponibles
                FROM clase c 
                JOIN sede s ON s.id = c.sede_id
                LEFT JOIN reserva r ON r.clase_id = c.id AND r.estado = 'confirmada'
                WHERE c.fecha_hora >= now() - interval '1 hour'
                  AND c.fecha_hora <= now() + interval '48 hours'
                  AND c.estado = 'programada'
                GROUP BY c.id, c.nombre, s.nombre, c.fecha_hora, c.capacidad
                ORDER BY c.fecha_hora
                LIMIT 20
            """)
            if clases:
                df_clases = pd.DataFrame(clases)
                df_clases['fecha_hora'] = pd.to_datetime(df_clases['fecha_hora'])
                st.dataframe(
                    df_clases[['nombre', 'sede', 'fecha_hora', 'reservas', 'disponibles']], 
                    use_container_width=True,
                    column_config={
                        'fecha_hora': st.column_config.DatetimeColumn(
                            'Fecha y Hora',
                            format='DD/MM/YYYY HH:mm'
                        )
                    }
                )
            else:
                st.info("No hay clases programadas en las próximas 48 horas")
        except Exception as e:
            st.error(f"Error cargando clases: {e}")

    with tab2:
        st.subheader("Últimos Accesos")
        try:
            accesos_recientes = query("""
                SELECT 
                    s.nombre as socio,
                    se.nombre as sede,
                    a.fecha_entrada,
                    CASE WHEN a.fecha_salida IS NULL THEN 'Dentro' ELSE 'Salió' END as estado
                FROM acceso a
                JOIN socio s ON s.id = a.socio_id
                JOIN sede se ON se.id = a.sede_id
                ORDER BY a.fecha_entrada DESC
                LIMIT 10
            """)
            if accesos_recientes:
                df_accesos = pd.DataFrame(accesos_recientes)
                df_accesos['fecha_entrada'] = pd.to_datetime(df_accesos['fecha_entrada'])
                st.dataframe(
                    df_accesos,
                    use_container_width=True,
                    column_config={
                        'fecha_entrada': st.column_config.DatetimeColumn(
                            'Hora de Entrada',
                            format='DD/MM/YYYY HH:mm'
                        )
                    }
                )
            else:
                st.info("No hay accesos recientes")
        except Exception as e:
            st.error(f"Error cargando accesos: {e}")

    with tab3:
        st.subheader("Membresías que Vencen Pronto")
        try:
            vencimientos_detalle = query("""
                SELECT 
                    s.nombre as socio,
                    s.telefono,
                    mp.nombre as plan,
                    m.fecha_fin,
                    (m.fecha_fin - CURRENT_DATE) as dias_restantes
                FROM membresia m
                JOIN socio s ON s.id = m.socio_id
                JOIN membresia_plan mp ON mp.id = m.plan_id
                WHERE m.estado = 'activa' 
                  AND m.fecha_fin BETWEEN CURRENT_DATE AND CURRENT_DATE + 15
                ORDER BY m.fecha_fin
            """)
            if vencimientos_detalle:
                df_venc = pd.DataFrame(vencimientos_detalle)
                st.dataframe(df_venc, use_container_width=True)
            else:
                st.success("No hay membresías por vencer en los próximos 15 días")
        except Exception as e:
            st.error(f"Error cargando vencimientos: {e}")

    with tab4:
        st.subheader("Productos Más Vendidos (Último Mes)")
        try:
            top_productos = query("""
                SELECT 
                    p.nombre,
                    SUM(vi.cantidad) as total_vendido,
                    SUM(vi.subtotal) as ingresos,
                    p.stock as stock_actual
                FROM venta_item vi
                JOIN producto p ON p.id = vi.producto_id
                JOIN venta v ON v.id = vi.venta_id
                WHERE v.fecha >= CURRENT_DATE - 30
                GROUP BY p.id, p.nombre, p.stock
                ORDER BY total_vendido DESC
                LIMIT 10
            """)
            if top_productos:
                df_productos = pd.DataFrame(top_productos)
                st.dataframe(df_productos, use_container_width=True)
            else:
                st.info("No hay ventas de productos en el último mes")
        except Exception as e:
            st.error(f"Error cargando productos: {e}")

    # === ACCIONES RÁPIDAS ===
    st.divider()
    st.header("⚡ Acciones Rápidas")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🔍 Buscar Socio", use_container_width=True):
            st.info("Funcionalidad disponible en el módulo de Socios")
    
    with action_col2:
        if st.button("📝 Nueva Reserva", use_container_width=True):
            st.info("Funcionalidad disponible en el módulo de Clases")
    
    with action_col3:
        if st.button("💰 Registrar Pago", use_container_width=True):
            st.info("Funcionalidad disponible en el módulo de Pagos")

    # === PIE DE PÁGINA ===
    st.divider()
    st.caption(f"🕒 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    st.caption("💡 **Sugerencia:** Si encuentras errores al navegar a otras páginas, todas las funciones principales están disponibles desde este dashboard.")
