from config.database import query_db, execute_db

def get_attendance_by_worker_and_date(worker_id, target_date):
    """Obtiene el registro de asistencia de un trabajador para una fecha específica."""
    sql = """
        SELECT ID_Asistencia AS id, Fecha_Entrada AS entry, Fecha_Salida AS salida
        FROM Asistencia
        WHERE ID_Trabajador = %s AND DATE(Fecha_Entrada) = %s
        ORDER BY ID_Asistencia DESC
    """
    return query_db(sql, (worker_id, target_date), one=True)

def register_entry(worker_id, entry_datetime_str):
    """Registra la entrada de un trabajador en la base de datos."""
    sql = "INSERT INTO Asistencia (ID_Trabajador, Fecha_Entrada) VALUES (%s, %s)"
    return execute_db(sql, (worker_id, entry_datetime_str))

def register_exit(worker_id, exit_datetime_str, target_date):
    """Registra la salida del trabajador si tiene una entrada activa hoy."""
    sql = """
        UPDATE Asistencia 
        SET Fecha_Salida = %s
        WHERE ID_Trabajador = %s AND DATE(Fecha_Entrada) = %s AND Fecha_Salida IS NULL
    """
    return execute_db(sql, (exit_datetime_str, worker_id, target_date))