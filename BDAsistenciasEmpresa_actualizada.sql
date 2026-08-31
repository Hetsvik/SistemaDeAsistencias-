-- =============================================================================
-- ControlAsistenciaOficina - MySQL 8.0.16+
-- Empleados es la entidad principal. Trabajadores y Administrador dependen de
-- Empleados y conservan sus datos específicos.
-- =============================================================================

USE `b5akslrpbumcosysznqj`;

CREATE TABLE Roles_Sistema (
    ID_Rol INT AUTO_INCREMENT PRIMARY KEY,
    Nombre_Rol VARCHAR(50) NOT NULL,
    Descripcion VARCHAR(255) NULL,
    CONSTRAINT UQ_Roles_Sistema_Nombre UNIQUE (Nombre_Rol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `Roles_Sistema` (`ID_Rol`, `Nombre_Rol`, `Descripcion`) VALUES
    (1, 'Trabajador', 'Acceso para marcar asistencia y gestionar sus tareas.'),
    (2, 'Administrador', 'Acceso al panel, reportes y gestión de personal.');

-- 2. Empleados: datos comunes de cualquier persona registrada en la empresa.
CREATE TABLE `Empleados` (
    `ID_Empleado` INT AUTO_INCREMENT PRIMARY KEY,
    `Nombre_Completo` VARCHAR(150) NOT NULL,
    `Estado` ENUM('Activo', 'Inactivo') NOT NULL DEFAULT 'Activo'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Administradores: especialización de Empleados.
CREATE TABLE `Administrador` (
    `ID_Administrador` INT AUTO_INCREMENT PRIMARY KEY,
    `ID_Empleado` INT NOT NULL,
    `Codigo_Administrador` VARCHAR(20) NOT NULL,
    `PIN_Acceso` CHAR(4) NOT NULL,
    `ID_Rol` INT NOT NULL DEFAULT 2,
    CONSTRAINT `UQ_Administrador_Empleado` UNIQUE (`ID_Empleado`),
    CONSTRAINT `UQ_Administrador_Codigo` UNIQUE (`Codigo_Administrador`),
    CONSTRAINT `CHK_Administrador_Rol` CHECK (`ID_Rol` = 2),
    CONSTRAINT `CHK_Administrador_PIN` CHECK (`PIN_Acceso` REGEXP '^[0-9]{4}$'),
    CONSTRAINT `FK_Administrador_Empleados` FOREIGN KEY (`ID_Empleado`)
        REFERENCES `Empleados` (`ID_Empleado`),
    CONSTRAINT `FK_Administrador_Roles` FOREIGN KEY (`ID_Rol`)
        REFERENCES `Roles_Sistema` (`ID_Rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Trabajadores: especialización de Empleados.
CREATE TABLE `Trabajadores` (
    `ID_Trabajador` INT AUTO_INCREMENT PRIMARY KEY,
    `ID_Empleado` INT NOT NULL,
    `Rol_Cargo` VARCHAR(100) NOT NULL,
    `HoraIngreso` TIME NULL,
    `Codigo_Trabajador` VARCHAR(20) NOT NULL,
    `PIN_Acceso` CHAR(4) NOT NULL,
    `ID_Rol` INT NOT NULL DEFAULT 1,
    CONSTRAINT `UQ_Trabajadores_Empleado` UNIQUE (`ID_Empleado`),
    CONSTRAINT `UQ_Trabajadores_Codigo` UNIQUE (`Codigo_Trabajador`),
    CONSTRAINT `CHK_Trabajadores_Rol` CHECK (`ID_Rol` = 1),
    CONSTRAINT `CHK_Trabajadores_PIN` CHECK (`PIN_Acceso` REGEXP '^[0-9]{4}$'),
    CONSTRAINT `FK_Trabajadores_Empleados` FOREIGN KEY (`ID_Empleado`)
        REFERENCES `Empleados` (`ID_Empleado`),
    CONSTRAINT `FK_Trabajadores_Roles` FOREIGN KEY (`ID_Rol`)
        REFERENCES `Roles_Sistema` (`ID_Rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Proyectos
CREATE TABLE `Proyectos` (
    `ID_Proyecto` INT AUTO_INCREMENT PRIMARY KEY,
    `Nombre_Proyecto` VARCHAR(150) NOT NULL,
    `Area_Departamento` VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Asistencia. Un trabajador solo puede registrar una entrada por día.
CREATE TABLE `Asistencia` (
    `ID_Asistencia` INT AUTO_INCREMENT PRIMARY KEY,
    `ID_Trabajador` INT NOT NULL,
    `Fecha_Entrada` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `Fecha_Salida` DATETIME NULL,
    `Fecha_Calculada` DATE GENERATED ALWAYS AS (DATE(`Fecha_Entrada`)) STORED,
    CONSTRAINT `CHK_Asistencia_Fechas` CHECK (
        `Fecha_Salida` IS NULL OR `Fecha_Salida` >= `Fecha_Entrada`
    ),
    CONSTRAINT `FK_Asistencia_Trabajadores` FOREIGN KEY (`ID_Trabajador`)
        REFERENCES `Trabajadores` (`ID_Trabajador`),
    CONSTRAINT `UQ_Trabajador_Fecha` UNIQUE (`ID_Trabajador`, `Fecha_Calculada`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Tareas (Se integraron Fecha_Inicio y Fecha_Entrega)
CREATE TABLE `Tareas` (
    `ID_Tarea` INT AUTO_INCREMENT PRIMARY KEY,
    `ID_Trabajador` INT NOT NULL,
    `ID_Administrador_Asignador` INT NOT NULL,
    `ID_Proyecto` INT NOT NULL,
    `Fecha` DATE NOT NULL DEFAULT (CURRENT_DATE),
    `Fecha_Inicio` DATETIME NULL,
    `Fecha_Entrega` DATETIME NULL,
    `Descripcion_Tarea` TEXT NOT NULL,
    `Estado_Tarea` ENUM('Asignada', 'En Progreso', 'Completada', 'Bloqueada')
        NOT NULL DEFAULT 'Asignada',
    `Observaciones` TEXT NULL,
    CONSTRAINT `CHK_Tareas_Fechas_Entrega` CHECK (
        `Fecha_Entrega` IS NULL OR `Fecha_Inicio` IS NULL OR `Fecha_Entrega` >= `Fecha_Inicio`
    ),
    CONSTRAINT `FK_Tareas_Trabajadores` FOREIGN KEY (`ID_Trabajador`)
        REFERENCES `Trabajadores` (`ID_Trabajador`),
    CONSTRAINT `FK_Tareas_Administrador` FOREIGN KEY (`ID_Administrador_Asignador`)
        REFERENCES `Administrador` (`ID_Administrador`),
    CONSTRAINT `FK_Tareas_Proyectos` FOREIGN KEY (`ID_Proyecto`)
        REFERENCES `Proyectos` (`ID_Proyecto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX `IX_Tareas_Busqueda`
    ON `Tareas` (`ID_Trabajador`, `Fecha`);

-- 8. Actividades
CREATE TABLE `Actividades` (
    `ID_Actividad` INT AUTO_INCREMENT PRIMARY KEY,
    `ID_Tarea` INT NOT NULL,
    `Fecha_Actividad` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `Descripcion_Actividad` TEXT NOT NULL,
    `Estado_Actividad` ENUM('Pendiente', 'En Progreso', 'Completada')
        NOT NULL DEFAULT 'Pendiente',
    `Observaciones` TEXT NULL,
    CONSTRAINT `FK_Actividades_Tareas` FOREIGN KEY (`ID_Tarea`)
        REFERENCES `Tareas` (`ID_Tarea`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Comentarios_Tarea (
    ID_Comentario INT AUTO_INCREMENT PRIMARY KEY,
    ID_Tarea INT NOT NULL,
    Autor VARCHAR(150) NOT NULL,
    Rol ENUM('Administrador', 'Empleado') NOT NULL,
    Mensaje TEXT NOT NULL,
    Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Tarea) REFERENCES Tareas(ID_Tarea) ON DELETE CASCADE
);

CREATE INDEX `IX_Comentarios_Tarea_Busqueda`
    ON `Comentarios_Tarea` (`ID_Tarea`, `Fecha`);

-- =============================================================================
-- DATOS INICIALES
-- =============================================================================

INSERT INTO `Empleados` (`ID_Empleado`, `Nombre_Completo`, `Estado`) VALUES
    (1, 'Administrador General', 'Activo'),
    (2, 'Adonis Vasquez', 'Activo'),
    (3, 'Benjamin Alfonso', 'Activo'),
    (4, 'Celeste Lechuga', 'Activo'),
    (5, 'Xiomara Ramirez', 'Activo'),
    (6, 'Marco Coila', 'Activo'),
    (7, 'Kevin Vega', 'Activo'),
    (8, 'Fiorella Alarcon', 'Activo'),
    (9, 'Alejandro Guzman', 'Activo');

INSERT INTO `Administrador` (
    `ID_Administrador`, `ID_Empleado`, `Codigo_Administrador`, `PIN_Acceso`
) VALUES
    (1, 1, 'AD001', '0671');

INSERT INTO `Trabajadores` (
    `ID_Trabajador`, `ID_Empleado`, `Rol_Cargo`, `Codigo_Trabajador`, `PIN_Acceso`
) VALUES
    (1, 2, 'Arquitecto', 'EM0038', '1020'),
    (2, 3, 'Ingeniero de Sistemas', 'EM0014', '8844'),
    (3, 4, 'Arquitecta', 'EM0030', '7777'),
    (4, 5, 'Arquitecta', 'EM0033', '7920'),
    (5, 6, 'Arquitecto', 'EM0009', '1600'),
    (6, 7, 'Abogado', 'EM0003', '0749'),
    (7, 8, 'Abogada', 'EM0011', '9032'),
    (8, 9, 'Arquitecto', 'EM0029', '0671');

INSERT INTO `Proyectos` (`ID_Proyecto`, `Nombre_Proyecto`, `Area_Departamento`) VALUES
    (1, 'Torre Alta Vista', 'Arquitectura y Diseño'),
    (2, 'Desarrollo Sistema Horarios', 'Tecnología y Sistemas');

INSERT INTO `Asistencia` (
    `ID_Asistencia`, `ID_Trabajador`, `Fecha_Entrada`, `Fecha_Salida`
) VALUES
    (1, 1, '2026-08-17 09:00:00', NULL),
    (2, 2, '2026-08-17 09:30:00', NULL);

INSERT INTO `Tareas` (
    `ID_Tarea`, `ID_Trabajador`, `ID_Administrador_Asignador`, `ID_Proyecto`, `Fecha`,
    `Fecha_Inicio`, `Fecha_Entrega`, `Descripcion_Tarea`, `Estado_Tarea`, `Observaciones`
) VALUES
    (1, 1, 1, 1, '2026-08-17', '2026-08-17 09:00:00', '2026-08-17 17:00:00',
     'Modelado 3D de la fachada principal', 'En Progreso', NULL),
    (2, 2, 1, 2, '2026-08-17', '2026-08-17 09:30:00', '2026-08-17 18:00:00',
     'Creación y modelado de la base de datos para el sistema de horarios y asistencias corporativo',
     'En Progreso', NULL);

DELIMITER $$

CREATE PROCEDURE `sp_registrar_empleado`(
    IN p_nombre_completo VARCHAR(150),
    IN p_estado VARCHAR(10)
)
BEGIN
    IF p_nombre_completo IS NULL OR TRIM(p_nombre_completo) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El nombre del empleado es obligatorio.';
    END IF;

    INSERT INTO `Empleados` (`Nombre_Completo`, `Estado`)
    VALUES (
        TRIM(p_nombre_completo),
        COALESCE(NULLIF(p_estado, ''), 'Activo')
    );
END $$

CREATE PROCEDURE `sp_registrar_administrador`(
    IN p_nombre_completo VARCHAR(150),
    IN p_codigo_administrador VARCHAR(20),
    IN p_pin_acceso CHAR(4)
)
BEGIN
    DECLARE v_id_empleado INT;

    IF p_nombre_completo IS NULL OR TRIM(p_nombre_completo) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El nombre del administrador es obligatorio.';
    END IF;

    INSERT INTO `Empleados` (`Nombre_Completo`, `Estado`)
    VALUES (TRIM(p_nombre_completo), 'Activo');

    SET v_id_empleado = LAST_INSERT_ID();

    INSERT INTO `Administrador`
        (`ID_Empleado`, `Codigo_Administrador`, `PIN_Acceso`)
    VALUES
        (v_id_empleado, TRIM(p_codigo_administrador), p_pin_acceso);
END $$

CREATE PROCEDURE `sp_registrar_trabajador`(
    IN p_nombre_completo VARCHAR(150),
    IN p_rol_cargo VARCHAR(100),
    IN p_hora_ingreso TIME,
    IN p_codigo_trabajador VARCHAR(20),
    IN p_pin_acceso CHAR(4)
)
BEGIN
    DECLARE v_id_empleado INT;

    IF p_nombre_completo IS NULL OR TRIM(p_nombre_completo) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El nombre del trabajador es obligatorio.';
    END IF;

    IF p_rol_cargo IS NULL OR TRIM(p_rol_cargo) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El cargo del trabajador es obligatorio.';
    END IF;

    INSERT INTO `Empleados` (`Nombre_Completo`, `Estado`)
    VALUES (TRIM(p_nombre_completo), 'Activo');

    SET v_id_empleado = LAST_INSERT_ID();

    INSERT INTO `Trabajadores` (
        `ID_Empleado`, `Rol_Cargo`, `HoraIngreso`,
        `Codigo_Trabajador`, `PIN_Acceso`
    ) VALUES (
        v_id_empleado, TRIM(p_rol_cargo), p_hora_ingreso,
        TRIM(p_codigo_trabajador), p_pin_acceso
    );
END $$

CREATE PROCEDURE `sp_registrar_asistencia`(
    IN p_id_trabajador INT,
    IN p_fecha_entrada DATETIME
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM `Trabajadores` t
        INNER JOIN `Empleados` e ON e.ID_Empleado = t.ID_Empleado
        WHERE t.ID_Trabajador = p_id_trabajador
          AND e.Estado = 'Activo'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El trabajador no existe o está inactivo.';
    END IF;

    INSERT INTO `Asistencia` (`ID_Trabajador`, `Fecha_Entrada`)
    VALUES (p_id_trabajador, COALESCE(p_fecha_entrada, CURRENT_TIMESTAMP));
END $$

CREATE PROCEDURE `sp_registrar_salida_asistencia`(
    IN p_id_trabajador INT,
    IN p_fecha_salida DATETIME
)
BEGIN
    UPDATE `Asistencia`
    SET `Fecha_Salida` = COALESCE(p_fecha_salida, CURRENT_TIMESTAMP)
    WHERE `ID_Trabajador` = p_id_trabajador
      AND `Fecha_Calculada` = CURRENT_DATE
      AND `Fecha_Salida` IS NULL;

    IF ROW_COUNT() = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No existe una asistencia de entrada pendiente para hoy.';
    END IF;
END $$

CREATE PROCEDURE `sp_asignar_tarea`(
    IN p_id_trabajador INT,
    IN p_id_administrador_asignador INT,
    IN p_id_proyecto INT,
    IN p_fecha DATE,
    IN p_fecha_inicio DATETIME,
    IN p_fecha_entrega DATETIME,
    IN p_descripcion_tarea TEXT,
    IN p_observaciones TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM `Trabajadores` t
        INNER JOIN `Empleados` e ON e.ID_Empleado = t.ID_Empleado
        WHERE t.ID_Trabajador = p_id_trabajador
          AND e.Estado = 'Activo'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El trabajador no existe o está inactivo.';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM `Proyectos`
        WHERE `ID_Proyecto` = p_id_proyecto
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El proyecto indicado no existe.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM `Administrador` a
        INNER JOIN `Empleados` e ON e.ID_Empleado = a.ID_Empleado
        WHERE a.ID_Administrador = p_id_administrador_asignador
          AND e.Estado = 'Activo'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El administrador asignador no existe o está inactivo.';
    END IF;

    IF p_descripcion_tarea IS NULL OR TRIM(p_descripcion_tarea) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La descripción de la tarea es obligatoria.';
    END IF;

    INSERT INTO `Tareas` (
        `ID_Trabajador`, `ID_Administrador_Asignador`, `ID_Proyecto`, `Fecha`,
        `Fecha_Inicio`, `Fecha_Entrega`, `Descripcion_Tarea`, `Observaciones`
    ) VALUES (
        p_id_trabajador, p_id_administrador_asignador, p_id_proyecto,
        COALESCE(p_fecha, CURRENT_DATE), p_fecha_inicio, p_fecha_entrega,
        TRIM(p_descripcion_tarea), p_observaciones
    );
END $$

CREATE PROCEDURE `sp_registrar_actividad`(
    IN p_id_tarea INT,
    IN p_fecha_actividad DATETIME,
    IN p_descripcion_actividad TEXT,
    IN p_estado_actividad VARCHAR(20),
    IN p_observaciones TEXT
)
BEGIN
    SET p_estado_actividad = COALESCE(p_estado_actividad, 'Pendiente');

    IF NOT EXISTS (
        SELECT 1 FROM `Tareas`
        WHERE `ID_Tarea` = p_id_tarea
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La tarea indicada no existe.';
    END IF;

    IF p_descripcion_actividad IS NULL OR TRIM(p_descripcion_actividad) = '' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La descripción de la actividad es obligatoria.';
    END IF;

    IF p_estado_actividad NOT IN ('Pendiente', 'En Progreso', 'Completada') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El estado de la actividad no es válido.';
    END IF;

    INSERT INTO `Actividades` (
        `ID_Tarea`, `Fecha_Actividad`, `Descripcion_Actividad`,
        `Estado_Actividad`, `Observaciones`
    ) VALUES (
        p_id_tarea, COALESCE(p_fecha_actividad, CURRENT_TIMESTAMP),
        TRIM(p_descripcion_actividad), p_estado_actividad, p_observaciones
    );
END $$

<<<<<<< HEAD
DELIMITER ;
=======
DELIMITER ;
>>>>>>> 7376e4ff6055d81d744e3173a0200498899e29eb
