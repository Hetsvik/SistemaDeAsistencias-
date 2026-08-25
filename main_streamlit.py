from datetime import datetime
import mysql.connector
import streamlit as st
from zoneinfo import ZoneInfo

# Configuración de página
st.set_page_config(
    page_title="Control de Asistencia Corporativo",
    page_icon="🏢",
    layout="wide",
)

# Estilos CSS personalizados inyectados directamente en Streamlit
st.markdown("""<style>
    /* Fondo principal de la aplicación */
    .stAppViewContainer {
        background-color: #F8FAFC;
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
        
    # Información formal de la empresa (Siguiendo buenas prácticas de marcado)
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

# -----------------------------------------------------------------------------
# MANEJO DE SESIÓN Y PERSISTENCIA (F5)
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None and "user_id" in st.query_params:
    saved_id = st.query_params["user_id"]
    saved_role = st.query_params.get("role")

    if saved_role == "Administrador":
        user_data = query(
            """
            SELECT A.ID_Administrador AS id, E.Nombre_Completo AS name, 'Administrador' AS role
            FROM Administrador A
            JOIN Empleados E ON E.ID_Empleado = A.ID_Empleado
            WHERE A.ID_Administrador = %s
            """,
            (saved_id,),
            one=True,
        )
    elif saved_role == "Empleado":
        user_data = query(
            """
            SELECT W.ID_Trabajador AS id, E.Nombre_Completo AS name, 'Empleado' AS role
            FROM Trabajadores W
            JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
            WHERE W.ID_Trabajador = %s
            """,
            (saved_id,),
            one=True,
        )
    else:
        user_data = None

    if user_data:
        st.session_state.user = user_data

def login(code, pin, role):
    code = code.strip().upper()
    pin = pin.strip()

    if role in ("Empleado", "Trabajador"):
        user = query(
            """
            SELECT T.ID_Trabajador AS id, E.Nombre_Completo AS name,
                   T.Rol_Cargo AS position, T.Codigo_Trabajador AS code,
                   'Empleado' AS role
            FROM Trabajadores T
            JOIN Empleados E ON E.ID_Empleado=T.ID_Empleado
            WHERE UPPER(T.Codigo_Trabajador)=%s
                AND T.PIN_Acceso=%s
                AND E.Estado='Activo'
            """,
            (code, pin),
            one=True,
        )
    elif role == "Administrador":
        user = query(
            """
            SELECT A.ID_Administrador AS id, E.Nombre_Completo AS name, 'Administrador' AS position,
                A.Codigo_Administrador AS code,
                'Administrador' AS role
            FROM Administrador A
            JOIN Empleados E ON E.ID_Empleado=A.ID_Empleado
            WHERE UPPER(A.Codigo_Administrador)=%s
                AND A.PIN_Acceso=%s
                AND E.Estado='Activo'
            """,
            (code, pin),
            one=True,
        )
    else:
        return None

    return user

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
        pin = st.text_input("PIN de Acceso", type="password")

        if st.button("Ingresar", type="primary", use_container_width=True):
            if not code or not pin:
                st.warning("⚠️ Completa todos los campos.")
                return

            user = login(code, pin, role)
            if user:
                st.session_state.user = user
                st.query_params["user_id"] = str(user["id"])
                st.query_params["role"] = user["role"]
                st.success(f"Bienvenido, {user['name']}")
                st.rerun()
            else:
                st.error("❌ Código, PIN o perfil incorrecto.")

# -----------------------------------------------------------------------------
# VISTAS DE EMPLEADO
# -----------------------------------------------------------------------------
def render_employee_view():
    user = st.session_state.user
    st.title(f"Panel del Empleado — {user['name']}")

    today_date = today_local()

    if "emp_nav" not in st.session_state:
        st.session_state.emp_nav = "🕒 Control de Asistencia"

    nav_options = ["🕒 Control de Asistencia", "📋 Mis Tareas del Día"]
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

        attendance = query(
            """
            SELECT ID_Asistencia AS id, Fecha_Entrada AS entry, Fecha_Salida AS salida
            FROM Asistencia
            WHERE ID_Trabajador = %s AND DATE(Fecha_Entrada) = %s
            ORDER BY ID_Asistencia DESC
            """,
            (user["id"], today_date),
            one=True,
        )

        from datetime import time as dtime
        
        if attendance and attendance.get("entry"):
            hora_entrada = attendance["entry"].time()
            limite_tolerancia = dtime(9, 20, 0)
            
            if hora_entrada <= limite_tolerancia:
                st.success(f"🟢 **A tiempo:** Registraste tu entrada dentro de la tolerancia.")
            else:
                st.error(f"🔴 **Tardanza:** Registraste tu entrada fuera del límite de las 09:20.")
        else:
            st.warning(f"⚪ **Pendiente:** Aún no has registrado tu entrada de hoy.")

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
                execute(
                    "INSERT INTO Asistencia (ID_Trabajador, Fecha_Entrada) VALUES (%s, %s)",
                    (user["id"], now_local().strftime("%Y-%m-%d %H:%M:%S")),
                )
                st.success("Entrada registrada con éxito.")
                st.rerun()

        with col2:
            can_exit = attendance is not None and attendance.get("salida") is None
            if st.button("🔵 Registrar Salida", disabled=not can_exit, use_container_width=True):
                _, count = execute(
                    """
                    UPDATE Asistencia 
                    SET Fecha_Salida = %s
                    WHERE ID_Trabajador = %s AND DATE(Fecha_Entrada) = %s AND Fecha_Salida IS NULL
                    """,
                    (
                        now_local().strftime("%Y-%m-%d %H:%M:%S"),
                        user["id"],
                        today_date,
                    ),
                )
                if count:
                    st.success("Salida registrada con éxito.")
                    st.rerun()
                else:
                    st.error("No hay entrada activa para hoy.")

    # TAREAS Y FEEDBACK
    elif st.session_state.emp_nav == "📋 Mis Tareas del Día":
        st.subheader("Tareas de Hoy")
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
            for task in tasks:
                with st.expander(f"📌 {task['project']} - [{task['state']}]"):
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.info(f"📅 **Inicio:** {task['start_time'] or 'Sin definir'}")
                    with col_t2:
                        st.warning(f"⏰ **Límite:** {task['end_time'] or 'Sin definir'}")

                    st.write(f"**Descripción:** {task['description']}")
                    st.write(f"**Observaciones previas:** {task['notes'] or 'Ninguna'}")

                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        new_state = st.selectbox(
                            "Actualizar Estado",
                            ["Asignada", "En Progreso", "Completada", "Bloqueada"],
                            key=f"st_{task['id']}",
                        )
                    with col_act2:
                        new_notes = st.text_input(
                            "Observaciones adicionales (Opcional)",
                            value="",
                            key=f"nt_{task['id']}",
                        )

                    if st.button("Actualizar Tarea", key=f"btn_{task['id']}", use_container_width=True):
                        if new_state == "Bloqueada" and not new_notes.strip():
                            st.warning("Debes ingresar una observación si bloqueas la tarea.")
                        else:
                            final_notes = task["notes"] or ""

                            if new_notes.strip():
                                final_notes += f"\nNote: {new_notes.strip()}"

                            if task["end_time"]:
                                limit_dt = (
                                    task["end_time"]
                                    if isinstance(task["end_time"], datetime)
                                    else datetime.strptime(str(task["end_time"]), "%Y-%m-%d %H:%M:%S")
                                )
                                curr_dt = now_local().replace(tzinfo=None)

                                if curr_dt > limit_dt:
                                    tag_fuera_plazo = "[ENTREGADO FUERA DE PLAZO]"
                                    if tag_fuera_plazo not in final_notes:
                                        final_notes = f"{tag_fuera_plazo} {final_notes}".strip()
                                    st.warning("⚠️ El reporte fue enviado fuera del tiempo límite.")

                            execute(
                                "UPDATE Tareas SET Estado_Tarea=%s, Observaciones=%s WHERE ID_Tarea=%s AND ID_Trabajador=%s",
                                (new_state, final_notes.strip(), task["id"], user["id"]),
                            )
                            st.success("Tarea actualizada correctamente.")
                            st.rerun()

                    st.divider()
                    st.markdown("💬 **Feedback y Comunicación**")
                    comentarios = obtener_comentarios(task["id"])
                    chat_container = st.container(height=200)
                    with chat_container:
                        if comentarios:
                            for c in comentarios:
                                st.caption(f"**{c['Autor']} ({c['Rol']})** - {c['Fecha']}")
                                st.write(f"└ {c['Mensaje']}")
                        else:
                            st.info("No hay mensajes. Usa este espacio para comunicarte con el administrador.")

                    col_msg1, col_msg2 = st.columns([3, 1])
                    with col_msg1:
                        reply_msg = st.text_input("Agregar comentario...", key=f"input_emp_{task['id']}", label_visibility="collapsed")
                    with col_msg2:
                        if st.button("Enviar", key=f"send_emp_{task['id']}", use_container_width=True):
                            agregar_comentario(task["id"], user["name"], "Empleado", reply_msg)
                            st.rerun()
        else:
            st.info("No tienes tareas asignadas para el día de hoy.")

# -----------------------------------------------------------------------------
# VISTAS DE ADMINISTRADOR
# -----------------------------------------------------------------------------
def render_admin_view():
    st.title("⚙️ Panel de Administración")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Monitoreo y Control", "➕ Asignar Tareas", "👥 Personal", "📁 Proyectos"]
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
        limite_tolerancia = dtime(9, 20, 0)
        
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
        tasks_monitoreo = query(
            """
            SELECT T.ID_Tarea AS id, E.Nombre_Completo AS emp, P.Nombre_Proyecto AS project, 
                   T.Descripcion_Tarea AS description, T.Estado_Tarea AS state, T.Observaciones AS notes
            FROM Tareas T
            JOIN Trabajadores W ON W.ID_Trabajador = T.ID_Trabajador
            JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
            JOIN Proyectos P ON P.ID_Proyecto = T.ID_Proyecto
            WHERE T.Fecha = CURDATE() ORDER BY T.ID_Tarea DESC
            """
        )

        if tasks_monitoreo:
            for task in tasks_monitoreo:
                icon = '✅' if task['state'] == 'Completada' else ('⏸️' if task['state'] == 'Bloqueada' else '📌')
                
                with st.expander(f"{icon} {task['project']} | {task['emp']} — [{task['state']}]"):
                    st.write(f"**Descripción:** {task['description']}")
                    st.write(f"**Reporte/Archivos adjuntos:** {task['notes'] or 'Sin reportes enviados'}")

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("⏸️ Pausar", key=f"pause_{task['id']}", use_container_width=True):
                            execute("UPDATE Tareas SET Estado_Tarea='Bloqueada' WHERE ID_Tarea=%s", (task["id"],))
                            st.rerun()
                    with col_btn2:
                        if st.button("▶️ Reanudar", key=f"resume_{task['id']}", use_container_width=True):
                            execute("UPDATE Tareas SET Estado_Tarea='En Progreso' WHERE ID_Tarea=%s", (task["id"],))
                            st.rerun()
                    with col_btn3:
                        if st.button("✅ Aprobar", key=f"approve_{task['id']}", use_container_width=True):
                            execute("UPDATE Tareas SET Estado_Tarea='Completada' WHERE ID_Tarea=%s", (task["id"],))
                            st.rerun()

                    st.divider()
                    st.markdown("💬 **Chat de la Tarea**")
                    comentarios = obtener_comentarios(task["id"])
                    
                    chat_container = st.container(height=200)
                    with chat_container:
                        if comentarios:
                            for c in comentarios:
                                st.caption(f"**{c['Autor']} ({c['Rol']})** - {c['Fecha']}")
                                st.write(f"└ {c['Mensaje']}")
                        else:
                            st.info("Inicia la comunicación para dar feedback al empleado.")

                    col_msg1, col_msg2 = st.columns([3, 1])
                    with col_msg1:
                        nuevo_msg = st.text_input("Instrucciones u observaciones...", key=f"input_admin_{task['id']}", label_visibility="collapsed")
                    with col_msg2:
                        if st.button("Enviar Feedback", key=f"send_admin_{task['id']}", use_container_width=True):
                            agregar_comentario(task["id"], st.session_state.user["name"], "Administrador", nuevo_msg)
                            st.rerun()
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
            state = st.selectbox("Estado", ["Asignada", "En Progreso"])

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
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE())
                            """,
                            (
                                w_dict[selected_w],
                                st.session_state.user["id"],
                                p_dict[selected_p],
                                desc.strip(),
                                state,
                                dt_inicio.strftime("%Y-%m-%d %H:%M:%S"),
                                dt_entrega.strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                        )
                        st.success("Tarea asignada exitosamente.")
                        st.rerun()

    # GESTIÓN DE PERSONAL
    with tab3:
        st.subheader("Registrar Nuevo Trabajador")
        with st.form("form_worker"):
            name = st.text_input("Nombre Completo")
            position = st.text_input("Cargo / Puesto")
            code = st.text_input("Código de Trabajador (Ej: TRAB01)")
            pin = st.text_input("PIN (4 dígitos)", type="password")
            submitted = st.form_submit_button("Registrar Trabajador")

            if submitted:
                if not all([name, position, code, pin]):
                    st.warning("Completa todos los datos.")
                elif len(pin) != 4 or not pin.isdigit():
                    st.warning("El PIN debe ser strictly de 4 dígitos numéricos.")
                else:
                    try:
                        emp_id, _ = execute(
                            "INSERT INTO Empleados (Nombre_Completo, Estado) VALUES (%s, 'Activo')",
                            (name.strip(),),
                        )
                        execute(
                            "INSERT INTO Trabajadores (ID_Empleado, Rol_Cargo, Codigo_Trabajador, PIN_Acceso) VALUES (%s, %s, %s, %s)",
                            (emp_id, position.strip(), code.strip().upper(), pin.strip()),
                        )
                        st.success("Trabajador registrado.")
                        st.rerun()
                    except Exception:
                        st.error("El código de trabajador ya existe en la base de datos.")

        st.divider()
        st.subheader("Listado de Personal")
        people = query(
            """
            SELECT W.ID_Trabajador AS id, E.Nombre_Completo AS Nombre, W.Rol_Cargo AS Cargo,
                   W.Codigo_Trabajador AS Codigo, E.Estado
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
        projs = query("SELECT ID_Proyecto AS ID, Nombre_Proyecto AS Proyecto, Area_Departamento AS Área FROM Proyectos ORDER BY Nombre_Proyecto")
        st.dataframe(projs, use_container_width=True)

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