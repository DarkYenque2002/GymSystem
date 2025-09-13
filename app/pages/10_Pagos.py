import streamlit as st
from datetime import date, datetime, time, timedelta
from io import StringIO
import csv

from app.lib.auth import require_perm, has_permission
from app.lib.db import query, db_cursor
from app.lib.ui import load_base_css

st.set_page_config(page_title="Pagos", page_icon="💳", layout="wide")
load_base_css()
st.title("💳 Pagos")

require_perm("payments_read")

# ------------------ Helpers ------------------
MEDIOS = ["Efectivo", "Tarjeta", "Transferencia", "Yape", "Plin", "POS", "Otro"]

def to_csv(rows, headers):
    sio = StringIO()
    writer = csv.DictWriter(sio, fieldnames=headers)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k) for k in headers})
    return sio.getvalue()

def auditoria(cur, accion, entidad, entidad_id=None, detalle=None):
    """Audita si la tabla auditoria existe (opcional)."""
    try:
        u = st.session_state.get("user") or {}
        uid = u.get("id")
        cur.execute("""
            INSERT INTO auditoria (usuario_id, accion, entidad, entidad_id, detalle)
            VALUES (%s, %s, %s, %s, %s::jsonb)
        """, (uid, accion, entidad, entidad_id, detalle))
    except Exception:
        # si no existe la tabla o falla, no romper el flujo
        pass

def generar_recibo_html(pago_data):
    """Genera HTML para el recibo de pago con nuevo diseño"""
    fecha_formato = pago_data['fecha'].strftime('%d/%m/%Y %H:%M') if isinstance(pago_data['fecha'], datetime) else pago_data['fecha']
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .voucher-container {{
                background: white;
                border-radius: 20px;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                max-width: 450px;
                width: 100%;
                position: relative;
            }}
            
            .voucher-header {{
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 30px 25px 25px;
                text-align: center;
                position: relative;
            }}
            
            .voucher-header::after {{
                content: '';
                position: absolute;
                bottom: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 20px solid transparent;
                border-right: 20px solid transparent;
                border-top: 20px solid #00f2fe;
            }}
            
            .gym-logo {{
                width: 60px;
                height: 60px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 15px;
                font-size: 28px;
            }}
            
            .gym-name {{
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 5px;
                letter-spacing: 1px;
            }}
            
            .gym-subtitle {{
                font-size: 14px;
                font-weight: 300;
                opacity: 0.9;
                margin-bottom: 8px;
            }}
            
            .voucher-type {{
                background: rgba(255, 255, 255, 0.2);
                display: inline-block;
                padding: 8px 20px;
                border-radius: 25px;
                font-size: 13px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .voucher-body {{
                padding: 35px 25px 25px;
            }}
            
            .voucher-number {{
                text-align: center;
                margin-bottom: 25px;
                padding: 15px;
                background: #f8f9ff;
                border-radius: 12px;
                border-left: 4px solid #4facfe;
            }}
            
            .voucher-number .label {{
                font-size: 12px;
                color: #6b7280;
                text-transform: uppercase;
                font-weight: 500;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }}
            
            .voucher-number .number {{
                font-size: 20px;
                font-weight: 700;
                color: #1f2937;
                font-family: 'Courier New', monospace;
            }}
            
            .info-grid {{
                display: grid;
                gap: 18px;
                margin-bottom: 25px;
            }}
            
            .info-item {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                padding: 12px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            
            .info-item:last-child {{
                border-bottom: none;
            }}
            
            .info-label {{
                font-size: 13px;
                color: #6b7280;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                min-width: 90px;
            }}
            
            .info-value {{
                font-size: 14px;
                color: #1f2937;
                font-weight: 500;
                text-align: right;
                flex: 1;
                margin-left: 15px;
            }}
            
            .amount-section {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px 20px;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 25px;
                position: relative;
                overflow: hidden;
            }}
            
            .amount-section::before {{
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                width: 100%;
                height: 100%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            }}
            
            .amount-label {{
                font-size: 14px;
                font-weight: 400;
                opacity: 0.9;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .amount-value {{
                font-size: 32px;
                font-weight: 700;
                font-family: 'Inter', sans-serif;
                position: relative;
                z-index: 1;
            }}
            
            .voucher-footer {{
                background: #f8f9ff;
                padding: 20px 25px;
                text-align: center;
                border-top: 3px solid #e5e7eb;
            }}
            
            .thank-you {{
                font-size: 16px;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 5px;
            }}
            
            .footer-note {{
                font-size: 12px;
                color: #6b7280;
                margin-bottom: 15px;
                line-height: 1.4;
            }}
            
            .attendant {{
                font-size: 11px;
                color: #9ca3af;
                padding-top: 10px;
                border-top: 1px solid #e5e7eb;
                font-style: italic;
            }}
            
            .decorative-elements {{
                position: absolute;
                top: 10px;
                right: 10px;
                width: 80px;
                height: 80px;
                opacity: 0.1;
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="white" stroke-width="2"/><circle cx="50" cy="50" r="25" fill="none" stroke="white" stroke-width="2"/><circle cx="50" cy="50" r="10" fill="white"/></svg>');
                background-size: contain;
            }}
            
            @media print {{
                body {{ 
                    background: white;
                    padding: 0;
                    min-height: auto;
                }}
                .voucher-container {{
                    box-shadow: none;
                    border-radius: 0;
                    max-width: none;
                }}
            }}
            
            @media (max-width: 480px) {{
                body {{
                    padding: 10px;
                }}
                .voucher-header {{
                    padding: 25px 20px 20px;
                }}
                .voucher-body {{
                    padding: 25px 20px;
                }}
                .gym-name {{
                    font-size: 20px;
                }}
                .amount-value {{
                    font-size: 28px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="voucher-container">
            <div class="voucher-header">
                <div class="decorative-elements"></div>
                <div class="gym-logo">💪</div>
                <div class="gym-name">FITNESS ZONE</div>
                <div class="gym-subtitle">Centro de Entrenamiento Premium</div>
                <div class="voucher-type">Comprobante de Pago</div>
            </div>
            
            <div class="voucher-body">
                <div class="voucher-number">
                    <div class="label">Número de Transacción</div>
                    <div class="number">FZ-{pago_data['id']:06d}</div>
                </div>
                
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Fecha</span>
                        <span class="info-value">{fecha_formato}</span>
                    </div>
                    
                    <div class="info-item">
                        <span class="info-label">Cliente</span>
                        <span class="info-value">{pago_data['socio']}</span>
                    </div>
                    
                    <div class="info-item">
                        <span class="info-label">Concepto</span>
                        <span class="info-value">{pago_data['concepto']}</span>
                    </div>
                    
                    <div class="info-item">
                        <span class="info-label">Método</span>
                        <span class="info-value">{pago_data['medio']}</span>
                    </div>
                    
                    {f'''<div class="info-item">
                        <span class="info-label">Referencia</span>
                        <span class="info-value">{pago_data['ref_externa']}</span>
                    </div>''' if pago_data.get('ref_externa') else ''}
                </div>
                
                <div class="amount-section">
                    <div class="amount-label">Total Pagado</div>
                    <div class="amount-value">S/ {pago_data['monto']:,.2f}</div>
                </div>
            </div>
            
            <div class="voucher-footer">
                <div class="thank-you">¡Gracias por confiar en nosotros! 🎯</div>
                <div class="footer-note">
                    Conserva este comprobante como respaldo de tu transacción.<br>
                    Para consultas: info@fitnesszone.com | (01) 234-5678
                </div>
                <div class="attendant">
                    Procesado por: {st.session_state.get('user', {}).get('email', 'Sistema Automático')}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def mostrar_recibo_interactivo(pago_data):
    """Muestra el recibo en la interfaz de Streamlit"""
    st.success("✅ Pago registrado exitosamente")
    
    # Generar el HTML del recibo
    recibo_html = generar_recibo_html(pago_data)
    
    # Mostrar el recibo en un contenedor especial
    st.markdown("### 🧾 Recibo Generado")
    
    # Crear dos columnas: una para el recibo y otra para las acciones
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Mostrar el recibo usando componente HTML
        st.components.v1.html(recibo_html, height=600, scrolling=True)
    
    with col2:
        st.markdown("#### Acciones")
        
        # Botón para descargar como HTML
        st.download_button(
            label="📄 Descargar Recibo (HTML)",
            data=recibo_html,
            file_name=f"recibo_{pago_data['id']:06d}.html",
            mime="text/html",
            use_container_width=True
        )
        
        # Información adicional
        st.info("💡 **Tip:** Puedes abrir el archivo HTML descargado en tu navegador e imprimirlo desde allí.")
        
        # Botón para limpiar y hacer otro pago
        if st.button("➕ Registrar Nuevo Pago", use_container_width=True):
            # Limpiar el estado del recibo
            if 'mostrar_recibo' in st.session_state:
                del st.session_state['mostrar_recibo']
            if 'ultimo_pago' in st.session_state:
                del st.session_state['ultimo_pago']
            st.rerun()

# ------------------ Tabs ------------------
tab_nuevo, tab_listado = st.tabs(["➕ Registrar pago", "📋 Listado / Anular"])

# ================== NUEVO PAGO ==================
with tab_nuevo:
    if not has_permission("payments_create"):
        st.info("No tienes permiso para registrar pagos.")
    else:
        # Verificar si hay que mostrar un recibo
        if st.session_state.get('mostrar_recibo') and st.session_state.get('ultimo_pago'):
            mostrar_recibo_interactivo(st.session_state['ultimo_pago'])
        else:
            # Formulario normal de pago
            socios = query("SELECT id, nombre FROM socio ORDER BY nombre LIMIT 500")
            if not socios:
                st.warning("Primero crea un socio.")
            else:
                c1, c2 = st.columns([2, 1])
                with c1:
                    socio = st.selectbox("Socio", socios, format_func=lambda s: f"{s['nombre']} (#{s['id']})")
                with c2:
                    medio = st.selectbox("Medio de pago", MEDIOS, index=0)

                concepto = st.text_input("Concepto", placeholder="Mensualidad septiembre / Inscripción / Producto, etc.")
                monto = st.number_input("Monto (S/)", min_value=0.10, step=1.00, value=50.00, format="%.2f")
                ref = st.text_input("Referencia externa (opcional)", placeholder="N° operación, voucher, etc.")

                # Fecha/hora del pago
                colf1, colf2 = st.columns(2)
                with colf1:
                    f_pago = st.date_input("Fecha de pago", value=date.today())
                with colf2:
                    t_pago = st.time_input("Hora", value=datetime.now().time().replace(microsecond=0))

                guardar = st.button("💾 Guardar pago", type="primary", disabled=(not concepto or monto <= 0))

                if guardar:
                    try:
                        ts = datetime.combine(f_pago, t_pago)
                        with db_cursor(commit=True) as cur:
                            cur.execute("""
                                INSERT INTO pago (socio_id, concepto, monto, medio, ref_externa, fecha)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                RETURNING id
                            """, (socio["id"], concepto.strip(), monto, medio, (ref or None), ts))
                            pid = cur.fetchone()["id"]
                            auditoria(cur,
                                      accion="crear_pago",
                                      entidad="pago",
                                      entidad_id=pid,
                                      detalle=f'{{"socio_id": {socio["id"]}, "monto": {monto}, "medio": "{medio}"}}')
                        
                        # Preparar datos para el recibo
                        pago_data = {
                            'id': pid,
                            'fecha': ts,
                            'socio': socio['nombre'],
                            'concepto': concepto.strip(),
                            'medio': medio,
                            'monto': monto,
                            'ref_externa': ref if ref else None
                        }
                        
                        # Guardar en session state y activar vista de recibo
                        st.session_state['ultimo_pago'] = pago_data
                        st.session_state['mostrar_recibo'] = True
                        
                        # Rerun para mostrar el recibo
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"No se pudo registrar el pago: {e}")

# ================== LISTADO ==================
with tab_listado:
    st.subheader("Búsqueda")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        desde = st.date_input("Desde", value=date.today() - timedelta(days=7))
    with c2:
        hasta = st.date_input("Hasta", value=date.today())
    with c3:
        q_socio = st.text_input("Socio (nombre contiene)")
    with c4:
        q_medio = st.selectbox("Medio", ["(Todos)"] + MEDIOS)

    c5, c6 = st.columns(2)
    with c5:
        q_concepto = st.text_input("Concepto (contiene)")
    with c6:
        limite = st.selectbox("Límite", [50, 100, 200, 500, 1000], index=2)

    # rango inclusive del día "hasta"
    start = datetime.combine(desde, time.min)
    end = datetime.combine(hasta + timedelta(days=1), time.min)

    sql = """
    SELECT p.id, p.fecha, s.nombre AS socio, p.concepto, p.medio, p.monto, p.ref_externa
    FROM pago p
    JOIN socio s ON s.id = p.socio_id
    WHERE p.fecha >= %s AND p.fecha < %s
    """
    params = [start, end]

    if q_socio.strip():
        sql += " AND s.nombre ILIKE %s"
        params.append(f"%{q_socio}%")
    if q_concepto.strip():
        sql += " AND p.concepto ILIKE %s"
        params.append(f"%{q_concepto}%")
    if q_medio != "(Todos)":
        sql += " AND p.medio = %s"
        params.append(q_medio)

    sql += " ORDER BY p.fecha DESC, p.id DESC LIMIT %s"
    params.append(limite)

    try:
        rows = query(sql, tuple(params))
    except Exception as e:
        st.error(f"Error consultando pagos: {e}")
        rows = []

    # Totales del periodo filtrado
    total = sum(r["monto"] for r in rows) if rows else 0
    st.metric("Total en el periodo (S/)", f"{total:,.2f}")

    if rows:
        st.dataframe(rows, use_container_width=True)

        # Exportar CSV
        csv_data = to_csv(rows, headers=["id", "fecha", "socio", "concepto", "medio", "monto", "ref_externa"])
        st.download_button("⬇️ Exportar CSV", data=csv_data, file_name="pagos.csv", mime="text/csv")

        # Sección para regenerar recibos
        st.divider()
        st.markdown("### 🧾 Regenerar Recibo")
        sel_recibo = st.selectbox(
            "Selecciona el pago para regenerar su recibo",
            rows,
            format_func=lambda r: f"#{r['id']} | {r['fecha']} | {r['socio']} | S/ {r['monto']} | {r['concepto']}"
        )
        
        if st.button("📄 Generar Recibo"):
            pago_data = {
                'id': sel_recibo['id'],
                'fecha': sel_recibo['fecha'],
                'socio': sel_recibo['socio'],
                'concepto': sel_recibo['concepto'],
                'medio': sel_recibo['medio'],
                'monto': sel_recibo['monto'],
                'ref_externa': sel_recibo['ref_externa']
            }
            
            recibo_html = generar_recibo_html(pago_data)
            
            st.download_button(
                label="📄 Descargar Recibo",
                data=recibo_html,
                file_name=f"recibo_{pago_data['id']:06d}.html",
                mime="text/html"
            )
            
            # Mostrar preview del recibo
            with st.expander("👁️ Vista Previa del Recibo"):
                st.components.v1.html(recibo_html, height=400, scrolling=True)

    # Anular / reversar
    if rows:
        # Verificar permisos para reversar
        puede_reversar = False
        try:
            puede_reversar = has_permission("payments_refund")
        except Exception:
            pass
        
        if puede_reversar:
            st.divider()
            st.markdown("### Anular / Reversar pago")
            sel = st.selectbox(
                "Selecciona el pago",
                rows,
                format_func=lambda r: f"#{r['id']} | {r['fecha']} | {r['socio']} | S/ {r['monto']} | {r['medio']} | {r['concepto']}"
            )
            motivo = st.text_input("Motivo de anulación (se registrará en auditoría)")
            if st.button("🧾 Generar reverso (asiento negativo)"):
                try:
                    with db_cursor(commit=True) as cur:
                        # crear contrapartida negativa (no borramos historial)
                        cur.execute("""
                            INSERT INTO pago (socio_id, concepto, monto, medio, ref_externa, fecha)
                            VALUES (
                                (SELECT socio_id FROM pago WHERE id=%s),
                                %s,
                                -(SELECT monto FROM pago WHERE id=%s),
                                'anulacion',
                                %s,
                                now()
                            )
                            RETURNING id
                        """, (sel["id"], f"ANULACIÓN #{sel['id']}: {motivo or sel['concepto']}", sel["id"], f"reversa de #{sel['id']}"))
                        rid = cur.fetchone()["id"]
                        auditoria(cur,
                                  accion="reverso_pago",
                                  entidad="pago",
                                  entidad_id=rid,
                                  detalle=f'{{"reversa_de": {sel["id"]}}}')
                    st.success(f"Pago reversado con asiento #{rid}")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo reversar: {e}")
        else:
            st.info("No tienes permiso para anular/reversar pagos.")
    else:
        st.info("No se encontraron pagos en el periodo seleccionado.")
