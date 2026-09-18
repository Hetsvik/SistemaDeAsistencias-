import altair as alt
import pandas as pd
from datetime import timedelta
import calendar
from datetime import time as dtime
from datetime import datetime
import mysql.connector
import os
import streamlit as st
from zoneinfo import ZoneInfo
from services.google_drive_service import GoogleDriveService
from repositories.attendance_repo import get_attendance_by_worker_and_date, register_entry, register_exit
from repositories.auth_repo import get_user_by_id_and_role, authenticate_user
from services.validador_Archivos import validate_secure_file
from repositories.tareas_repo import (
    get_tasks_by_worker_and_date, update_task_status_by_worker,
    get_all_tasks_for_today, update_task_state_admin, delete_task
)
drive = GoogleDriveService()

# Configuración de página
st.set_page_config(
    page_title="Control de Asistencia Corporativo",
    page_icon="🏢",
    layout="wide",
)

# Estilos CSS personalizados inyectados directamente en Streamlit
st.markdown("""<style>
    /* Fondo principal de la aplicación */
    ./* Fondo principal adaptativo (Soluciona el error visual en modo oscuro) */
    @media (prefers-color-scheme: light) {
        .stAppViewContainer {
            background-color: #F8FAFC;
        }
    }
    
    @media (prefers-color-scheme: dark) {
        /* Adapta el fondo y los botones secundarios al modo oscuro */
        .stAppViewContainer {
            background-color: #0E1117;
        }
        .stButton > button[kind="secondary"] {
            background-color: #1E293B !important;
            border-color: #334155 !important;
        }
        .stButton > button[kind="secondary"] * {
            color: #93C5FD !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background-color: #0F172A !important;
        }
    }
    /* ================= SIDEBAR ================= */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
    }
    /* Texto general del sidebar a blanco (evitando romper botones o códigos) */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div[data-testid="stText"] {
        color: #F8FAFC !important;
    }
    /* Arreglo para la etiqueta del Rol (código markdown) */
    [data-testid="stSidebar"] code {
        color: #0F172A !important;
        background-color: #E2E8F0 !important;
        font-weight: 700 !important;
        padding: 4px 8px !important;
        border-radius: 4px !important;
    }
    /* Arreglo para el botón "Cerrar Sesión" en el Sidebar */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
    }
    [data-testid="stSidebar"] .stButton > button * {
        color: #FCA5A5 !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(239, 68, 68, 0.15) !important;
        border-color: #EF4444 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover * {
        color: #EF4444 !important;
    }

    /* ================= TARJETA INFORMACIÓN EMPRESA ================= */
    .sidebar-company-card {
        background-color: #1E293B !important;
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        padding: 14px !important;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .sidebar-company-name {
        color: #F8FAFC !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        line-height: 1.35 !important;
        margin-bottom: 10px !important;
    }
    .sidebar-company-info {
        color: #94A3B8 !important;
        font-size: 0.82rem !important;
        line-height: 1.4 !important;
    }

    /* ================= BOTONES PRINCIPALES ================= */
    /* Ej: Registrar Entrada (Azul Corporativo) */
    .stButton > button[kind="primary"] {
        background-color: #1E3A8A !important;
        border: none !important;
        border-radius: 8px !important;
    }
    .stButton > button[kind="primary"] * {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
    }

    /* ================= BOTONES SECUNDARIOS ================= */
    /* Ej: Registrar Salida (Blanco con borde azul) */
    .stButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
    }
    .stButton > button[kind="secondary"] * {
        color: #1E3A8A !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #EFF6FF !important;
        border-color: #1E3A8A !important;
    }
    
    /* Logo de la empresa */
    .brand-header {
        display: flex;
        align-items: center;
        padding: 10px 0px 20px 0px;
    }
    .brand-header img {
        max-width: 180px;
        height: auto;
    }
    </style>
""", unsafe_allow_html=True)

# Render del Logo en la esquina del Sidebar
with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except Exception:
        st.markdown("### **EMPRESA**")
        
    # Información formal de la empresa
    st.markdown("""
        <div class="sidebar-company-card">
            <div class="sidebar-company-name">
                🏢 Construcciones Asesoramiento<br>Técnico & Legal S.A.C.
            </div>
            <div class="sidebar-company-info">
                📞 +51 981 173 251
            </div>
            <div class="sidebar-company-info" style="margin-bottom: 8px;">
                ✉️ arqshuan@yahoo.es
            </div>
        </div>
    """, unsafe_allow_html=True)

def now_local():
    """Retorna la fecha y hora actual en zona horaria local (UTC-5)"""
    return datetime.now(ZoneInfo("America/Lima"))

def today_local():
    """Retorna únicamente la fecha de hoy en zona horaria local (UTC-5)"""
    return datetime.now(ZoneInfo("America/Lima")).date()

# -----------------------------------------------------------------------------
# CONEXIÓN A BASE DE DATOS
# -----------------------------------------------------------------------------
def db():
    conn = mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=st.secrets["mysql"]["port"],
    )
    cur = conn.cursor()
    cur.execute("SET time_zone = '-05:00';")
    cur.close()
    return conn

def query(sql, params=(), one=False):
    try:
        conn = db()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        res = cur.fetchone() if one else cur.fetchall()
        cur.close()
        conn.close()
        return res
    except mysql.connector.Error as e:
        st.error(f"❌ Error SQL en la consulta: {e}")
        st.stop()

def execute(sql, params=()):
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        rowid, rowcount = cur.lastrowid, cur.rowcount
        cur.close()
        conn.close()
        return rowid, rowcount
    except mysql.connector.Error as e:
        st.error(f"❌ Error SQL al ejecutar: {e}")
        st.stop()

# -----------------------------------------------------------------------------
# LÓGICA DE COMENTARIOS Y CHAT (CLICKUP STYLE)
# -----------------------------------------------------------------------------
def obtener_comentarios(id_tarea):
    return query(
        "SELECT Autor, Rol, Mensaje, Fecha FROM Comentarios_Tarea WHERE ID_Tarea = %s ORDER BY ID_Comentario ASC",
        (id_tarea,),
    )

def agregar_comentario(id_tarea, autor, rol, mensaje):
    if mensaje and mensaje.strip():
        execute(
            "INSERT INTO Comentarios_Tarea (ID_Tarea, Autor, Rol, Mensaje) VALUES (%s, %s, %s, %s)",
            (id_tarea, autor, rol, mensaje.strip()),
        )

@st.fragment(run_every="10s")
def render_chat_fragment(id_tarea, rol_usuario):
    """Renderiza el chat y se recarga automáticamente cada 10 segundos de forma aislada."""
    comentarios = obtener_comentarios(id_tarea)
    chat_container = st.container(height=200)
    with chat_container:
        if comentarios:
            for c in comentarios:
                st.caption(f"**{c['Autor']} ({c['Rol']})** - {c['Fecha']}")
                st.write(f"└ {c['Mensaje']}")
        else:
            if rol_usuario == "Empleado":
                st.info("No hay mensajes. Usa este espacio para comunicarte con el administrador.")
            else:
                st.info("Inicia la comunicación para dar feedback al empleado.")

# -----------------------------------------------------------------------------
# MANEJO DE SESIÓN Y PERSISTENCIA
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------------------------------------------------------------
# INTERFAZ: LOGIN
# -----------------------------------------------------------------------------
def render_login():
    st.title("⏱️ Sistema de Control de Asistencia y Actividades")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("Iniciar Sesión")
        role = st.selectbox("Perfil de Acceso", ["Empleado", "Administrador"])
        code = st.text_input("Código de Usuario")
        pin = st.text_input("Contraseña de Acceso", type="password")

        if st.button("Ingresar", type="primary", use_container_width=True):
            if not code or not pin:
                st.warning("⚠️ Completa todos los campos.")
                return

            user = authenticate_user(code, pin, role)
            if user:
                st.session_state.user = user
                st.success(f"Bienvenido, {user['name']}")
                st.rerun()
            else:
                st.error("❌ Código, Contraseña o perfil incorrecto.")

# -----------------------------------------------------------------------------
# INTEGRACIÓN GOOGLE DRIVE
# -----------------------------------------------------------------------------
from services.google_drive_service import GoogleDriveService

# Inicializamos el servicio de Google Drive
try:
    drive_service = GoogleDriveService()
except Exception as e:
    drive_service = None

# -----------------------------------------------------------------------------
# VISTAS DE EMPLEADO
# -----------------------------------------------------------------------------
def render_employee_view():
    user = st.session_state.user
    st.title(f"Panel del Empleado — {user['name']}")

    today_date = today_local()

    if "emp_nav" not in st.session_state:
        st.session_state.emp_nav = "🕒 Control de Asistencia"

    nav_options = ["🕒 Control de Asistencia", "📋 Mis Tareas del Día", "👤 Mi Perfil"]
    current_index = (
        nav_options.index(st.session_state.emp_nav)
        if st.session_state.emp_nav in nav_options
        else 0
    )

    selected_tab = st.radio(
        "Navegación",
        nav_options,
        index=current_index,
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.emp_nav = selected_tab
    st.divider()

    # CONTROL DE ASISTENCIA
    if st.session_state.emp_nav == "🕒 Control de Asistencia":
        st.subheader("Marcación de Asistencia Hoy")

        attendance = get_attendance_by_worker_and_date(user["id"], today_date)

        from datetime import time as dtime
        
        if attendance and attendance.get("entry"):
            hora_entrada = attendance["entry"].time()
            limite_tolerancia = dtime(9, 40, 0)
            
            if hora_entrada <= limite_tolerancia:
                st.success("🟢 **A tiempo:** Registraste tu entrada dentro de la tolerancia.")
            else:
                st.error("🔴 **Tardanza:** Registraste tu entrada fuera del límite de las 09:40.")
        else:
            st.warning("⚪ **Pendiente:** Aún no has registrado tu entrada de hoy.")

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric(
                "Entrada Registrada",
                str(attendance["entry"].strftime("%H:%M:%S")) if attendance and attendance.get("entry") else "Pendiente",
            )
        with col_b:
            st.metric(
                "Salida Registrada",
                str(attendance["salida"].strftime("%H:%M:%S")) if attendance and attendance.get("salida") else "Pendiente",
            )

        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "🔴 Registrar Entrada",
                type="primary",
                disabled=bool(attendance),
                use_container_width=True,
            ):
                register_entry(user["id"], now_local().strftime("%Y-%m-%d %H:%M:%S"))
                
                st.success("Entrada registrada con éxito.")
                st.rerun()

        with col2:
            can_exit = attendance is not None and attendance.get("salida") is None
            if st.button("🔵 Registrar Salida", disabled=not can_exit, use_container_width=True):
                
                _, count = register_exit(user["id"], now_local().strftime("%Y-%m-%d %H:%M:%S"), today_date)
                
                if count:
                    st.success("Salida registrada con éxito.")
                    st.rerun()
                else:
                    st.error("No hay entrada activa para hoy.")

    # TAREAS Y FEEDBACK
    elif st.session_state.emp_nav == "📋 Mis Tareas del Día":
        st.subheader("Tareas de Hoy")
        from datetime import datetime # Aseguramos la importación
        curr_dt = now_local().replace(tzinfo=None)

        tasks = query(
            """
            SELECT T.ID_Tarea AS id, P.Nombre_Proyecto AS project, T.Descripcion_Tarea AS description,
                   T.Estado_Tarea AS state, T.Observaciones AS notes,
                   T.Fecha_Inicio AS start_time, T.Fecha_Entrega AS end_time
            FROM Tareas T
            JOIN Proyectos P ON P.ID_Proyecto=T.ID_Proyecto
            WHERE T.ID_Trabajador=%s AND DATE(T.Fecha)=%s
            ORDER BY T.ID_Tarea DESC
            """,
            (user["id"], today_date),
        )

        if tasks:
            # LÓGICA DEL MENSAJE EMERGENTE TOP-LEFT
            tareas_pendientes = [t for t in tasks if t['state'] not in ('Completada', 'Bloqueada') and t['end_time']]
            
            if tareas_pendientes:
                # Encontramos la tarea con la fecha de entrega más cercana
                tarea_proxima = min(tareas_pendientes, key=lambda x: (
                    x["end_time"] if isinstance(x["end_time"], datetime) 
                    else datetime.strptime(str(x["end_time"]), "%Y-%m-%d %H:%M:%S")
                ))
                
                limit_dt = (
                    tarea_proxima["end_time"] 
                    if isinstance(tarea_proxima["end_time"], datetime) 
                    else datetime.strptime(str(tarea_proxima["end_time"]), "%Y-%m-%d %H:%M:%S")
                )
                
                tiempo_restante = limit_dt - curr_dt
                
                if tiempo_restante.total_seconds() > 0:
                    horas, rem = divmod(tiempo_restante.seconds, 3600)
                    minutos, _ = divmod(rem, 60)
                    str_tiempo = f"{tiempo_restante.days} días, {horas}h {minutos}m" if tiempo_restante.days > 0 else f"{horas}h {minutos}m"
                    
                    # Inyección de HTML/CSS para el popup superior izquierdo
                    st.markdown(
                        f"""
                        <div style="
                            position: fixed;
                            top: 60px;
                            left: 20px;
                            background-color: #ff4b4b;
                            color: white;
                            padding: 12px 20px;
                            border-radius: 8px;
                            z-index: 999999;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                            font-family: sans-serif;
                            font-size: 14px;
                            font-weight: bold;
                            border: 1px solid #e03a3a;
                        ">
                            ⏳ Te queda {str_tiempo} para enviar el trabajo ({tarea_proxima['project']})
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


            # RENDERIZADO DE TAREAS
            for task in tasks:
                icon = '✅' if task['state'] == 'Completada' else ('⏸️' if task['state'] == 'Bloqueada' else ('⏳' if task['state'] in ('Enviar a Revisión', 'En Revisión') else '📌'))
                
                with st.expander(f"{icon} {task['project']} - [{task['state']}]"):
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.info(f"📅 **Inicio:** {task['start_time'] or 'Sin definir'}")
                    with col_t2:
                        st.warning(f"⏰ **Límite:** {task['end_time'] or 'Sin definir'}")

                    st.write(f"**Descripción:** {task['description']}")
                    
                    st.divider()

                    # CONTROL DE ESTADO BIDIRECCIONAL
                    if task['state'] == 'Completada':
                        st.success("✅ **Tarea Aprobada y Cerrada.** Esta tarea ya fue validada por la administración y no admite más cambios.")
                    else:
                        st.markdown("#### Actualizar Estado")
                        
                        estados_posibles = ["En Progreso", "Enviar a Revisión"]
                        idx_actual = estados_posibles.index(task['state']) if task['state'] in estados_posibles else 0
                        
                        col_act1, col_act2 = st.columns([3, 1])
                        with col_act1:
                            new_state = st.selectbox(
                                "Seleccione el estado",
                                estados_posibles,
                                index=idx_actual,
                                key=f"st_{task['id']}",
                                label_visibility="collapsed"
                            )
                        with col_act2:
                            update_btn = st.button("Actualizar", key=f"btn_{task['id']}", type="primary", use_container_width=True)

                        if update_btn:
                            final_notes = task["notes"] or ""

                            # Validación de Plazos (Fuera de Plazo)
                            if task["end_time"]:
                                limit_dt_act = (
                                    task["end_time"]
                                    if isinstance(task["end_time"], datetime)
                                    else datetime.strptime(str(task["end_time"]), "%Y-%m-%d %H:%M:%S")
                                )
                                
                                if curr_dt > limit_dt_act:
                                    tag_fuera_plazo = "[ENTREGADO FUERA DE PLAZO]"
                                    if tag_fuera_plazo not in final_notes:
                                        final_notes = f"{tag_fuera_plazo}\n{final_notes}".strip()
                                    st.warning("⚠️ El estado fue actualizado fuera del tiempo límite.")

                            execute(
                                "UPDATE Tareas SET Estado_Tarea=%s, Observaciones=%s WHERE ID_Tarea=%s AND ID_Trabajador=%s",
                                (new_state, final_notes.strip(), task["id"], user["id"]),
                            )
                            st.success("Tarea actualizada correctamente.")
                            st.rerun()
                            
                        st.caption("💡 *Si necesitas explicar un bloqueo o retraso, utiliza el chat de la tarea.*")

                    st.divider()
                    
                    # SECCIÓN DE CHAT Y COMUNICACIÓN
                    st.markdown("💬 **Feedback y Comunicación**")
                    render_chat_fragment(task["id"], "Empleado")

                    # CAMPO ADJUNTO + MENSAJE
                    uploaded_file_emp = st.file_uploader("📎 Adjuntar Archivo o Entregable", key=f"file_emp_{task['id']}")
                    col_msg1, col_msg2 = st.columns([3, 1])
                    with col_msg1:
                        reply_msg = st.text_input("Agregar comentario...", key=f"input_emp_{task['id']}", label_visibility="collapsed")
                    with col_msg2:
                        if st.button("Enviar", key=f"send_emp_{task['id']}", use_container_width=True):
                            file_link = ""
                            bloqueo_seguridad = False
                            
                            if uploaded_file_emp:
                                es_valido, msj_error = validate_secure_file(
                                    uploaded_file_emp.name, 
                                    uploaded_file_emp.type, 
                                    uploaded_file_emp.size
                                )
                                
                                if not es_valido:
                                    st.error(msj_error)
                                    bloqueo_seguridad = True
                                elif drive_service:
                                    file_bytes = uploaded_file_emp.getvalue()
                                    drive_res = drive_service.upload_file(
                                        file_data=file_bytes,
                                        file_name=uploaded_file_emp.name,
                                        mime_type=uploaded_file_emp.type
                                    )
                                    if drive_res and "webViewLink" in drive_res:
                                        file_link = f"\n📎 [Archivo Adjunto: {uploaded_file_emp.name}]({drive_res['webViewLink']})"
                                        st.success("Archivo subido a Google Drive de forma segura.")
                                    else:
                                        st.error("Error en la conexión con Google Drive.")

                            if not bloqueo_seguridad:
                                final_message = (reply_msg + file_link).strip()
                                if final_message:
                                    agregar_comentario(task["id"], user["name"], "Empleado", final_message)
                                    st.rerun()
                                else:
                                    st.warning("Escribe un mensaje o adjunta un archivo antes de enviar.")
        else:
            st.info("No tienes tareas asignadas para el día de hoy.")

    # MI PERFIL (EMPLEADO)
    elif st.session_state.emp_nav == "👤 Mi Perfil":
        st.subheader("🔒 Cambiar Contraseña")
        st.caption("Su nueva contraseña puede incluir letras (mayúsculas y minúsculas), números y caracteres especiales.")
        
        with st.form("emp_change_password"):
            curr_pass = st.text_input("Contraseña Actual", type="password")
            new_pass = st.text_input("Nueva Contraseña", type="password")
            conf_pass = st.text_input("Confirmar Nueva Contraseña", type="password")
            
            if st.form_submit_button("Actualizar Contraseña"):
                if not curr_pass or not new_pass or not conf_pass:
                    st.warning("Debe completar todos los campos.")
                elif new_pass != conf_pass:
                    st.error("La nueva contraseña y la confirmación no coinciden.")
                elif len(new_pass) < 6:
                    st.error("La nueva contraseña debe tener al menos 6 caracteres.")
                elif curr_pass == new_pass:
                    st.error("La nueva contraseña no puede ser igual a la clave actual.")
                else:
                    user_db = query("SELECT PIN_Acceso FROM Trabajadores WHERE ID_Trabajador=%s", (user["id"],), one=True)
                    if user_db and user_db["PIN_Acceso"] == curr_pass:
                        execute("UPDATE Trabajadores SET PIN_Acceso=%s WHERE ID_Trabajador=%s", (new_pass, user["id"]))
                        st.success("✅ Contraseña actualizada con éxito.")
                    else:
                        st.error("❌ La contraseña actual es incorrecta.")
# -----------------------------------------------------------------------------
# VISTAS DE ADMINISTRADOR
# -----------------------------------------------------------------------------
def render_admin_view():
    st.title("⚙️ Panel de Administración")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["📊 Monitoreo", "➕ Asignar Tareas", "👥 Personal", "📁 Proyectos", "👤 Mi Perfil", "📈 Reportes"]
    )

    # MONITOREO ESTILO CLICKUP
    with tab1:
        st.subheader("Asistencia del Día")
        
        # LEFT JOIN para traer a todos los trabajadores activos
        attendance_raw = query(
            """
            SELECT E.Nombre_Completo AS Empleado, 
                   W.Codigo_Trabajador AS Codigo,
                   A.Fecha_Entrada AS Entrada, 
                   A.Fecha_Salida AS Salida
            FROM Trabajadores W
            JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
            LEFT JOIN Asistencia A ON W.ID_Trabajador = A.ID_Trabajador AND A.Fecha_Calculada = CURDATE()
            WHERE E.Estado = 'Activo'
            ORDER BY E.Nombre_Completo
            """
        )

        from datetime import time as dtime
        limite_tolerancia = dtime(9, 40, 0)
        
        tabla_final = []
        if attendance_raw:
            for row in attendance_raw:
                entrada_raw = row["Entrada"]
                salida_raw = row["Salida"]

                if entrada_raw is None:
                    estado = "⚪ Ausente"
                    hora_entrada_str = "—"
                else:
                    hora_val = entrada_raw.time() if hasattr(entrada_raw, 'time') else entrada_raw
                    if hora_val <= limite_tolerancia:
                        estado = "🟢 A tiempo"
                    else:
                        estado = "🔴 Tardanza"
                    hora_entrada_str = entrada_raw.strftime("%H:%M:%S") if hasattr(entrada_raw, 'strftime') else str(entrada_raw)

                hora_salida_str = salida_raw.strftime("%H:%M:%S") if (salida_raw and hasattr(salida_raw, 'strftime')) else "—"

                tabla_final.append({
                    "Empleado": row["Empleado"],
                    "Código": row["Codigo"],
                    "Entrada": hora_entrada_str,
                    "Salida": hora_salida_str,
                    "Estado": estado
                })

        st.dataframe(tabla_final, use_container_width=True)
        st.divider()

        st.subheader("📋 Control de Tareas (ClickUp View)")
        st.subheader("📋 Control de Tareas (ClickUp View)")
        
        # 1. Obtenemos todas las tareas limpiamente desde el repositorio
        tasks_monitoreo = get_all_tasks_for_today()

        if tasks_monitoreo:
            for task in tasks_monitoreo:
                icon = '✅' if task['state'] == 'Completada' else ('⏸️' if task['state'] == 'Bloqueada' else ('⏳' if task['state'] in ('Enviar a Revisión', 'En Revisión') else '📌'))
                
                with st.expander(f"{icon} {task['project']} | {task['emp']} — [{task['state']}]"):
                    st.write(f"**Descripción:** {task['description']}")
                    st.write(f"**Reporte/Entregable del empleado:** {task['notes'] or 'Sin reportes enviados'}")

                    # ESTRUCTURA DE COLUMNAS PARA BOTONES ADMIN
                    col_btn1, col_btn2, col_del = st.columns([2, 2, 1])
                    
                    if task['state'] in ('Enviar a Revisión', 'En Revisión'):
                        with col_btn1:
                            if st.button("✅ Aprobar (Completada)", key=f"approve_{task['id']}", type="primary", use_container_width=True):
                                update_task_state_admin(task["id"], 'Completada')
                                st.rerun()
                        with col_btn2:
                            if st.button("🔄 Rechazar (En Progreso)", key=f"reject_{task['id']}", use_container_width=True):
                                update_task_state_admin(task["id"], 'En Progreso')
                                st.rerun()

                    elif task['state'] in ('En Progreso', 'Asignada'):
                        with col_btn1:
                            if st.button("⏸️ Pausar Tarea", key=f"pause_{task['id']}", use_container_width=True):
                                update_task_state_admin(task["id"], 'Bloqueada')
                                st.rerun()

                    elif task['state'] == 'Bloqueada':
                        with col_btn1:
                            if st.button("▶️ Reanudar (En Progreso)", key=f"resume_{task['id']}", use_container_width=True):
                                update_task_state_admin(task["id"], 'En Progreso')
                                st.rerun()

                    elif task['state'] == 'Completada':
                        with col_btn1:
                            st.success("✅ Tarea Aprobada y Cerrada.")

                    with col_del:
                        if st.button("🗑️", key=f"delete_{task['id']}", use_container_width=True, help="Eliminar tarea"):
                            delete_task(task["id"])
                            st.rerun()
                    st.divider()
                    st.markdown("💬 **Chat de la Tarea**")
                    
                    render_chat_fragment(task["id"], "Administrador")
    
                    # CAMPO ADJUNTO + MENSAJE (ADMIN)
                    uploaded_file_admin = st.file_uploader("📎 Adjuntar Archivo", key=f"file_admin_{task['id']}")
                    col_msg1, col_msg2 = st.columns([3, 1])
                    with col_msg1:
                        nuevo_msg = st.text_input("Instrucciones u observaciones...", key=f"input_admin_{task['id']}", label_visibility="collapsed")
                    with col_msg2:
                        if st.button("Enviar", key=f"send_emp_{task['id']}", use_container_width=True):
                            file_link = ""
                            bloqueo_seguridad = False
                            
                            if uploaded_file_admin:
                                # 1. Ejecutar barrera de seguridad
                                es_valido, msj_error = validate_secure_file(
                                    uploaded_file_admin.name, 
                                    uploaded_file_admin.type, 
                                    uploaded_file_admin.size
                                )
                                
                                if not es_valido:
                                    st.error(msj_error)
                                    bloqueo_seguridad = True
                                elif drive_service:
                                    # 2. Si es válido, recién lo enviamos a la nube
                                    file_bytes = uploaded_file_admin.getvalue()
                                    drive_res = drive_service.upload_file(
                                        file_data=file_bytes,
                                        file_name=uploaded_file_admin.name,
                                        mime_type=uploaded_file_admin.type
                                    )
                                    if drive_res and "webViewLink" in drive_res:
                                        file_link = f"\n📎 [Archivo Adjunto: {uploaded_file_admin.name}]({drive_res['webViewLink']})"
                                        st.success("Archivo subido a Google Drive de forma segura.")
                                    else:
                                        st.error("Error en la conexión con Google Drive.")

                            # Solo se envía el mensaje a MySQL si no hubo un bloqueo de seguridad
                            if not bloqueo_seguridad:
                                final_message = (nuevo_msg + file_link).strip()
                                if final_message:
                                    agregar_comentario(task["id"], st.session_state.user["name"], "Administrador", final_message)
                                    st.rerun()
                                else:
                                    st.warning("Escribe un mensaje o adjunta un archivo antes de enviar.")
        else:
            st.info("No hay tareas registradas hoy.")

    # ASIGNAR TAREAS
    with tab2:
        st.subheader("Nueva Tarea para un Empleado")
        workers = query(
            """
            SELECT W.ID_Trabajador AS id, E.Nombre_Completo AS name 
            FROM Trabajadores W
            JOIN Empleados E ON E.ID_Empleado=W.ID_Empleado
            WHERE E.Estado='Activo'
            ORDER BY E.Nombre_Completo
            """
        )
        projects = query("SELECT ID_Proyecto AS id, Nombre_Proyecto AS name FROM Proyectos ORDER BY Nombre_Proyecto")

        if workers and projects:
            w_dict = {w["name"]: w["id"] for w in workers}
            p_dict = {p["name"]: p["id"] for p in projects}

            selected_w = st.selectbox("Trabajador", list(w_dict.keys()))
            selected_p = st.selectbox("Proyecto", list(p_dict.keys()))

            col_in1, col_in2 = st.columns(2)
            with col_in1:
                f_inicio_date = st.date_input("Fecha de Inicio", value=today_local())
            with col_in2:
                f_inicio_time = st.time_input("Hora de Inicio")

            col_en1, col_en2 = st.columns(2)
            with col_en1:
                f_entrega_date = st.date_input("Fecha de Entrega", value=today_local())
            with col_en2:
                f_entrega_time = st.time_input("Hora de Entrega")

            desc = st.text_area("Descripción")

            if st.button("Asignar Tarea"):
                if not desc.strip():
                    st.warning("Escribe una descripción.")
                else:
                    dt_inicio = datetime.combine(f_inicio_date, f_inicio_time)
                    dt_entrega = datetime.combine(f_entrega_date, f_entrega_time)

                    if dt_entrega < dt_inicio:
                        st.error("❌ La fecha de entrega no puede ser anterior a la de inicio.")
                    else:
                        execute(
                            """
                            INSERT INTO Tareas (ID_Trabajador, ID_Administrador_Asignador, ID_Proyecto, Descripcion_Tarea, Estado_Tarea, Fecha_Inicio, Fecha_Entrega, Fecha)
                            VALUES (%s, %s, %s, %s, 'Asignada', %s, %s, CURDATE())
                            """,
                            (
                                w_dict[selected_w],
                                st.session_state.user["id"],
                                p_dict[selected_p],
                                desc.strip(),
                                # 'Asignada' ahora está hardcodeado en la consulta SQL
                                dt_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                                dt_entrega.strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                        )
                        st.success("Tarea asignada exitosamente.")
                        st.rerun()
    with tab3:
        st.subheader("➕ Registrar Nuevo Trabajador")
        with st.form("form_worker"):
            col_reg1, col_reg2 = st.columns(2)
            with col_reg1:
                name = st.text_input("Nombre Completo *")
                email = st.text_input("Correo Electrónico (Opcional)")
                position = st.text_input("Cargo / Puesto *")
            with col_reg2:
                phone = st.text_input("Teléfono (Opcional)")
                code = st.text_input("Código de Trabajador * (Ej: TRAB01)")
                pin = st.text_input("Contraseña Inicial *", type="password")
            
            st.caption("Los campos marcados con (*) son obligatorios.")
            submitted = st.form_submit_button("Registrar Trabajador")

            if submitted:
                if not all([name, position, code, pin]):
                    st.warning("⚠️ Completa todos los datos obligatorios.")
                elif len(pin) < 4:
                    st.warning("⚠️ La contraseña inicial debe tener al menos 4 caracteres.")
                else:
                    try:
                        emp_id, _ = execute(
                            "INSERT INTO Empleados (Nombre_Completo, Correo, Telefono, Estado) VALUES (%s, %s, %s, 'Activo')",
                            (name.strip(), email.strip() if email else None, phone.strip() if phone else None),
                        )
                        execute(
                            "INSERT INTO Trabajadores (ID_Empleado, Rol_Cargo, Codigo_Trabajador, PIN_Acceso) VALUES (%s, %s, %s, %s)",
                            (emp_id, position.strip(), code.strip().upper(), pin.strip()),
                        )
                        st.success("✅ Trabajador registrado con éxito.")
                        st.rerun()
                    except Exception:
                        st.error("❌ El código de trabajador ya existe en la base de datos.")

        st.divider()

        # MÓDULO: MODIFICAR / ACTUALIZAR EMPLEADO
        st.subheader("✏️ Editar Datos del Personal")
        
        edit_workers = query("""
            SELECT W.ID_Trabajador AS id, W.ID_Empleado AS emp_id, E.Nombre_Completo,
                   E.Correo, E.Telefono, W.Rol_Cargo, W.Codigo_Trabajador, E.Estado
            FROM Trabajadores W
            JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
            ORDER BY E.Nombre_Completo
        """)

        if edit_workers:
            worker_options = {f"{w['Codigo_Trabajador']} - {w['Nombre_Completo']}": w for w in edit_workers}
            selected_edit = st.selectbox("🔍 Buscar empleado a modificar:", list(worker_options.keys()))
            current_w = worker_options[selected_edit]

            with st.form("form_edit_worker"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    new_name = st.text_input("Nombre Completo", value=current_w["Nombre_Completo"])
                    new_email = st.text_input("Correo Electrónico", value=current_w["Correo"] if current_w["Correo"] else "", key=f"email_{current_w['emp_id']}")
                    new_code = st.text_input("Código de Trabajador", value=current_w["Codigo_Trabajador"])
                with col_e2:
                    new_position = st.text_input("Cargo / Puesto", value=current_w["Rol_Cargo"])
                    new_phone = st.text_input("Teléfono", value=current_w["Telefono"] if current_w["Telefono"] else "", key=f"phone_{current_w['emp_id']}")
                    new_status = st.selectbox("Estado en la Empresa", ["Activo", "Inactivo"], index=0 if current_w["Estado"] == "Activo" else 1)

                new_pin = st.text_input("Nueva Contraseña (Déjalo en blanco si no deseas cambiarla)", type="password")

                submit_edit = st.form_submit_button("Actualizar Datos")

                if submit_edit:
                    if not all([new_name.strip(), new_position.strip(), new_code.strip()]):
                        st.warning("⚠️ El nombre, cargo y código no pueden estar vacíos.")
                    else:
                        try:
                            # 1. Actualizamos datos personales en la tabla Empleados
                            execute(
                                "UPDATE Empleados SET Nombre_Completo=%s, Correo=%s, Telefono=%s, Estado=%s WHERE ID_Empleado=%s",
                                (new_name.strip(), new_email.strip() if new_email else None, new_phone.strip() if new_phone else None, new_status, current_w["emp_id"])
                            )
                            
                            # 2. Actualizamos datos laborales en Trabajadores (con o sin PIN)
                            if new_pin.strip():
                                execute(
                                    "UPDATE Trabajadores SET Rol_Cargo=%s, Codigo_Trabajador=%s, PIN_Acceso=%s WHERE ID_Trabajador=%s",
                                    (new_position.strip(), new_code.strip().upper(), new_pin.strip(), current_w["id"])
                                )
                            else:
                                execute(
                                    "UPDATE Trabajadores SET Rol_Cargo=%s, Codigo_Trabajador=%s WHERE ID_Trabajador=%s",
                                    (new_position.strip(), new_code.strip().upper(), current_w["id"])
                                )
                            
                            st.success(f"✅ Datos de {new_name} actualizados correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al actualizar: Es posible que el código '{new_code}' ya pertenezca a otro trabajador.")

        st.divider()

        # NUEVO MÓDULO: DAR DE BAJA / RETIRAR EMPLEADO
        st.subheader("🗑️ Retirar Empleado del Sistema")
        
        if edit_workers: # Reutilizamos la consulta previa por eficiencia
            del_options = {f"{w['Codigo_Trabajador']} - {w['Nombre_Completo']}": w['emp_id'] for w in edit_workers}
            
            empleado_seleccionado = st.selectbox(
                "Selecciona el empleado que deseas eliminar:",
                options=list(del_options.keys()),
                index=None,
                placeholder="Elige un empleado..."
            )
            
            if empleado_seleccionado:
                id_a_eliminar = del_options[empleado_seleccionado]
                
                st.warning(f"⚠️ **Atención:** Estás a punto de eliminar a **{empleado_seleccionado}**. Esta acción es irreversible y, por las reglas de integridad de la base de datos, borrará automáticamente su historial de asistencias y tareas asociadas.")
                
                confirmacion = st.checkbox("Comprendo las consecuencias, habilitar eliminación.")
                
                if confirmacion:
                    if st.button("🗑️ Eliminar Empleado Definitivamente", type="primary"):
                        try:
                            # Por seguridad y soporte de claves foráneas, borramos primero en Trabajadores y luego en Empleados
                            execute("DELETE FROM Trabajadores WHERE ID_Empleado = %s", (id_a_eliminar,))
                            execute("DELETE FROM Empleados WHERE ID_Empleado = %s", (id_a_eliminar,))
                            
                            st.success(f"✅ El empleado ha sido retirado exitosamente de Clever Cloud.")
                            st.rerun() 
                            
                        except Exception as e:
                            st.error(f"❌ Error al eliminar. Verifica si existen registros huérfanos que impiden el borrado: {e}")
        else:
            st.info("No hay empleados registrados actualmente en el sistema.")

        st.divider()

        # LISTADO ACTUALIZADO
        st.subheader("📋 Listado de Personal")
        people = query(
            """
            SELECT W.Codigo_Trabajador AS Código, E.Nombre_Completo AS Nombre, W.Rol_Cargo AS Cargo,
                   COALESCE(E.Correo, 'Sin registrar') AS Correo, 
                   COALESCE(E.Telefono, 'Sin registrar') AS Teléfono, E.Estado
            FROM Trabajadores W
            JOIN Empleados E ON E.ID_Empleado=W.ID_Empleado 
            ORDER BY E.Nombre_Completo
            """
        )
        st.dataframe(people, use_container_width=True)
    # GESTIÓN DE PROYECTOS
    with tab4:
        st.subheader("Registrar Nuevo Proyecto")
        with st.form("form_project"):
            p_name = st.text_input("Nombre del Proyecto")
            p_area = st.text_input("Área / Departamento")
            p_submitted = st.form_submit_button("Crear Proyecto")

            if p_submitted:
                if not p_name.strip() or not p_area.strip():
                    st.warning("Ingresa el nombre y área del proyecto.")
                else:
                    execute(
                        "INSERT INTO Proyectos (Nombre_Proyecto, Area_Departamento) VALUES (%s, %s)",
                        (p_name.strip(), p_area.strip()),
                    )
                    st.success("Proyecto creado.")
                    st.rerun()

        st.divider()
        st.subheader("Lista de Proyectos")
            
        # 1. Realizar la consulta a la base de datos y guardarla en una variable
        proyectos_lista = query("SELECT ID_Proyecto AS ID, Nombre_Proyecto AS Proyecto, Area_Departamento AS Área FROM Proyectos ORDER BY ID_Proyecto DESC")
        
        cols_header = st.columns([1, 3, 3, 1])
        cols_header[0].write("**ID**")
        cols_header[1].write("**Proyecto**")
        cols_header[2].write("**Área**")
        cols_header[3].write("")
        st.divider()
        
        # 2. Iterar sobre la variable proyectos_lista, no sobre la función query
        if proyectos_lista:
            for p in proyectos_lista:
                c1, c2, c3, c4 = st.columns([1, 3, 3, 1])
                c1.write(p['ID'])
                c2.write(p['Proyecto'])
                c3.write(p['Área'])
                
                # Botón para eliminar (usamos el ID del proyecto como llave única)
                if c4.button("🗑️", key=f"btn_del_proj_{p['ID']}"):
                    try:
                        execute("DELETE FROM Proyectos WHERE ID_Proyecto = %s", (p['ID'],))
                        st.success(f"Proyecto eliminado exitosamente.")
                        st.rerun()
                    except Exception as e:
                        # 3. Manejo del error si el proyecto ya tiene tareas asignadas
                        st.error("❌ No se puede eliminar este proyecto porque ya tiene tareas asignadas en el sistema.")
        else:
            st.info("No hay proyectos registrados actualmente.")

    # MI PERFIL (ADMINISTRADOR)
    with tab5:
        st.subheader("🔒 Cambiar Contraseña de Administrador")
        st.caption("Su nueva contraseña puede incluir letras (mayúsculas y minúsculas), números y caracteres especiales.")
        
        with st.form("admin_change_password"):
            curr_pass = st.text_input("Contraseña Actual", type="password")
            new_pass = st.text_input("Nueva Contraseña", type="password")
            conf_pass = st.text_input("Confirmar Nueva Contraseña", type="password")
            
            if st.form_submit_button("Actualizar Contraseña"):
                if not curr_pass or not new_pass or not conf_pass:
                    st.warning("Debe completar todos los campos.")
                elif new_pass != conf_pass:
                    st.error("La nueva contraseña y la confirmación no coinciden.")
                elif len(new_pass) < 6:
                    st.error("La nueva contraseña debe tener al menos 6 caracteres.")
                elif curr_pass == new_pass:
                    st.error("La nueva contraseña no puede ser igual a la clave actual.")
                else:
                    user_db = query("SELECT PIN_Acceso FROM Administrador WHERE ID_Administrador=%s", (st.session_state.user["id"],), one=True)
                    if user_db and user_db["PIN_Acceso"] == curr_pass:
                        execute("UPDATE Administrador SET PIN_Acceso=%s WHERE ID_Administrador=%s", (new_pass, st.session_state.user["id"]))
                        st.success("✅ Contraseña actualizada con éxito.")
                    else:
                        st.error("❌ La contraseña actual es incorrecta.")


   # REPORTES ANALÍTICOS Y KARDEX DE EMPLEADO
    with tab6:
        st.subheader("📈 Reporte Analítico de Rendimiento")
        
        workers_report = query("""
            SELECT W.ID_Trabajador AS id, E.Nombre_Completo AS name, W.Codigo_Trabajador AS code
            FROM Trabajadores W
            JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
            WHERE E.Estado = 'Activo' ORDER BY E.Nombre_Completo
        """)
        
        if workers_report:
            col_filt1, col_filt2 = st.columns(2)
            with col_filt1:
                w_dict_rep = {f"{w['code']} - {w['name']}": w["id"] for w in workers_report}
                selected_worker_rep = st.selectbox("👤 Seleccionar Empleado:", list(w_dict_rep.keys()))
            
            with col_filt2:
                rango_tiempo = st.selectbox("📅 Periodo de Evaluación:", ["Esta Semana", "Este Mes", "Mes Anterior"])
            
            worker_id_rep = w_dict_rep[selected_worker_rep]
            
            hoy = today_local()
            if rango_tiempo == "Esta Semana":
                inicio_fecha = hoy - timedelta(days=hoy.weekday())
                fin_fecha = inicio_fecha + timedelta(days=6)
            elif rango_tiempo == "Este Mes":
                inicio_fecha = hoy.replace(day=1)
                ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                fin_fecha = hoy.replace(day=ultimo_dia)
            else:
                primer_dia_mes_actual = hoy.replace(day=1)
                fin_fecha = primer_dia_mes_actual - timedelta(days=1)
                inicio_fecha = fin_fecha.replace(day=1)

            st.caption(f"Visualizando datos desde **{inicio_fecha.strftime('%d/%m/%Y')}** hasta **{fin_fecha.strftime('%d/%m/%Y')}**")
            
            if st.button("📊 Generar Reporte", type="primary"):
                # 1. Ejecutar las consultas SQL optimizadas
                kpi_asistencia = query("""
                    SELECT 
                        COUNT(*) AS total_dias,
                        SUM(CASE WHEN TIME(Fecha_Entrada) <= '09:40:00' THEN 1 ELSE 0 END) AS a_tiempo,
                        SUM(CASE WHEN TIME(Fecha_Entrada) > '09:40:00' THEN 1 ELSE 0 END) AS tardanzas
                    FROM Asistencia 
                    WHERE ID_Trabajador = %s AND Fecha_Calculada BETWEEN %s AND %s
                """, (worker_id_rep, inicio_fecha, fin_fecha))
                
                kpi_tareas = query("""
                    SELECT 
                        COUNT(*) AS total_tareas,
                        SUM(CASE WHEN Estado_Tarea = 'Completada' THEN 1 ELSE 0 END) AS completadas
                    FROM Tareas 
                    WHERE ID_Trabajador = %s AND Fecha BETWEEN %s AND %s
                """, (worker_id_rep, inicio_fecha, fin_fecha))

                # 2. Guardar los resultados en session_state para que no se borren
                st.session_state.reporte_actual = {
                    "id_trabajador": worker_id_rep,
                    "nombre": selected_worker_rep.split('-')[1].strip(),
                    "rango": rango_tiempo,
                    "inicio": inicio_fecha,
                    "fin": fin_fecha,
                    "tot_asistencias": int(kpi_asistencia[0]['total_dias'] or 0) if kpi_asistencia else 0,
                    "a_tiempo": int(kpi_asistencia[0]['a_tiempo'] or 0) if kpi_asistencia else 0,
                    "tardanzas": int(kpi_asistencia[0]['tardanzas'] or 0) if kpi_asistencia else 0,
                    "tot_tareas": int(kpi_tareas[0]['total_tareas'] or 0) if kpi_tareas else 0,
                    "completadas": int(kpi_tareas[0]['completadas'] or 0) if kpi_tareas else 0,
                }
                st.session_state.reporte_actual["eficiencia"] = round((st.session_state.reporte_actual["completadas"] / st.session_state.reporte_actual["tot_tareas"] * 100), 1) if st.session_state.reporte_actual["tot_tareas"] > 0 else 0.0

            # 3. RENDERIZADO DEL REPORTE SI EXISTE EN MEMORIA
            if "reporte_actual" in st.session_state and st.session_state.reporte_actual["id_trabajador"] == worker_id_rep:
                rep = st.session_state.reporte_actual
                
                st.divider()
                st.markdown(f"### 📈 Resultados de {rep['nombre']}")
                
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric(label="Llegadas a Tiempo", value=f"🟢 {rep['a_tiempo']}")
                kpi2.metric(label="Tardanzas", value=f"🔴 {rep['tardanzas']}")
                kpi3.metric(label="Tareas Completadas", value=f"✅ {rep['completadas']} / {rep['tot_tareas']}")
                kpi4.metric(label="Eficiencia", value=f"⚡ {rep['eficiencia']}%")
                
                st.write("")
                col_graf, col_det = st.columns([1, 1])
                
                with col_graf:
                    st.markdown("#### Distribución de Tareas")
                    graf_tareas = query("""
                        SELECT Estado_Tarea, COUNT(*) AS Cantidad 
                        FROM Tareas 
                        WHERE ID_Trabajador = %s AND Fecha BETWEEN %s AND %s 
                        GROUP BY Estado_Tarea
                    """, (worker_id_rep, rep['inicio'], rep['fin']))
                    
                    if graf_tareas:
                        import altair as alt
                        import pandas as pd
                        df_graf = pd.DataFrame(graf_tareas)
                        chart = alt.Chart(df_graf).mark_bar(color="#c5a880").encode(
                            x=alt.X('Estado_Tarea', title="", axis=alt.Axis(labelAngle=0)),
                            y=alt.Y('Cantidad', title="Cantidad de Tareas"),
                            tooltip=['Estado_Tarea', 'Cantidad']
                        ).properties(height=300)
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("No hay datos suficientes para graficar.")
                        
                with col_det:
                    st.markdown(f"#### Registro de Tareas ({rep['rango']})")
                    tareas_periodo = query("""
                        SELECT P.Nombre_Proyecto AS Proyecto, T.Descripcion_Tarea AS Tarea, T.Estado_Tarea AS Estado
                        FROM Tareas T
                        JOIN Proyectos P ON T.ID_Proyecto = P.ID_Proyecto
                        WHERE T.ID_Trabajador = %s AND T.Fecha BETWEEN %s AND %s
                        ORDER BY T.Fecha DESC
                    """, (worker_id_rep, rep['inicio'], rep['fin']))
                    
                    if tareas_periodo:
                        st.dataframe(pd.DataFrame(tareas_periodo), use_container_width=True, hide_index=True)
                    else:
                        st.info("Sin tareas asignadas en este periodo.")

                # 4. BOTÓN PARA GUARDAR LA FOTOGRAFÍA OFICIAL
                st.divider()
                st.info("💡 Si este reporte corresponde a un cierre de mes o evaluación oficial, puedes guardarlo permanentemente en el sistema.")
                if st.button("💾 Guardar Reporte Oficial en Base de Datos"):
                    try:
                        execute("""
                            INSERT INTO Evaluaciones_Rendimiento 
                            (ID_Trabajador, ID_Administrador, Periodo_Texto, Fecha_Inicio, Fecha_Fin, Total_Asistencias, Llegadas_Tiempo, Tardanzas, Total_Tareas, Tareas_Completadas, Eficiencia_Porcentaje)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            rep['id_trabajador'],
                            st.session_state.user["id"],
                            rep['rango'],
                            rep['inicio'].strftime('%Y-%m-%d'),
                            rep['fin'].strftime('%Y-%m-%d'),
                            rep['tot_asistencias'],
                            rep['a_tiempo'],
                            rep['tardanzas'],
                            rep['tot_tareas'],
                            rep['completadas'],
                            rep['eficiencia']
                        ))
                        st.success("✅ Reporte oficial guardado correctamente.")
                        # Limpiamos la sesión tras guardar para reiniciar el flujo
                        del st.session_state.reporte_actual
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar el reporte: {e}")
        else:
            st.info("No hay empleados activos en el sistema.")
# -----------------------------------------------------------------------------
# CONTROL DE FLUJO PRINCIPAL Y NOTIFICACIONES
# -----------------------------------------------------------------------------
if st.session_state.user is None:
    render_login()
else:
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['name']}**")
        st.write(f"💼 Rol: `{st.session_state.user['role']}`")
        st.divider()

        today_date = today_local()

        if st.session_state.user["role"] == "Empleado":
            notificaciones = query(
                """
                SELECT P.Nombre_Proyecto AS project, T.Descripcion_Tarea AS descr
                FROM Tareas T
                JOIN Proyectos P ON P.ID_Proyecto = T.ID_Proyecto
                WHERE T.ID_Trabajador = %s AND T.Estado_Tarea = 'Asignada' AND T.Fecha = %s
                ORDER BY T.ID_Tarea DESC
                """,
                (st.session_state.user["id"], today_date),
            )
        elif st.session_state.user["role"] == "Administrador":
            notificaciones = query(
                """
                SELECT E.Nombre_Completo AS emp, P.Nombre_Proyecto AS project, 
                       T.Descripcion_Tarea AS descr, T.Observaciones AS notes
                FROM Tareas T
                JOIN Trabajadores W ON W.ID_Trabajador = T.ID_Trabajador
                JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
                JOIN Proyectos P ON P.ID_Proyecto = T.ID_Proyecto
                WHERE T.Estado_Tarea = 'Completada' AND T.Fecha = %s
                ORDER BY T.ID_Tarea DESC
                """,
                (today_date,),
            )
        else:
            notificaciones = []

        cantidad = len(notificaciones) if notificaciones else 0
        titulo_campana = f"🔔 Notificaciones ({cantidad})" if cantidad > 0 else "🔔 Notificaciones"

        with st.expander(titulo_campana):
            if cantidad > 0:
                for i, notif in enumerate(notificaciones):
                    if st.session_state.user["role"] == "Empleado":
                        if st.button(
                            f"📌 {notif['project']}\n\n{notif['descr']}",
                            key=f"notif_emp_{i}_{notif['project']}",
                        ):
                            st.session_state.emp_nav = "📋 Mis Tareas del Día"
                            st.rerun()
                    else:
                        es_fuera_de_plazo = bool(
                            notif.get("notes") and "[ENTREGADO FUERA DE PLAZO]" in notif["notes"]
                        )
                        if es_fuera_de_plazo:
                            st.error(
                                f"⚠️ **ENTREGA FUERA DE PLAZO**\n\n"
                                f"**{notif['emp']}** envió su reporte a destiempo.\n\n"
                                f"📌 **Proyecto:** {notif['project']}\n"
                                f"📝 **Tarea:** {notif['descr']}"
                            )
                        else:
                            mensaje = f"✅ **{notif['emp']}** completó a tiempo:\n\n📌 {notif['project']} - {notif['descr']}"
                            st.success(mensaje)
            else:
                st.write("No hay notificaciones nuevas.")

        st.divider()

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

    if st.session_state.user["role"] == "Empleado":
            render_employee_view()
    elif st.session_state.user["role"] == "Administrador":
            render_admin_view()