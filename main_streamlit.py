import io
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import mysql.connector
import streamlit as st

# Librerías de Google Drive API (descomentadas)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
except ImportError:
    pass

# 1. Configuración básica de la página
st.set_page_config(
    page_title="Control de Asistencia",
    page_icon="🏢",
    layout="wide"
)

# 2. Inyección de estilos CSS específicos para componentes de Streamlit
st.markdown("""
    <style>
    /* Fondo principal de la aplicación */
    .stAppViewContainer {
        background-color: #F8FAFC !important;
    }
    
    /* Fondo del Sidebar (Barra Lateral) */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
    }

    /* Forzar texto visible en todo el Sidebar */
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #F8FAFC !important;
    }

    /* Corrección de cajas de texto / Inputs / Selects dentro del Sidebar */
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] div[data-baseweb="input"],
    [data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }

    /* Corrección de TODOS los botones dentro del Sidebar */
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] .stButton > button {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }

    /* Estado hover de los botones en el Sidebar */
    [data-testid="stSidebar"] button:hover,
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1D4ED8 !important;
        color: #FFFFFF !important;
        border-color: #1D4ED8 !important;
    }

    /* Corrección del contenedor de Notificaciones (Expander) */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }

    /* Ajuste y bordes suavizados para el logo */
    [data-testid="stSidebar"] [data-testid="stImage"] img {
        border-radius: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)


def now_local():
    """Retorna la fecha y hora actual en zona horaria local (UTC-5)"""
    return datetime.now(ZoneInfo("America/Lima"))


def today_local():
    """Retorna únicamente la fecha de hoy en zona horaria local (UTC-5)"""
    return datetime.now(ZoneInfo("America/Lima")).date()


# -----------------------------------------------------------------------------
# CONEXIÓN A BASE DE DATOS Y GOOGLE DRIVE
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


def upload_to_google_drive(uploaded_file, worker_name, task_id):
    """Sube un archivo cargado a Google Drive y devuelve su enlace público"""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = ["https://www.googleapis.com/auth/drive.file"]
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )

        service = build("drive", "v3", credentials=creds)
        folder_id = st.secrets["google_drive"].get("folder_id", None)

        file_extension = os.path.splitext(uploaded_file.name)[1]
        custom_file_name = f"Reporte_Tarea_{task_id}_{worker_name.replace(' ', '_')}{file_extension}"

        file_metadata = {"name": custom_file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaIoBaseUpload(
            io.BytesIO(uploaded_file.getvalue()),
            mimetype=uploaded_file.type,
            resumable=True,
        )

        drive_file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

        service.permissions().create(
            fileId=drive_file.get("id"),
            body={"role": "reader", "type": "anyone"},
        ).execute()

        return drive_file.get("webViewLink")
    except Exception as e:
        st.error(f"❌ Error al subir el archivo a Google Drive: {e}")
        return None


# -----------------------------------------------------------------------------
# LÓGICA DE COMENTARIOS Y CHAT
# -----------------------------------------------------------------------------
def obtener_comentarios(id_tarea):
    """Obtiene el historial de chat de una tarea específica."""
    return query(
        "SELECT Autor, Rol, Mensaje, Fecha FROM Comentarios_Tarea WHERE ID_Tarea = %s ORDER BY ID_Comentario ASC",
        (id_tarea,),
    )


def agregar_comentario(id_tarea, autor, rol, mensaje):
    """Inserta un nuevo mensaje en el hilo de la tarea."""
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
    saved_id = st.query_params.get("user_id")
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
    elif saved_role in ("Empleado", "Trabajador"):
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

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric(
                "Entrada Registrada",
                str(attendance["entry"])
                if attendance and attendance.get("entry")
                else "Pendiente",
            )
        with col_b:
            st.metric(
                "Salida Registrada",
                str(attendance["salida"])
                if attendance and attendance.get("salida")
                else "Pendiente",
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

                    col_act1, col_act2 = st.columns([1, 1])
                    with col_act1:
                        new_state = st.selectbox(
                            "Actualizar Estado",
                            ["Asignada", "En Progreso", "Completada", "Bloqueada"],
                            key=f"st_{task['id']}",
                        )
                        new_notes = st.text_input(
                            "Observaciones adicionales (Opcional)",
                            value="",
                            key=f"nt_{task['id']}",
                        )
                    with col_act2:
                        uploaded_file = st.file_uploader(
                            "📎 Adjuntar Reporte (Drive)",
                            key=f"file_{task['id']}",
                        )

                    if st.button("Guardar Reporte / Actualizar", key=f"btn_{task['id']}", use_container_width=True):
                        if new_state == "Bloqueada" and not new_notes.strip():
                            st.warning("Debes ingresar una observación si bloqueas la tarea.")
                        else:
                            final_notes = task["notes"] or ""

                            if uploaded_file is not None:
                                with st.spinner("Subiendo reporte a Google Drive..."):
                                    drive_url = upload_to_google_drive(
                                        uploaded_file, user["name"], task["id"]
                                    )
                                    if drive_url:
                                        file_tag = f"\n📁 [Ver Reporte en Drive]({drive_url})"
                                        final_notes += f" {file_tag}"
                                        st.success("☁️ Archivo subido exitosamente a Google Drive.")

                            if new_notes.strip():
                                final_notes += f"\nNote: {new_notes.strip()}"

                            if task["end_time"]:
                                limit_dt = (
                                    task["end_time"]
                                    if isinstance(task["end_time"], datetime)
                                    else datetime.strptime(
                                        str(task["end_time"]), "%Y-%m-%d %H:%M:%S"
                                    )
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

    with tab1:
        st.subheader("Asistencia del Día")
        attendance_data = query(
            """
            SELECT E.Nombre_Completo AS Empleado, W.Codigo_Trabajador AS Codigo,
                   A.Fecha_Entrada AS Entrada, A.Fecha_Salida AS Salida
            FROM Asistencia A
            JOIN Trabajadores W ON W.ID_Trabajador=A.ID_Trabajador
            JOIN Empleados E ON E.ID_Empleado=W.ID_Empleado
            WHERE DATE(A.Fecha_Entrada)=CURDATE() ORDER BY A.Fecha_Entrada
            """
        )
        st.dataframe(attendance_data, use_container_width=True)
        st.divider()

        st.subheader("📋 Control de Tareas")
        tasks_monitoreo = query(
            """
            SELECT T.ID_Tarea AS id, E.Nombre_Completo AS emp, P.Nombre_Proyecto AS project, 
                   T.Descripcion_Tarea AS description, T.Estado_Tarea AS state, T.Observaciones AS notes
            FROM Tareas T
            JOIN Trabajadores W ON W.ID_Trabajador = T.ID_Trabajador
            JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
            JOIN Proyectos P ON P.ID_Proyecto = T.ID_Proyecto
            WHERE DATE(T.Fecha) = CURDATE() ORDER BY T.ID_Tarea DESC
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
                    st.warning("El PIN debe ser estrictamente de 4 dígitos numéricos.")
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
# CONTROL DE FLUJO PRINCIPAL Y NOTIFICACIONES EN SIDEBAR
# -----------------------------------------------------------------------------
if st.session_state.user is None:
    render_login()
else:
    with st.sidebar:
        # Render del Logo
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.markdown("### **EMPRESA**")
        st.divider()

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
                WHERE T.ID_Trabajador = %s AND T.Estado_Tarea = 'Asignada' AND DATE(T.Fecha) = %s
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
                WHERE T.Estado_Tarea = 'Completada' AND DATE(T.Fecha) = %s
                ORDER BY T.ID_Tarea DESC
                """,
                (today_date,),
            )
        else:
            notificaciones = []

        count_notif = len(notificaciones) if notificaciones else 0
        with st.expander(f"🔔 Notificaciones ({count_notif})"):
            if notificaciones:
                for n in notificaciones:
                    if st.session_state.user["role"] == "Empleado":
                        st.write(f"📌 **{n['project']}**: {n['descr']}")
                    else:
                        st.write(f"✅ **{n['emp']}** completó: {n['descr']}")
            else:
                st.info("No hay notificaciones sin leer.")

        st.divider()

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.user = None
            st.query_params.clear()
            st.rerun()

    # Render de la vista correspondiente
    if st.session_state.user["role"] in ("Empleado", "Trabajador"):
        render_employee_view()
    elif st.session_state.user["role"] == "Administrador":
        render_admin_view()
