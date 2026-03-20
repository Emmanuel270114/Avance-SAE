// JavaScript para formularios - Lógica de formularios de usuario

document.addEventListener('DOMContentLoaded', function() {
    // --- Lógica cascada: UA → Rol → Nivel ---
    const selectUA = document.getElementById('id_unidad_academica');
    const selectRol = document.getElementById('id_rol');
    const selectNivel = document.getElementById('id_nivel');
    const ROL_CAPTURISTA = '3';
    const ROLES_SIN_NIVEL = new Set(['6', '7', '8', '9']);

    function esRolSinNivel(idRol) {
        return ROLES_SIN_NIVEL.has(String(idRol || ''));
    }

    function esRolRequiereFormato(idRol) {
        return String(idRol || '') === ROL_CAPTURISTA;
    }

    function limpiarOpcionesRolDinamicas() {
        if (!selectRol) return;
        Array.from(selectRol.options)
            .filter(opt => opt.dataset && opt.dataset.dynamicRol === '1')
            .forEach(opt => opt.remove());
    }

    function asegurarOpcionRolActual(idRol, rolNombre) {
        if (!selectRol || !idRol) return;
        const idRolStr = String(idRol);
        const existe = Array.from(selectRol.options).some(opt => String(opt.value) === idRolStr);
        if (existe) return;

        const opcion = document.createElement('option');
        opcion.value = idRolStr;
        opcion.textContent = rolNombre || 'Rol actual';
        opcion.dataset.dynamicRol = '1';
        selectRol.appendChild(opcion);
    }

    function habilitarRolPorUA() {
        const uaSeleccionada = selectUA && selectUA.value;
        if (selectRol) {
            if (uaSeleccionada) {
                selectRol.removeAttribute('disabled');
                selectRol.title = 'Selecciona un rol';
            } else {
                selectRol.setAttribute('disabled', 'disabled');
                selectRol.title = 'Selecciona primero una Unidad Académica';
                selectRol.value = '';
                // Limpiar Nivel al cambiar/limpiar UA
                if (selectNivel) {
                    selectNivel.value = '';
                    selectNivel.setAttribute('disabled', 'disabled');
                    selectNivel.removeAttribute('required');
                    selectNivel.title = 'Selecciona primero un Rol';
                }
            }
        }
    }

    function habilitarNivelPorRol(opciones = {}) {
        const recargarNiveles = opciones.recargarNiveles !== false;
        const rolSeleccionado = selectRol && selectRol.value;
        const rolRequiereNivel = rolSeleccionado && !esRolSinNivel(rolSeleccionado);
        if (selectNivel) {
            if (rolRequiereNivel) {
                selectNivel.removeAttribute('disabled');
                selectNivel.setAttribute('required', 'required');
                selectNivel.title = 'Selecciona un nivel';
                if (selectNivel.options && selectNivel.options.length > 0 && selectNivel.options[0].value === '') {
                    selectNivel.options[0].textContent = '-- Seleccione un Nivel --';
                }
                // Cargar niveles según UA
                const uaSeleccionada = selectUA ? selectUA.value : null;
                if (uaSeleccionada && recargarNiveles) {
                    const nivelActual = selectNivel.value || '';
                    cargarNivelesPorUA(uaSeleccionada, nivelActual);
                }
            } else if (rolSeleccionado) {
                selectNivel.value = '';
                selectNivel.setAttribute('disabled', 'disabled');
                selectNivel.removeAttribute('required');
                selectNivel.title = 'No aplica para este rol';
                if (selectNivel.options && selectNivel.options.length > 0 && selectNivel.options[0].value === '') {
                    selectNivel.options[0].textContent = '-- No aplica para este Rol --';
                }

                const hiddenNivel = document.getElementById('id_nivel_hidden');
                if (hiddenNivel) hiddenNivel.value = '';
            } else {
                selectNivel.setAttribute('disabled', 'disabled');
                selectNivel.removeAttribute('required');
                selectNivel.title = 'Selecciona primero un Rol';
                selectNivel.value = '';
            }
        }

        // Mostrar/ocultar formatos según si es Capturista (ID 3)
        const formatosRow = document.getElementById('formatos-row');
        if (formatosRow) {
            const esCapturista = rolSeleccionado === ROL_CAPTURISTA;
            if (esCapturista) {
                formatosRow.style.display = '';
            } else {
                formatosRow.style.display = 'none';
                // Limpiar formatos si se quita Capturista
                limpiarSeleccionFormatos();
            }
        }
    }

    async function cargarNivelesPorUA(idUA, nivelPreseleccionado = null) {
        if (!idUA) return;
        try {
            const response = await fetch(`/registro/niveles-por-ua/${idUA}`);
            if (!response.ok) throw new Error('No se pudo obtener niveles');
            const niveles = await response.json();
            const nivelObjetivo = nivelPreseleccionado !== null && nivelPreseleccionado !== undefined
                ? String(nivelPreseleccionado)
                : String(selectNivel.value || '');
            selectNivel.innerHTML = '<option value="">-- Seleccione un Nivel --</option>';
            const hiddenNivel = document.getElementById('id_nivel_hidden');
            if (niveles.length > 0) {
                niveles.forEach(nivel => {
                    const opt = document.createElement('option');
                    opt.value = nivel.Id_Nivel;
                    opt.textContent = nivel.Nivel;
                    selectNivel.appendChild(opt);
                });
                const existeNivelObjetivo = nivelObjetivo && niveles.some(n => String(n.Id_Nivel) === nivelObjetivo);
                if (existeNivelObjetivo) {
                    selectNivel.value = nivelObjetivo;
                    if (hiddenNivel) hiddenNivel.value = nivelObjetivo;
                } else if (hiddenNivel) {
                    hiddenNivel.value = '';
                }
            } else {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Sin niveles disponibles';
                selectNivel.appendChild(opt);
                if (hiddenNivel) hiddenNivel.value = '';
            }
        } catch (err) {
            selectNivel.innerHTML = '<option value="">Error al cargar niveles</option>';
            const hiddenNivel = document.getElementById('id_nivel_hidden');
            if (hiddenNivel) hiddenNivel.value = '';
        }
    }

    // Iniciar estado cascada
    if (selectUA && selectRol && selectNivel) {
        // Si UA está bloqueada, habilitar Rol y cargar Niveles
        if (selectUA.disabled || selectUA.hasAttribute('readonly')) {
            selectRol.removeAttribute('disabled');
            if (selectUA.value) {
                cargarNivelesPorUA(selectUA.value);
                selectNivel.removeAttribute('disabled');
            }
        } else {
            // Si UA no está bloqueada, asegurarse de que el estado inicial es correcto
            habilitarRolPorUA();
        }

        // Evento: UA cambia (usar 'input' además de 'change' para máxima compatibilidad)
        selectUA.addEventListener('change', function() {
            habilitarRolPorUA();
        });
        selectUA.addEventListener('input', function() {
            habilitarRolPorUA();
        });

        // Evento: Rol cambia
        selectRol.addEventListener('change', function() {
            habilitarNivelPorRol();
        });
        selectRol.addEventListener('input', function() {
            habilitarNivelPorRol();
        });

        // Evento: Nivel cambia (sincronizar hidden si existe)
        selectNivel.addEventListener('change', function() {
            const hiddenNivel = document.getElementById('id_nivel_hidden');
            if (hiddenNivel) hiddenNivel.value = this.value;
        });
    }

    // Estado: edición o registro
    let editando = false;
    let idUsuarioEdit = null;
    const formatosContainer = document.getElementById('formatos-container');
    const formatoCheckboxes = Array.from(document.querySelectorAll('input[name="id_formatos"]'));

    function marcarErrorFormatos(marcar) {
        if (!formatosContainer) return;
        if (marcar) {
            formatosContainer.classList.add('input-error');
        } else {
            formatosContainer.classList.remove('input-error');
        }
    }

    function seleccionarFormatos(ids) {
        if (!formatoCheckboxes.length) return;
        const idsSet = new Set((ids || []).map(String));
        formatoCheckboxes.forEach(checkbox => {
            checkbox.checked = idsSet.has(String(checkbox.value));
        });
        marcarErrorFormatos(false);
    }

    function limpiarSeleccionFormatos() {
        if (!formatoCheckboxes.length) return;
        formatoCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        marcarErrorFormatos(false);
    }

    formatoCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                marcarErrorFormatos(false);
            }
        });
    });

    // Función para sugerir usuario basado en email
    window.sugerirUsuario = function() {
        const correo = document.getElementById('email').value.trim();
        let usuario = correo.split('@')[0];
        document.getElementById('usuario').value = usuario;
    };

    // Al hacer clic en una fila de usuario, cargar datos en el formulario
    document.querySelectorAll('.fila-usuario').forEach(fila => {
        fila.addEventListener('click', async function() {
            editando = true;
            idUsuarioEdit = this.dataset.id;
            if (window.setIdUsuarioEdit) {
                window.setIdUsuarioEdit(idUsuarioEdit);
            }
            document.getElementById('id_usuario').value = this.dataset.id;
            document.getElementById('nombre').value = this.dataset.nombre;
            document.getElementById('ap_pat').value = this.dataset.paterno;
            document.getElementById('ap_mat').value = this.dataset.materno;
            document.getElementById('usuario').value = this.dataset.usuario;
            document.getElementById('email').value = this.dataset.email;
            document.getElementById('id_unidad_academica').value = this.getAttribute('data-id_unidad');
            limpiarOpcionesRolDinamicas();
            asegurarOpcionRolActual(this.dataset.id_rol, this.dataset.rol_nombre);
            document.getElementById('id_rol').value = this.dataset.id_rol;
            const formatosCsv = this.getAttribute('data-formatos') || '';
            const formatosSeleccionados = formatosCsv
                .split(',')
                .map(v => v.trim())
                .filter(Boolean);
            seleccionarFormatos(formatosSeleccionados);
            
            // --- Aplicar cascada: habilitar Rol si UA está seleccionada ---
            habilitarRolPorUA();
            
            // --- Cargar y habilitar Niveles según UA del usuario ---
            const idUA = this.getAttribute('data-id_unidad');
            const idNivelUsuario = this.dataset.id_nivel;
            if (idUA) {
                await cargarNivelesPorUA(idUA, idNivelUsuario || null);
            } else if (idNivelUsuario) {
                document.getElementById('id_nivel').value = idNivelUsuario;
            }

            // Aplicar lógica de nivel/formatos sin recargar niveles de nuevo
            habilitarNivelPorRol({ recargarNiveles: false });
            
            document.getElementById('titulo-usuario').textContent = 'Editar Usuario';
            document.getElementById('btn-guardar').textContent = 'Actualizar';
            document.getElementById('btn-cancelar').style.display = 'inline-block';
            document.getElementById('btn-eliminar').style.display = 'inline-block';
            document.getElementById('btn-limpiar').style.display = 'none';
            // --- Scroll automático al encabezado 'Bienvenido' y enfoque en el campo nombre ---
            const headerBienvenido = document.querySelector('.bienvenido');
            if (headerBienvenido) {
                headerBienvenido.scrollIntoView({ behavior: 'smooth', block: 'start' });
                setTimeout(() => {
                    const inputNombre = document.getElementById('nombre');
                    if (inputNombre) inputNombre.focus();
                }, 300);
            }
        });
    });
    // --- Lógica para limpiar filtros ---
    const btnLimpiarFiltros = document.getElementById('btn-limpiar-filtros');
    if (btnLimpiarFiltros) {
        btnLimpiarFiltros.addEventListener('click', function() {
            // Limpiar campos de filtro
            const filtroUsuarios = document.getElementById('filtro-usuarios');
            if (filtroUsuarios) filtroUsuarios.value = '';
            const filtroUA = document.getElementById('filtro-ua');
            if (filtroUA) filtroUA.value = '';
            // Lanzar evento input/change para recargar la tabla si aplica
            if (filtroUsuarios) filtroUsuarios.dispatchEvent(new Event('input'));
            if (filtroUA) filtroUA.dispatchEvent(new Event('change'));
        });
    }

    // Botón cancelar
    const btnCancelar = document.getElementById('btn-cancelar');
    if (btnCancelar) {
        btnCancelar.addEventListener('click', function() {
            editando = false;
            idUsuarioEdit = null;
            
            document.getElementById('registroForm').reset();
            limpiarOpcionesRolDinamicas();
            limpiarSeleccionFormatos();
            document.getElementById('titulo-usuario').textContent = 'Registro Usuario';
            document.getElementById('btn-guardar').textContent = 'Registrar';
            document.getElementById('btn-cancelar').style.display = 'none';
            document.getElementById('btn-eliminar').style.display = 'none';
            document.getElementById('btn-limpiar').style.display = 'inline-block';
            
            // Limpiar errores visuales
            document.querySelectorAll('.input-error').forEach(input => {
                input.classList.remove('input-error');
            });
            marcarErrorFormatos(false);
        });
    }

    // Botón limpiar
    const btnLimpiar = document.getElementById('btn-limpiar');
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', function() {
            document.getElementById('registroForm').reset();
            limpiarOpcionesRolDinamicas();
            limpiarSeleccionFormatos();
            
            // Limpiar errores visuales
            document.querySelectorAll('.input-error').forEach(input => {
                input.classList.remove('input-error');
            });
            marcarErrorFormatos(false);
        });
    }

    // Manejo del formulario de registro/edición
    const registroForm = document.getElementById('registroForm');
    if (registroForm) {
        registroForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            let rawData = Object.fromEntries(formData.entries());
            
            // Para unidad académica, usar el valor del hidden si el select está disabled
            let idUnidadAcademica;
            const selectUA = document.getElementById('id_unidad_academica');
            if (selectUA && selectUA.disabled) {
                const hiddenUA = document.getElementById('id_unidad_academica_hidden');
                idUnidadAcademica = hiddenUA ? parseInt(hiddenUA.value) : null;
            } else {
                idUnidadAcademica = rawData.id_unidad_academica ? parseInt(rawData.id_unidad_academica) : null;
            }
            // Para nivel, usar el valor del hidden si el select está disabled
            let idNivel;
            const selectNivel = document.getElementById('id_nivel');
            const hiddenNivel = document.getElementById('id_nivel_hidden');
            const idRol = rawData.id_rol ? parseInt(rawData.id_rol, 10) : null;

            if (esRolSinNivel(idRol)) {
                idNivel = null;
            } else if (hiddenNivel && hiddenNivel.value) {
                idNivel = parseInt(hiddenNivel.value, 10);
            } else if (selectNivel && selectNivel.value) {
                idNivel = parseInt(selectNivel.value, 10);
            } else {
                idNivel = null;
            }

            const idFormatos = formatoCheckboxes
                .filter(checkbox => checkbox.checked)
                .map(checkbox => parseInt(checkbox.value, 10))
                .filter(value => !Number.isNaN(value));

            if (esRolRequiereFormato(idRol) && !idFormatos.length) {
                document.getElementById('mensaje').innerHTML = "<p style='color:red;'>❌ Debes seleccionar al menos un formato.</p>";
                marcarErrorFormatos(true);
                return;
            }

            // Transformar datos al formato esperado por el backend (tanto para registro como edición)
            let data = {
                Nombre: rawData.nombre,
                Paterno: rawData.paterno,
                Materno: rawData.materno,
                Email: rawData.email,
                Id_Rol: idRol,
                Usuario: rawData.usuario,
                Id_Unidad_Academica: idUnidadAcademica,
                Id_Nivel: idNivel,
                Id_Formatos: idFormatos
            };
            
            // Para registro, agregar campos adicionales requeridos
            if (!editando) {
                data.Id_Estatus = 1; // Activo por defecto
            }
            
            // URL según si es edición o registro
            const url = editando ? `/usuarios/editar/${idUsuarioEdit}` : '/usuarios/registrar';
            
            try {
                const response = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                
                // Limpiar resaltados previos
                document.getElementById('email').classList.remove('input-error');
                document.getElementById('nombre').classList.remove('input-error');
                document.getElementById('ap_pat').classList.remove('input-error');
                document.getElementById('ap_mat').classList.remove('input-error');
                document.getElementById('usuario').classList.remove('input-error');
                marcarErrorFormatos(false);
                
                if (response.ok && (result.Id_Usuario || result.mensaje)) {
                    document.getElementById("mensaje").innerHTML = `<p style='color:green;'>${editando ? '✅ Usuario actualizado' : '✅ Usuario registrado con ID ' + result.Id_Usuario}</p>`;
                    setTimeout(() => { location.reload(); }, 1200);
                } else {
                    let detail = result.detail || result.mensaje || 'Error desconocido';
                    if (detail.includes('La persona ya está registrada')) {
                        document.getElementById('nombre').classList.add('input-error');
                        document.getElementById('ap_pat').classList.add('input-error');
                        document.getElementById('ap_mat').classList.add('input-error');
                    }
                    if (detail.includes('Email ya está registrado')) {
                        document.getElementById('email').classList.add('input-error');
                    }
                    if (detail.toLowerCase().includes('nombre de usuario')) {
                        document.getElementById('usuario').classList.add('input-error');
                    }
                    if (detail.toLowerCase().includes('formato')) {
                        marcarErrorFormatos(true);
                    }
                    document.getElementById("mensaje").innerHTML = `<p style='color:red;'>❌ ${detail}</p>`;
                }
            } catch (err) {
                document.getElementById("mensaje").innerHTML = `<p style='color:red;'>⚠️ Error de conexión: ${err.message}</p>`;
            }
        });
    }
});