// JavaScript para modal - Lógica de modales de confirmación

document.addEventListener('DOMContentLoaded', function() {
    // Variable global para el usuario en edición
    let idUsuarioEdit = null;
    
    // Elementos del modal
    const btnConfirmar = document.getElementById('btn-modal-confirmar');
    const btnCancelar = document.getElementById('btn-modal-cancelar');
    const modal = document.getElementById('modal-confirmar');
    
    // Funciones para mostrar/ocultar modal
    function mostrarModal() {
        if (modal) {
            modal.classList.add('show');
        } else {
            console.error('Modal no encontrado');
        }
    }

    function ocultarModal() {
        if (modal) {
            modal.classList.remove('show');
        } else {
            console.error('Modal no encontrado para ocultar');
        }
    }

    // Eliminar (baja lógica) usuario seleccionado
    const btnEliminar = document.getElementById('btn-eliminar');
    if (btnEliminar) {
        btnEliminar.addEventListener('click', function() {
            if (!idUsuarioEdit) return;
            mostrarModal();
        });
    }

    // Confirmar eliminación en el modal
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', async function() {
            ocultarModal();
            
            if (!idUsuarioEdit) return;
            try {
                const resp = await fetch(`/usuarios/eliminar/${idUsuarioEdit}`, { method: 'POST' });
                const result = await resp.json();
                if (resp.ok) {
                    document.getElementById('mensaje').innerHTML = `<p style='color:green;'>✅ ${result.mensaje}</p>`;
                    setTimeout(() => { location.reload(); }, 1000);
                } else {
                    document.getElementById('mensaje').innerHTML = `<p style='color:red;'>❌ ${result.mensaje || 'Error eliminando'}</p>`;
                }
            } catch(err) {
                document.getElementById('mensaje').innerHTML = `<p style='color:red;'>⚠️ Error de conexión: ${err}</p>`;
            }
        });
    }

    // Cancelar eliminación en el modal
    if (btnCancelar) {
        btnCancelar.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            ocultarModal();
        });
    }

    // Cerrar modal al hacer clic fuera de él
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                ocultarModal();
            }
        });
    }
    
    // Exponer función para establecer el ID del usuario a eliminar
    window.setIdUsuarioEdit = function(id) {
        idUsuarioEdit = id;
    };
});