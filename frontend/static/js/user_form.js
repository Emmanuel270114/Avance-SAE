    // --- Lógica para actualizar niveles según UA seleccionada ---
    const selectUA = document.getElementById('id_unidad_academica');
    const selectNivel = document.getElementById('id_nivel');
    async function cargarNivelesPorUA(idUA) {
        if (!idUA) return;
        try {
            const response = await fetch(`/registro/niveles-por-ua/${idUA}`);
            if (!response.ok) throw new Error('No se pudo obtener niveles');
            const niveles = await response.json();
            selectNivel.innerHTML = '';
            const hiddenNivel = document.getElementById('id_nivel_hidden');
            if (niveles.length > 0) {
                selectNivel.removeAttribute('readonly');
                selectNivel.removeAttribute('disabled');
                niveles.forEach(nivel => {
                    const opt = document.createElement('option');
                    opt.value = nivel.Id_Nivel;
                    opt.textContent = nivel.Nivel;
                    selectNivel.appendChild(opt);
                });
                selectNivel.value = niveles[0].Id_Nivel;
                if (hiddenNivel) hiddenNivel.value = selectNivel.value;
            } else {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Sin niveles disponibles';
                selectNivel.appendChild(opt);
                selectNivel.setAttribute('disabled', 'disabled');
                if (hiddenNivel) hiddenNivel.value = '';
            }
        } catch (err) {
            selectNivel.innerHTML = '';
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'Error al cargar niveles';
            selectNivel.appendChild(opt);
            selectNivel.setAttribute('disabled', 'disabled');
            const hiddenNivel = document.getElementById('id_nivel_hidden');
            if (hiddenNivel) hiddenNivel.value = '';
        }
    }

    if (selectUA && selectNivel) {
        // Sincronizar hidden cuando cambia el select de nivel manualmente
        selectNivel.addEventListener('change', function() {
            const hiddenNivel = document.getElementById('id_nivel_hidden');
            if (hiddenNivel) hiddenNivel.value = selectNivel.value;
        });
        // Si la UA está deshabilitada (bloqueada), cargar niveles al inicio
        if (selectUA.disabled || selectUA.hasAttribute('readonly')) {
            cargarNivelesPorUA(selectUA.value);
        }
        // También cargar niveles al cambiar la UA (caso superadmin)
        selectUA.addEventListener('change', function() {
            cargarNivelesPorUA(this.value);
        });
    }
// JavaScript para formularios - Lógica de formularios de usuario

document.addEventListener('DOMContentLoaded', function() {
    // Estado: edición o registro
    let editando = false;
    let idUsuarioEdit = null;

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
            document.getElementById('id_rol').value = this.dataset.id_rol;
            // --- Niveles válidos para la UA del usuario ---
            const idUA = this.getAttribute('data-id_unidad');
            const idNivelUsuario = this.dataset.id_nivel;
            if (idUA) {
                try {
                    const response = await fetch(`/registro/niveles-por-ua/${idUA}`);
                    if (!response.ok) throw new Error('No se pudo obtener niveles');
                    const niveles = await response.json();
                    const selectNivel = document.getElementById('id_nivel');
                    selectNivel.innerHTML = '';
                    niveles.forEach(nivel => {
                        const opt = document.createElement('option');
                        opt.value = nivel.Id_Nivel;
                        opt.textContent = nivel.Nivel;
                        selectNivel.appendChild(opt);
                    });
                    // Seleccionar el nivel actual del usuario
                    if (idNivelUsuario) {
                        selectNivel.value = idNivelUsuario;
                    }
                } catch (err) {
                    // Si falla, dejar el select como está
                }
            } else if (this.dataset.id_nivel) {
                document.getElementById('id_nivel').value = this.dataset.id_nivel;
            }
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
            document.getElementById('titulo-usuario').textContent = 'Datos Usuario';
            document.getElementById('btn-guardar').textContent = 'Registrar';
            document.getElementById('btn-cancelar').style.display = 'none';
            document.getElementById('btn-eliminar').style.display = 'none';
            document.getElementById('btn-limpiar').style.display = 'inline-block';
            
            // Limpiar errores visuales
            document.querySelectorAll('.input-error').forEach(input => {
                input.classList.remove('input-error');
            });
        });
    }

    // Botón limpiar
    const btnLimpiar = document.getElementById('btn-limpiar');
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', function() {
            document.getElementById('registroForm').reset();
            
            // Limpiar errores visuales
            document.querySelectorAll('.input-error').forEach(input => {
                input.classList.remove('input-error');
            });
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
            if (hiddenNivel && hiddenNivel.value) {
                idNivel = parseInt(hiddenNivel.value);
            } else if (selectNivel && selectNivel.value) {
                idNivel = parseInt(selectNivel.value);
            } else {
                idNivel = null;
            }
            // Transformar datos al formato esperado por el backend (tanto para registro como edición)
            let data = {
                Nombre: rawData.nombre,
                Paterno: rawData.paterno,
                Materno: rawData.materno,
                Email: rawData.email,
                Id_Rol: parseInt(rawData.id_rol),
                Usuario: rawData.usuario,
                Id_Unidad_Academica: idUnidadAcademica,
                Id_Nivel: idNivel
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
                    document.getElementById("mensaje").innerHTML = `<p style='color:red;'>❌ ${detail}</p>`;
                }
            } catch (err) {
                document.getElementById("mensaje").innerHTML = `<p style='color:red;'>⚠️ Error de conexión: ${err.message}</p>`;
            }
        });
    }
});