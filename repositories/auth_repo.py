from config.database import query_db

def get_user_by_id_and_role(user_id, role):
    """Recupera los datos del usuario para mantener la sesión activa."""
    if role == "Administrador":
        sql = """
            SELECT A.ID_Administrador AS id, E.Nombre_Completo AS name, 'Administrador' AS role
            FROM Administrador A
            JOIN Empleados E ON E.ID_Empleado = A.ID_Empleado
            WHERE A.ID_Administrador = %s
        """
    elif role == "Empleado":
        sql = """
            SELECT W.ID_Trabajador AS id, E.Nombre_Completo AS name, 'Empleado' AS role
            FROM Trabajadores W
            JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
            WHERE W.ID_Trabajador = %s
        """
    else:
        return None
    return query_db(sql, (user_id,), one=True)

def authenticate_user(code, pin, role):
    """Valida las credenciales de acceso contra la base de datos."""
    if role in ("Empleado", "Trabajador"):
        sql = """
            SELECT T.ID_Trabajador AS id, E.Nombre_Completo AS name,
                   T.Rol_Cargo AS position, T.Codigo_Trabajador AS code,
                   'Empleado' AS role
            FROM Trabajadores T
            JOIN Empleados E ON E.ID_Empleado=T.ID_Empleado
            WHERE UPPER(T.Codigo_Trabajador)=%s
                AND T.PIN_Acceso=%s
                AND E.Estado='Activo'
        """
    elif role == "Administrador":
        sql = """
            SELECT A.ID_Administrador AS id, E.Nombre_Completo AS name, 'Administrador' AS position,
                A.Codigo_Administrador AS code,
                'Administrador' AS role
            FROM Administrador A
            JOIN Empleados E ON E.ID_Empleado=A.ID_Empleado
            WHERE UPPER(A.Codigo_Administrador)=%s
                AND A.PIN_Acceso=%s
                AND E.Estado='Activo'
        """
    else:
        return None
    return query_db(sql, (code, pin), one=True)