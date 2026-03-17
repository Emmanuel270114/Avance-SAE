/**
 * Módulo común para UI de validación/rechazo (botones + panel de motivo)
 * Reutilizable en Resumen Dinámico (Matrícula / Egresados / otros formatos).
 */

function _notify(kind, text) {
  // Si existe SweetAlert2, úsalo. Si no, cae a alert.
  try {
    if (typeof Swal !== 'undefined' && Swal?.fire) {
      const icon = kind === 'success' ? 'success' : (kind === 'warning' ? 'warning' : 'error');
      return Swal.fire({ icon, title: text, confirmButtonText: 'OK' });
    }
  } catch (_) {}
  alert(text);
}

function initValidacionRechazo(config) {
  const cfg = config || {};

  const rolesPermitidos = Array.isArray(cfg.rolesPermitidos) ? cfg.rolesPermitidos : [];
  const idRol = Number(cfg.idRol);
  const puedeValidar = Boolean(cfg.puedeValidar);
  const usuarioYaValido = Boolean(cfg.usuarioYaValido);
  const usuarioYaRechazo = Boolean(cfg.usuarioYaRechazo);

  const endpoints = cfg.endpoints || {};
  const buildValidarPayload = typeof cfg.buildValidarPayload === 'function' ? cfg.buildValidarPayload : (() => ({}));
  const buildRechazarPayload = typeof cfg.buildRechazarPayload === 'function' ? cfg.buildRechazarPayload : ((_motivo) => ({}));

  // Hooks opcionales para flujos especiales (SweetAlert, confirmaciones, etc.)
  const beforeValidar = typeof cfg.beforeValidar === 'function' ? cfg.beforeValidar : null; // async () => boolean
  const beforeRechazar = typeof cfg.beforeRechazar === 'function' ? cfg.beforeRechazar : null; // async (motivo) => boolean
  const onValidado = typeof cfg.onValidado === 'function' ? cfg.onValidado : null; // async (data, res) => void
  const onRechazado = typeof cfg.onRechazado === 'function' ? cfg.onRechazado : null; // async (data, res) => void

  const ui = {
    btnValidar: document.getElementById(cfg.btnValidarId || 'btn-validar'),
    btnRechazar: document.getElementById(cfg.btnRechazarId || 'btn-rechazar'),
    contenedor: document.getElementById(cfg.contenedorId || 'contenedor-botones-validacion'),
    mensaje: document.getElementById(cfg.mensajeId || 'mensaje-validacion'),
    panel: document.getElementById(cfg.panelId || 'panel-rechazo'),
    motivo: document.getElementById(cfg.motivoId || 'motivo-rechazo'),
    contador: document.getElementById(cfg.contadorId || 'contador-caracteres'),
    btnConfirmar: document.querySelector(cfg.btnConfirmarSelector || '.btn-confirmar-rechazo'),
  };

  function actualizarContador() {
    if (!ui.motivo || !ui.contador) return;
    ui.contador.textContent = String((ui.motivo.value || '').length);
  }

  function abrirPanelRechazo() {
    if (ui.panel) ui.panel.style.display = 'block';
    if (ui.motivo) ui.motivo.focus();
    actualizarContador();
  }

  function cerrarPanelRechazo() {
    if (ui.panel) ui.panel.style.display = 'none';
    if (ui.motivo) ui.motivo.value = '';
    actualizarContador();
  }

  function verificarEstadoValidacion() {
    if (!ui.btnValidar || !ui.btnRechazar || !ui.contenedor || !ui.mensaje) return;

    // Normalizar clases de estado para que el banner tenga el mismo estilo en todos los módulos
    try {
      ui.mensaje.classList.remove('validada', 'rechazada', 'esperando');
    } catch (_) {}

    // Caso 1: ya existe un resultado (validado o rechazado) por este usuario
    if (usuarioYaValido || usuarioYaRechazo) {
      ui.contenedor.style.display = 'none';
      ui.mensaje.style.display = 'block';
      try { ui.mensaje.classList.add(usuarioYaValido ? 'validada' : 'rechazada'); } catch (_) {}
      ui.mensaje.innerHTML = usuarioYaValido
        ? (cfg.htmlYaValido || '<i class="fas fa-lock"></i> Ya registraste tu validación para este resumen.')
        : (cfg.htmlYaRechazo || '<i class="fas fa-lock"></i> Ya registraste un rechazo para este resumen.');
      return;
    }

    // Caso 2: no es el turno de validación para este rol (flujo/semaforo no compatible)
    if (!puedeValidar) {
      ui.contenedor.style.display = 'none';
      ui.mensaje.style.display = 'block';
      try { ui.mensaje.classList.add('esperando'); } catch (_) {}
      ui.mensaje.innerHTML = cfg.htmlNoTurno || '<i class="fas fa-info-circle"></i> Aún no es tu turno de validación.';
      return;
    }

    // Caso 3: sí puede validar (se muestra contenedor normalmente)
    ui.contenedor.style.display = '';
    ui.mensaje.style.display = 'none';
  }

  async function ejecutarValidacion() {
    if (!endpoints.validar) {
      _notify('error', 'No se configuró el endpoint de validación.');
      return;
    }

    if (ui.btnValidar?.disabled) {
      _notify('warning', cfg.msgValidarBloqueado || 'No puedes validar en este momento.');
      return;
    }

    if (beforeValidar) {
      const ok = await Promise.resolve(beforeValidar());
      if (!ok) return;
    }

    if (ui.btnValidar) ui.btnValidar.disabled = true;
    if (ui.btnRechazar) ui.btnRechazar.disabled = true;

    try {
      const res = await fetch(endpoints.validar, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildValidarPayload()),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data?.success === false) {
        throw new Error(data?.detail || data?.message || 'No se pudo validar');
      }
      if (onValidado) {
        await Promise.resolve(onValidado(data, res));
      } else {
        _notify('success', cfg.msgValidado || '✅ Validado correctamente');
      }
      if (!cfg.noReloadOnSuccess) location.reload();
    } catch (err) {
      console.error(err);
      _notify('error', (cfg.msgErrorValidarPrefix || '❌ Error al validar: ') + (err?.message || err));
      if (ui.btnValidar) ui.btnValidar.disabled = false;
      if (ui.btnRechazar) ui.btnRechazar.disabled = false;
    }
  }

  async function ejecutarRechazo() {
    if (!endpoints.rechazar) {
      _notify('error', 'No se configuró el endpoint de rechazo.');
      return;
    }

    const motivo = (ui.motivo?.value || '').trim();
    if (!motivo) {
      _notify('warning', cfg.msgMotivoVacio || 'Escribe un motivo de rechazo.');
      return;
    }

    if (beforeRechazar) {
      const ok = await Promise.resolve(beforeRechazar(motivo));
      if (!ok) return;
    }

    if (ui.btnConfirmar) ui.btnConfirmar.disabled = true;

    try {
      const res = await fetch(endpoints.rechazar, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildRechazarPayload(motivo)),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data?.success === false) {
        throw new Error(data?.detail || data?.message || 'No se pudo rechazar');
      }
      if (onRechazado) {
        await Promise.resolve(onRechazado(data, res));
      } else {
        _notify('success', cfg.msgRechazado || '🔴 Rechazado.');
      }
      if (!cfg.noReloadOnSuccess) location.reload();
    } catch (err) {
      console.error(err);
      _notify('error', (cfg.msgErrorRechazarPrefix || '❌ Error al rechazar: ') + (err?.message || err));
      if (ui.btnConfirmar) ui.btnConfirmar.disabled = false;
    }
  }

  // Exponer handlers para onclick existentes.
  window.__validacionRechazo = {
    verificarEstadoValidacion,
    ejecutarValidacion,
    abrirPanelRechazo,
    cerrarPanelRechazo,
    actualizarContador,
    ejecutarRechazo,
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (!rolesPermitidos.includes(idRol)) return;
    verificarEstadoValidacion();

    // Si no hay onclick en HTML, lo amarramos.
    if (ui.btnValidar && !ui.btnValidar.getAttribute('onclick')) {
      ui.btnValidar.addEventListener('click', ejecutarValidacion);
    }
    if (ui.btnRechazar && !ui.btnRechazar.getAttribute('onclick')) {
      ui.btnRechazar.addEventListener('click', abrirPanelRechazo);
    }
    if (ui.motivo) ui.motivo.addEventListener('input', actualizarContador);
  });

  return window.__validacionRechazo;
}

try { window.initValidacionRechazo = initValidacionRechazo; } catch (_) {}
