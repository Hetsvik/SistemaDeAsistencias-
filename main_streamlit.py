from datetime import datetime
import mysql.connector
import os
import streamlit as st
from zoneinfo import ZoneInfo

# Configuración de la interfaz
st.set_page_config(
    page_title="Control de Asistencia y Actividades",
    page_icon="⏱️",
    layout="wide",
)


def now_local():
    """Retorna la fecha y hora actual en zona horaria local (UTC-5) formateada para MySQL"""
    return datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")


def today_local():
    """Retorna únicamente la fecha de hoy en zona horaria local (UTC-5)"""
    return datetime.now(ZoneInfo("America/Lima")).date()


# -----------------------------------------------------------------------------
# CONEXIÓN A BASE DE DATOS EN CLEVER CLOUD
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

    current_time = now_local()
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

    # -------------------------------------------------------------------------
    # SECCIÓN 1: CONTROL DE ASISTENCIA
    # -------------------------------------------------------------------------
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
                (
                    str(attendance["entry"])
                    if attendance and attendance.get("entry")
                    else "Pendiente"
                ),
            )
        with col_b:
            st.metric(
                "Salida Registrada",
                (
                    str(attendance["salida"])
                    if attendance and attendance.get("salida")
                    else "Pendiente"
                ),
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
                    (user["id"], now_local()),
                )
                st.success("Entrada registrada con éxito.")
                st.rerun()

        with col2:
            can_exit = (
                attendance is not None and attendance.get("salida") is None
            )
            if st.button(
                "🔵 Registrar Salida",
                disabled=not can_exit,
                use_container_width=True,
            ):
                _, count = execute(
                    """
                    UPDATE Asistencia 
                    SET Fecha_Salida = %s
                    WHERE ID_Trabajador = %s AND DATE(Fecha_Entrada) = %s AND Fecha_Salida IS NULL
                    """,
                    (now_local(), user["id"], today_date),
                )
                if count:
                    st.success("Salida registrada con éxito.")
                    st.rerun()
                else:
                    st.error("No hay entrada activa para hoy.")

    # -------------------------------------------------------------------------
    # SECCIÓN 2: TAREAS DEL DÍA (CON FECHA INICIO Y ENTREGA)
    # -------------------------------------------------------------------------
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
                    # Muestra de fechas programadas
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.info(
                            f"📅 **Inicio Programado:**\n\n{task['start_time'] or 'Sin definir'}"
                        )
                    with col_t2:
                        st.warning(
                            f"⏰ **Fecha/Hora de Entrega:**\n\n{task['end_time'] or 'Sin definir'}"
                        )

                    st.write(f"**Descripción:** {task['description']}")
                    st.write(
                        f"**Observaciones:** {task['notes'] or 'Sin observaciones'}"
                    )

                    new_state = st.selectbox(
                        "Actualizar Estado",
                        ["Asignada", "En Progreso", "Completada", "Bloqueada"],
                        key=f"st_{task['id']}",
                    )
                    new_notes = st.text_input(
                        "Observaciones",
                        value=task["notes"] or "",
                        key=f"nt_{task['id']}",
                    )

                    if st.button("Actualizar Tarea", key=f"btn_{task['id']}"):
                        if new_state == "Bloqueada" and not new_notes.strip():
                            st.warning(
                                "Debes ingresar una observación si bloqueas la tarea."
                            )
                        else:
                            execute(
                                "UPDATE Tareas SET Estado_Tarea=%s, Observaciones=%s WHERE ID_Tarea=%s AND ID_Trabajador=%s",
                                (
                                    new_state,
                                    new_notes.strip() or None,
                                    task["id"],
                                    user["id"],
                                ),
                            )
                            st.success("Estado actualizado.")
                            st.rerun()
        else:
            st.info("No tienes tareas asignadas para el día de hoy.")


# -----------------------------------------------------------------------------
# VISTAS DE ADMINISTRADOR
# -----------------------------------------------------------------------------
def render_admin_view():
    st.title("⚙️ Panel de Administración")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Monitoreo Hoy", "➕ Asignar Tareas", "👥 Personal", "📁 Proyectos"]
    )

    # TAB 1: Monitoreo
    with tab1:
        st.subheader("Asistencia del Día")
        attendance_data = query(
            """
            SELECT E.Nombre_Completo AS Empleado, W.Codigo_Trabajador AS Codigo,
                   A.Fecha_Entrada AS Entrada, A.Fecha_Salida AS Salida
            FROM Asistencia A
            JOIN Trabajadores W ON W.ID_Trabajador=A.ID_Trabajador
            JOIN Empleados E ON E.ID_Empleado=W.ID_Empleado
            WHERE A.Fecha_Calculada=CURDATE() ORDER BY A.Fecha_Entrada
            """
        )
        st.dataframe(attendance_data, use_container_width=True)

        st.subheader("Tareas del Día")
        task_data = query(
            """
            SELECT E.Nombre_Completo AS Empleado, P.Nombre_Proyecto AS Proyecto,
                   T.Descripcion_Tarea AS Tarea, T.Fecha_Inicio AS 'Fecha/Hora Inicio', 
                   T.Fecha_Entrega AS 'Fecha/Hora Entrega', T.Estado_Tarea AS Estado, T.Observaciones AS Notas
            FROM Tareas T
            JOIN Trabajadores W ON W.ID_Trabajador=T.ID_Trabajador
            JOIN Empleados E ON E.ID_Empleado=W.ID_Empleado
            JOIN Proyectos P ON P.ID_Proyecto=T.ID_Proyecto
            WHERE T.Fecha=CURDATE() ORDER BY T.ID_Tarea DESC
            """
        )
        st.dataframe(task_data, use_container_width=True)

    # TAB 2: Asignar Tareas (NUEVOS CAMPOS INICIO Y ENTREGA)
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
        projects = query(
            "SELECT ID_Proyecto AS id, Nombre_Proyecto AS name FROM Proyectos ORDER BY Nombre_Proyecto"
        )

        if workers and projects:
            w_dict = {w["name"]: w["id"] for w in workers}
            p_dict = {p["name"]: p["id"] for p in projects}

            selected_w = st.selectbox("Trabajador", list(w_dict.keys()))
            selected_p = st.selectbox("Proyecto", list(p_dict.keys()))

            # Captura de Fecha y Hora de Inicio
            col_in1, col_in2 = st.columns(2)
            with col_in1:
                f_inicio_date = st.date_input(
                    "Fecha de Inicio", value=today_local()
                )
            with col_in2:
                f_inicio_time = st.time_input("Hora de Inicio")

            # Captura de Fecha y Hora de Entrega
            col_en1, col_en2 = st.columns(2)
            with col_en1:
                f_entrega_date = st.date_input(
                    "Fecha de Entrega", value=today_local()
                )
            with col_en2:
                f_entrega_time = st.time_input("Hora de Entrega")

            desc = st.text_area("Descripción")
            state = st.selectbox("Estado", ["Asignada", "En Progreso"])

            if st.button("Asignar Tarea"):
                if not desc.strip():
                    st.warning("Escribe una descripción.")
                else:
                    dt_inicio = datetime.combine(f_inicio_date, f_inicio_time)
                    dt_entrega = datetime.combine(
                        f_entrega_date, f_entrega_time
                    )

                    if dt_entrega < dt_inicio:
                        st.error(
                            "❌ La fecha de entrega no puede ser anterior a la fecha de inicio."
                        )
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

    # TAB 3: Gestión de Personal
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
                    st.warning(
                        "El PIN debe ser strictly de 4 dígitos numéricos."
                    )
                else:
                    try:
                        emp_id, _ = execute(
                            "INSERT INTO Empleados (Nombre_Completo, Estado) VALUES (%s, 'Activo')",
                            (name.strip(),),
                        )
                        execute(
                            "INSERT INTO Trabajadores (ID_Empleado, Rol_Cargo, Codigo_Trabajador, PIN_Acceso) VALUES (%s, %s, %s, %s)",
                            (
                                emp_id,
                                position.strip(),
                                code.strip().upper(),
                                pin.strip(),
                            ),
                        )
                        st.success("Trabajador registrado.")
                        st.rerun()
                    except Exception:
                        st.error(
                            "El código de trabajador ya existe en la base de datos."
                        )

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

    # TAB 4: Gestión de Proyectos
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
        projs = query(
            "SELECT ID_Proyecto AS ID, Nombre_Proyecto AS Proyecto, Area_Departamento AS Área FROM Proyectos ORDER BY Nombre_Proyecto"
        )
        st.dataframe(projs, use_container_width=True)


# -----------------------------------------------------------------------------
# CONTROL DE FLUJO PRINCIPAL
# -----------------------------------------------------------------------------
if st.session_state.user is None:
    render_login()
else:
    with st.sidebar:
        st.write(f"👤 *{st.session_state.user['name']}*")
        st.write(f"💼 Rol: {st.session_state.user['role']}")

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
                SELECT E.Nombre_Completo AS emp, P.Nombre_Proyecto AS project, T.Descripcion_Tarea AS descr
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
        titulo_campana = (
            f"🔔 Notificaciones ({cantidad})"
            if cantidad > 0
            else "🔔 Notificaciones"
        )

        with st.expander(titulo_campana):
            if cantidad > 0:
                for i, notif in enumerate(notificaciones):
                    if st.session_state.user["role"] == "Empleado":
                        if st.button(
                            f"📌 {notif['project']}\n\n{notif['descr']}",
                            key=f"notif_emp_{i}_{notif['project']}",
                        ):
                            st.session_state.emp_nav = (
                                "📋 Mis Tareas del Día"
                            )
                            st.rerun()
                    else:
                        st.success(
                            f"*✅ {notif['emp']} completó:*\n\n{notif['project']} - {notif['descr']}"
                        )
            else:
                st.write("No hay notificaciones nuevas para hoy.")

        st.divider()

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

    if st.session_state.user["role"] == "Empleado":
        render_employee_view()
    elif st.session_state.user["role"] == "Administrador":
        render_admin_view()
