const $ = s => document.querySelector(s);

let user = null;
let projects = [];
let workers = [];

const notice = (message, type = 'success') => {
  const n = $('#notice');
  n.textContent = message;
  n.className = `notice ${type}`;
  setTimeout(() => n.className = 'notice hidden', 4000);
};

const api = async (url, options = {}) => {
  const config = { credentials: 'include', ...options };
  config.headers = { ...(options.body ? {'Content-Type': 'application/json'} : {}), ...(options.headers || {}) };

  const response = await fetch(url, config);
  let payload = null;
  try { payload = await response.json(); } catch (_) {}

  if (!response.ok) {
    throw new Error(payload?.detail || payload?.error || 'Ocurrió un error en el servidor.');
  }
  return payload;
};

const time = value => value
  ? new Date(value).toLocaleTimeString('es-PE', {hour:'2-digit', minute:'2-digit'})
  : '—';

const date = value => value
  ? new Date(`${value}T00:00:00`).toLocaleDateString('es-PE')
  : '—';

const escape = value => String(value ?? '').replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])
);

function renderTable(columns, rows) {
  if (!rows.length) return '<p class="empty">Aún no hay registros para mostrar.</p>';
  return `<table><thead><tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr></thead>
    <tbody>${rows.join('')}</tbody></table>`;
}

/* ---------------- LOGIN ---------------- */

document.querySelectorAll('.role-card').forEach(button => {
  button.addEventListener('click', () => {
    $('#roleStep').classList.add('hidden');
    $('#credentialStep').classList.remove('hidden');
    $('#loginRoleLabel').textContent = `ACCESO ${button.dataset.role.toUpperCase()}`;
    $('#loginForm').dataset.role = button.dataset.role;
  });
});

$('#backRole').onclick = () => {
  $('#credentialStep').classList.add('hidden');
  $('#roleStep').classList.remove('hidden');
};

$('#loginForm').addEventListener('submit', async event => {
  event.preventDefault();

  const code = $('#loginCode').value.trim().toUpperCase();
  const pin = $('#loginPin').value.trim();
  const role = event.currentTarget.dataset.role;

  try {
    const result = await api('/api/login', {
      method: 'POST',
      body: JSON.stringify({ code, pin, role })
    });

    user = result.user;
    await startApp();
  } catch (error) {
    notice(error.message, 'error');
  }
});

$('#logout').onclick = async () => {
  try { await api('/api/logout', {method: 'POST'}); } catch (_) {}
  user = null;
  $('#appView').classList.add('hidden');
  $('#loginView').classList.remove('hidden');
  $('#loginForm').reset();
  $('#credentialStep').classList.add('hidden');
  $('#roleStep').classList.remove('hidden');
};

/* ---------------- NAVEGACIÓN ---------------- */

document.querySelectorAll('.nav-link').forEach(button => {
  button.onclick = () => showView(button.dataset.view);
});

async function showView(id) {
  document.querySelectorAll('.view').forEach(v =>
    v.classList.toggle('hidden', v.id !== id)
  );
  document.querySelectorAll('.nav-link').forEach(b =>
    b.classList.toggle('active', b.dataset.view === id)
  );

  const titles = {
    attendance: 'Mi jornada',
    tasks: 'Gestión de tareas',
    monitor: 'Monitoreo de la oficina',
    people: 'Administración de personal'
  };

  $('#pageTitle').textContent = titles[id];

  try {
    if (id === 'attendance') await renderAttendance();
    if (id === 'tasks') await renderTasks();
    if (id === 'monitor') await renderMonitor();
    if (id === 'people') await renderPeople();
  } catch (error) {
    notice(error.message, 'error');
  }
}

async function startApp() {
  $('#loginView').classList.add('hidden');
  $('#appView').classList.remove('hidden');

  const admin = user.role === 'Administrador';
  document.querySelectorAll('.admin-only').forEach(el =>
    el.classList.toggle('hidden', !admin)
  );

  $('#sideName').textContent = user.name;
  $('#sidePosition').textContent = `${user.position} · ${user.role}`;
  $('#welcomeName').textContent = `Hola, ${user.name.split(' ')[0]}`;
  $('#avatar').textContent = user.name.split(' ').map(x => x[0]).slice(0,2).join('');
  $('#today').textContent = new Date().toLocaleDateString('es-PE', {
    weekday:'long', day:'numeric', month:'long'
  });

  await showView('attendance');
}

/* ---------------- ASISTENCIA ---------------- */

async function renderAttendance() {
  if (user.role !== 'Empleado') {
    $('#entryInfo').textContent = 'Los administradores no registran asistencia.';
    $('#exitInfo').textContent = 'Acceso de solo administración.';
    $('#markEntry').disabled = true;
    $('#markExit').disabled = true;
    $('#myAttendance').innerHTML = '<p class="empty">Vista administrativa.</p>';
    return;
  }

  const record = await api('/api/attendance');

  $('#entryInfo').textContent = record
    ? `Entrada: ${time(record.entry)}`
    : 'Inicie su jornada laboral.';

  $('#exitInfo').textContent = record?.exit
    ? `Salida: ${time(record.exit)}`
    : 'Finalice su jornada cuando corresponda.';

  $('#markEntry').disabled = !!record;
  $('#markExit').disabled = !record || !!record.exit;

  const status = record
    ? (record.exit ? 'Finalizada' : 'En jornada')
    : 'Pendiente';

  $('#attendanceStatus').textContent = status;
  $('#attendanceStatus').className =
    `status ${record ? (record.exit ? 'done' : 'active') : 'neutral'}`;

  $('#myAttendance').innerHTML = record
    ? renderTable(
        ['Fecha','Entrada','Salida'],
        [`<tr><td>${date(record.date)}</td>
          <td>${time(record.entry)}</td>
          <td>${record.exit ? time(record.exit) : '<span class="tag">Activo</span>'}</td></tr>`]
      )
    : '<p class="empty">No ha marcado asistencia todavía.</p>';
}

$('#markEntry').onclick = async () => {
  try {
    await api('/api/attendance/entry', {method:'POST'});
    await renderAttendance();
    notice('Entrada registrada con éxito. ¡Buen día!');
  } catch (error) {
    notice(error.message, 'error');
  }
};

$('#markExit').onclick = async () => {
  try {
    await api('/api/attendance/exit', {method:'PATCH'});
    await renderAttendance();
    notice('Salida registrada correctamente.');
  } catch (error) {
    notice(error.message, 'error');
  }
};

/* ---------------- TAREAS ---------------- */

async function loadProjects() {
  projects = await api('/api/projects');
  $('#taskProject').innerHTML = projects
    .map(p => `<option value="${p.id}">${escape(p.name)}</option>`)
    .join('');
}

async function loadWorkers() {
  if (user.role !== 'Administrador') return;
  workers = await api('/api/workers');

  const select = $('#taskWorker');
  if (!select) return;

  select.innerHTML = workers
    .filter(w => w.status === 'Activo')
    .map(w => `<option value="${w.id}">${escape(w.name)} — ${escape(w.code)}</option>`)
    .join('') || '<option value="">Sin trabajadores activos</option>';
}

async function renderTasks() {
  await loadProjects();
  await loadWorkers();

  const own = await api('/api/tasks');

  $('#taskUpdate').innerHTML = own.length
    ? `<form class="update-form" id="updateTaskForm">
        <label>Tarea
          <select id="updateTask">
            ${own.map(t => `<option value="${t.id}">
              ${escape(t.project)} — ${escape(t.description)}
            </option>`).join('')}
          </select>
        </label>
        <label>Nuevo estado
          <select id="updateState">
            <option>En Progreso</option>
            <option>Completada</option>
            <option>Bloqueada</option>
          </select>
        </label>
        <label>Observaciones
          <input id="updateNotes" placeholder="Obligatorio si está bloqueada">
        </label>
        <button class="primary">Actualizar estado</button>
      </form>`
    : '<p class="empty">No hay tareas creadas para hoy.</p>';

  const form = $('#updateTaskForm');
  if (form) form.onsubmit = updateTask;
}

$('#taskForm').onsubmit = async e => {
  e.preventDefault();

  const description = $('#taskDescription').value.trim();
  const projectId = Number($('#taskProject').value);
  const workerElement = $('#taskWorker');

  if (!description) return notice('Ingrese una descripción.', 'error');

  try {
    await api('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        projectId,
        description,
        state: $('#taskState').value,
        workerId: workerElement ? Number(workerElement.value) : null
      })
    });

    e.target.reset();
    await renderTasks();
    notice('Actividad registrada correctamente.');
  } catch (error) {
    notice(error.message, 'error');
  }
};

async function updateTask(e) {
  e.preventDefault();

  const state = $('#updateState').value;
  const notes = $('#updateNotes').value.trim();

  if (state === 'Bloqueada' && !notes)
    return notice('Describa las observaciones antes de bloquear la tarea.', 'warning');

  try {
    await api(`/api/tasks/${Number($('#updateTask').value)}`, {
      method: 'PATCH',
      body: JSON.stringify({state, notes})
    });

    await renderTasks();
    notice('Estado de la actividad actualizado.');
  } catch (error) {
    notice(error.message, 'error');
  }
}

/* ---------------- MONITOREO ---------------- */

async function renderMonitor() {
  const result = await api('/api/monitor');
  const asis = result.attendance || [];
  const tasks = result.tasks || [];
  const active = asis.filter(a => !a.exit).length;

  $('#metrics').innerHTML = [
    [`${active}`, 'En jornada'],
    [`${asis.length}`, 'Entradas hoy'],
    [`${tasks.filter(t => t.state === 'Completada').length}`, 'Tareas completadas']
  ].map(x => `<article class="metric"><strong>${x[0]}</strong><span>${x[1]}</span></article>`).join('');

  $('#attendanceTable').innerHTML = renderTable(
    ['Colaborador','Código','Entrada','Salida'],
    asis.map(a => `<tr>
      <td>${escape(a.employee)}</td>
      <td>${escape(a.code)}</td>
      <td>${time(a.entry)}</td>
      <td>${a.exit ? time(a.exit) : '<span class="tag">Activo</span>'}</td>
    </tr>`)
  );

  $('#tasksTable').innerHTML = renderTable(
    ['Colaborador','Proyecto','Actividad','Estado'],
    tasks.map(t => `<tr>
      <td>${escape(t.employee)}</td>
      <td>${escape(t.project)}</td>
      <td>${escape(t.description)}</td>
      <td><span class="tag">${escape(t.state)}</span></td>
    </tr>`)
  );
}

$('#refreshMonitor').onclick = async () => {
  try {
    await renderMonitor();
    notice('Panel actualizado.');
  } catch (error) {
    notice(error.message, 'error');
  }
};

/* ---------------- PERSONAL Y PROYECTOS ---------------- */

async function renderPeople() {
  const people = await api('/api/people');

  $('#peopleTable').innerHTML = renderTable(
    ['Nombre','Cargo','Código','Estado'],
    people.map(p => `<tr>
      <td>${escape(p.name)}</td>
      <td>${escape(p.position)}</td>
      <td>${escape(p.code)}</td>
      <td>${p.status === 'Activo'
        ? '<span class="tag">Activo</span>'
        : '<span class="tag">Inactivo</span>'}</td>
    </tr>`)
  );

  const active = people.filter(p => p.status === 'Activo' && p.id !== user.id);
  $('#deactivatePerson').innerHTML = active
    .map(p => `<option value="${p.id}">${escape(p.name)}</option>`)
    .join('') || '<option value="">Sin opciones</option>';
}

$('#personForm').onsubmit = async e => {
  e.preventDefault();

  const pin = $('#personPin').value.trim();
  if (!/^\d{4}$/.test(pin))
    return notice('El PIN debe tener 4 dígitos.', 'error');

  try {
    await api('/api/workers', {
      method: 'POST',
      body: JSON.stringify({
        name: $('#personName').value.trim(),
        position: $('#personPosition').value.trim(),
        code: $('#personCode').value.trim().toUpperCase(),
        pin,
        role: $('#personRole').value
      })
    });

    e.target.reset();
    await renderPeople();
    await loadWorkers();
    notice('Trabajador registrado correctamente.');
  } catch (error) {
    notice(error.message, 'error');
  }
};

$('#projectForm').onsubmit = async e => {
  e.preventDefault();

  try {
    await api('/api/projects', {
      method: 'POST',
      body: JSON.stringify({
        name: $('#projectName').value.trim(),
        area: $('#projectArea').value.trim()
      })
    });

    e.target.reset();
    notice('Proyecto registrado correctamente.');
  } catch (error) {
    notice(error.message, 'error');
  }
};

$('#deactivateButton').onclick = async () => {
  const id = Number($('#deactivatePerson').value);
  if (!id) return;

  try {
    await api(`/api/people/${id}/deactivate`, {method:'PATCH'});
    await renderPeople();
    await loadWorkers();
    notice('Trabajador dado de baja correctamente.');
  } catch (error) {
    notice(error.message, 'error');
  }
};

/* ---------------- RELOJ ---------------- */

setInterval(() => {
  $('#clock').textContent = new Date().toLocaleTimeString('es-PE', {
    hour:'2-digit', minute:'2-digit', second:'2-digit'
  });
}, 1000);

/* No se cargan usuarios, tareas ni asistencia desde JavaScript.
   Toda la información procede de la API REST y MySQL. */
