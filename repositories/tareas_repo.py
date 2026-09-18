from config.database import query_db, execute_db
def get_tasks_by_worker_and_date(worker_id, target_date):
    """Obtiene las tareas asignadas a un trabajador específico para una fecha determinada."""
    sql = """
        SELECT T.ID_Tarea AS id, P.Nombre_Proyecto AS project, T.Descripcion_Tarea AS description,
               T.Estado_Tarea AS state, T.Observaciones AS notes,
               T.Fecha_Inicio AS start_time, T.Fecha_Entrega AS end_time
        FROM Tareas T
        JOIN Proyectos P ON P.ID_Proyecto=T.ID_Proyecto
        WHERE T.ID_Trabajador=%s AND DATE(T.Fecha)=%s
        ORDER BY T.ID_Tarea DESC
    """
    return query_db(sql, (worker_id, target_date))

def update_task_status_by_worker(task_id, worker_id, new_state, notes):
    """Permite al trabajador actualizar el estado y observaciones de su propia tarea."""
    sql = """
        UPDATE Tareas 
        SET Estado_Tarea=%s, Observaciones=%s 
        WHERE ID_Tarea=%s AND ID_Trabajador=%s
    """
    return execute_db(sql, (new_state, notes, task_id, worker_id))

def get_all_tasks_for_today():
    """Obtiene todas las tareas de todos los trabajadores para el monitoreo del administrador hoy."""
    sql = """
        SELECT T.ID_Tarea AS id, E.Nombre_Completo AS emp, P.Nombre_Proyecto AS project, 
               T.Descripcion_Tarea AS description, T.Estado_Tarea AS state, T.Observaciones AS notes
        FROM Tareas T
        JOIN Trabajadores W ON W.ID_Trabajador = T.ID_Trabajador
        JOIN Empleados E ON E.ID_Empleado = W.ID_Empleado
        JOIN Proyectos P ON P.ID_Proyecto = T.ID_Proyecto
        WHERE T.Fecha = CURDATE() ORDER BY T.ID_Tarea DESC
    """
    return query_db(sql)

def update_task_state_admin(task_id, new_state):
    """Permite al administrador forzar cambios de estado (Aprobar, Rechazar, Pausar)."""
    sql = "UPDATE Tareas SET Estado_Tarea=%s WHERE ID_Tarea=%s"
    return execute_db(sql, (new_state, task_id))

def delete_task(task_id):
    """Elimina una tarea del registro."""
    sql = "DELETE FROM Tareas WHERE ID_Tarea=%s"
    return execute_db(sql, (task_id,))