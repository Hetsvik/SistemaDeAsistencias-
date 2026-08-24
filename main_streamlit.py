import os
import streamlit as st
import mysql.connector
# Configuración de la interfaz
st.set_page_config(
    page_title="Control de Asistencia y Actividades",
    page_icon="⏱️",
    layout="wide"
)

# -----------------------------------------------------------------------------
# CONEXIÓN A BASE DE DATOS EN CLEVER CLOUD
# -----------------------------------------------------------------------------
def db():
    """Conexión a MySQL usando credenciales de st.secrets o variables de entorno de Clever Cloud."""
    def get_val(key_list):
        for k in key_list:
            if k in st.secrets:
                return st.secrets[k]
            if os.getenv(k):
                return os.getenv(k)
        return None

    host = get_val(["MYSQL_HOST", "MYSQL_ADDON_HOST"])
    port = get_val(["MYSQL_PORT", "MYSQL_ADDON_PORT"]) or "3306"
    user = get_val(["MYSQL_USER", "MYSQL_ADDON_USER"])
    password = get_val(["MYSQL_PASSWORD", "MYSQL_ADDON_PASSWORD"])
    database = get_val(["MYSQL_DATABASE", "MYSQL_ADDON_DB"])

    if not all([host, user, password, database]):
        st.error("❌ Faltan las variables de conexión a la base de datos en los Secrets de Streamlit.")
        st.stop()

    return mysql.connector.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        connection_timeout=10,
        autocommit=False
    )

def query(sql, params=(), one=False):
    conn = db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()
    finally:
        cur.close()
        conn.close()

def execute(sql, params=()):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid, cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# -----------------------------------------------------------------------------
# MANEJO DE SESIÓN
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

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
    
    tab1, tab2 = st.tabs(["🕒 Control de Asistencia", "📋 Mis Tareas del Día"])

    # TAB 1: Asistencia
    with tab1:
        st.subheader("Marcación de Asistencia Hoy")
        attendance = query(
            """
            SELECT ID_Asistencia AS id, Fecha_Calculada AS date,
                Fecha_Entrada AS entry, Fecha_Salida AS exit
            FROM Asistencia
            WHERE ID_Trabajador=%s AND Fecha_Calculada=CURDATE()
            """,
            (user["id"],),
            one=True,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Entrada Registrada", str(attendance["entry"]) if attendance and attendance["entry"] else "Pendiente")
        with col_b:
            st.metric("Salida Registrada", str(attendance["exit"]) if attendance and attendance["exit"] else "Pendiente")

        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔴 Registrar Entrada", type="primary", disabled=bool(attendance), use_container_width=True):
                try:
                    execute("INSERT INTO Asistencia (ID_Trabajador, Fecha_Entrada) VALUES (%s, NOW())", (user["id"],))
                    st.success("Entrada registrada con éxito.")
                    st.rerun()
                except Exception:
                    st.error("Ya existe una entrada registrada para hoy.")

        with col2:
            can_exit = attendance is not None and attendance["exit"] is None
            if st.button("🔵 Registrar Salida", disabled=not can_exit, use_container_width=True):
                _, count = execute(
                    """
                    UPDATE Asistencia SET Fecha_Salida=NOW()
                    WHERE ID_Trabajador=%s AND Fecha_Calculada=CURDATE() AND Fecha_Salida IS NULL
                    """,
                    (user["id"],),
                )
                if count:
                    st.success("Salida registrada con éxito.")
                    st.rerun()
                else:
                    st.error("No hay entrada activa para hoy.")

    # TAB 2: Tareas del Empleado
    with tab2:
        st.subheader("Crear / Registrar Nueva Tarea")
        projects = query("SELECT ID_Proyecto AS id, Nombre_Proyecto AS name FROM Proyectos ORDER BY Nombre_Proyecto")
        
        if projects:
            proj_dict = {p["name"]: p["id"] for p in projects}
            selected_proj = st.selectbox("Proyecto", list(proj_dict.keys()))
            task_desc = st.text_area("Descripción de la Tarea")
            task_state = st.selectbox("Estado Inicial", ["Asignada", "En Progreso"])

            if st.button("Guardar Tarea"):
                if not task_desc.strip():
                    st.warning("La descripción es obligatoria.")
                else:
                    admin = query(
                        """
                        SELECT A.ID_Administrador AS id FROM Administrador A
                        JOIN Empleados E ON E.ID_Empleado=A.ID_Empleado
                        WHERE E.Estado='Activo' ORDER BY A.ID_Administrador LIMIT 1
                        """,
                        one=True,
                    )
                    if not admin:
                        st.error("No hay un administrador activo en el sistema.")
                    else:
                        execute(
                            """
                            INSERT INTO Tareas (ID_Trabajador, ID_Administrador_Asignador, ID_Proyecto, Descripcion_Tarea, Estado_Tarea, Fecha)
                            VALUES (%s, %s, %s, %s, %s, CURDATE())
                            """,
                            (user["id"], admin["id"], proj_dict[selected_proj], task_desc.strip(), task_state)
                        )
                        st.success("Tarea agregada.")
                        st.rerun()
        else:
            st.info("No hay proyectos disponibles.")

        st.divider()
        st.subheader("Tareas de Hoy")
        tasks = query(
            """
            SELECT T.ID_Tarea AS id, P.Nombre_Proyecto AS project, T.Descripcion_Tarea AS description,
                T.Estado_Tarea AS state, T.Observaciones AS notes
            FROM Tareas T
            JOIN Proyectos P ON P.ID_Proyecto=T.ID_Proyecto
            WHERE T.ID_Trabajador=%s AND T.Fecha=CURDATE()
            ORDER BY T.ID_Tarea DESC
            """,
            (user["id"],),
        )

        for task in tasks:
            with st.expander(f"📌 {task['project']} - [{task['state']}]"):
                st.write(f"**Descripción:** {task['description']}")
                st.write(f"**Observaciones:** {task['notes'] or 'Sin observaciones'}")
                
                new_state = st.selectbox("Actualizar Estado", ["Asignada", "En Progreso", "Completada", "Bloqueada"], key=f"st_{task['id']}")
                new_notes = st.text_input("Observaciones", value=task['notes'] or "", key=f"nt_{task['id']}")

                if st.button("Actualizar Tarea", key=f"btn_{task['id']}"):
                    if new_state == "Bloqueada" and not new_notes.strip():
                        st.warning("Debes ingresar una observación si bloqueas la tarea.")
                    else:
                        execute(
                            "UPDATE Tareas SET Estado_Tarea=%s, Observaciones=%s WHERE ID_Tarea=%s AND ID_Trabajador=%s",
                            (new_state, new_notes.strip() or None, task['id'], user['id'])
                        )
                        st.success("Estado actualizado.")
                        st.rerun()

# -----------------------------------------------------------------------------
# VISTAS DE ADMINISTRADOR
# -----------------------------------------------------------------------------
def render_admin_view():
    st.title("⚙️ Panel de Administración")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Monitoreo Hoy", "➕ Asignar Tareas", "👥 Personal", "📁 Proyectos"])

    # TAB 1: Monitoreo
    with tab1:
        st.subheader("Asistencia del Día")
        attendance_data = query(
            """
            SELECT W.Nombre_Completo AS Empleado, W.Codigo_Trabajador AS Codigo,
                A.Fecha_Entrada AS Entrada, A.Fecha_Salida AS Salida
            FROM Asistencia A
            JOIN Trabajadores W ON W.ID_Trabajador=A.ID_Trabajador
            WHERE A.Fecha_Calculada=CURDATE() ORDER BY A.Fecha_Entrada
            """
        )
        st.dataframe(attendance_data, use_container_width=True)

        st.subheader("Tareas del Día")
        task_data = query(
            """
            SELECT W.Nombre_Completo AS Empleado, P.Nombre_Proyecto AS Proyecto,
                T.Descripcion_Tarea AS Tarea, T.Estado_Tarea AS Estado, T.Observaciones AS Notas
            FROM Tareas T
            JOIN Trabajadores W ON W.ID_Trabajador=T.ID_Trabajador
            JOIN Proyectos P ON P.ID_Proyecto=T.ID_Proyecto
            WHERE T.Fecha=CURDATE() ORDER BY T.ID_Tarea DESC
            """
        )
        st.dataframe(task_data, use_container_width=True)

    # TAB 2: Asignar Tareas
    with tab2:
        st.subheader("Nueva Tarea para un Empleado")
        workers = query("SELECT ID_Trabajador AS id, Nombre_Completo AS name FROM Trabajadores ORDER BY Nombre_Completo")
        projects = query("SELECT ID_Proyecto AS id, Nombre_Proyecto AS name FROM Proyectos ORDER BY Nombre_Proyecto")

        if workers and projects:
            w_dict = {w["name"]: w["id"] for w in workers}
            p_dict = {p["name"]: p["id"] for p in projects}

            selected_w = st.selectbox("Trabajador", list(w_dict.keys()))
            selected_p = st.selectbox("Proyecto", list(p_dict.keys()))
            desc = st.text_area("Descripción")
            state = st.selectbox("Estado", ["Asignada", "En Progreso"])

            if st.button("Asignar Tarea"):
                if not desc.strip():
                    st.warning("Escribe una descripción.")
                else:
                    execute(
                        """
                        INSERT INTO Tareas (ID_Trabajador, ID_Administrador_Asignador, ID_Proyecto, Descripcion_Tarea, Estado_Tarea, Fecha)
                        VALUES (%s, %s, %s, %s, %s, CURDATE())
                        """,
                        (w_dict[selected_w], st.session_state.user["id"], p_dict[selected_p], desc.strip(), state)
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
                    st.warning("El PIN debe ser estrictamente de 4 dígitos numéricos.")
                else:
                    try:
                        emp_id, _ = execute("INSERT INTO Empleados (Nombre_Completo, Estado) VALUES (%s, 'Activo')", (name.strip(),))
                        execute(
                            "INSERT INTO Trabajadores (ID_Empleado, Rol_Cargo, Codigo_Trabajador, PIN_Acceso) VALUES (%s, %s, %s, %s)",
                            (emp_id, position.strip(), code.strip().upper(), pin.strip())
                        )
                        st.success("Trabajador registrado.")
                        st.rerun()
                    except Exception:
                        st.error("El código de trabajador ya existe en la base de datos.")

        st.divider()
        st.subheader("Listado de Personal")
        people = query(
            """
            SELECT ID_Trabajador AS id, Nombre_Completo AS Nombre, Rol_Cargo AS Cargo,
            Codigo_Trabajador AS Codigo, Estado
            FROM Trabajadores T
            JOIN Empleados E ON E.ID_Empleado=T.ID_Empleado ORDER BY Nombre_Completo
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
                    execute("INSERT INTO Proyectos (Nombre_Proyecto, Area_Departamento) VALUES (%s, %s)", (p_name.strip(), p_area.strip()))
                    st.success("Proyecto creado.")
                    st.rerun()

        st.divider()
        st.subheader("Lista de Proyectos")
        projs = query("SELECT ID_Proyecto AS ID, Nombre_Proyecto AS Proyecto, Area_Departamento AS Área FROM Proyectos ORDER BY Nombre_Proyecto")
        st.dataframe(projs, use_container_width=True)

# -----------------------------------------------------------------------------
# CONTROL DE FLUJO PRINCIPAL
# -----------------------------------------------------------------------------
if st.session_state.user is None:
    render_login()
else:
    # Barra lateral
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['name']}**")
        st.write(f"💼 Rol: `{st.session_state.user['role']}`")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # Vistas según rol
    if st.session_state.user["role"] == "Empleado":
        render_employee_view()
    elif st.session_state.user["role"] == "Administrador":
        render_admin_view()