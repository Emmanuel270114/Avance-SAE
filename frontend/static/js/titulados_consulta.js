
let filasEgresados = [];

function seleccionarTodasEdades(seleccionar) {
    const checkboxes = document.querySelectorAll('.checkbox-edad');
    checkboxes.forEach(cb => cb.checked = seleccionar);
    actualizarContadorEdades();
}

function actualizarContadorEdades() {
    const checkboxes = document.querySelectorAll('.checkbox-edad:checked');
    const count = checkboxes.length;
    const countElement = document.getElementById('edades-seleccionadas-count');
    if (countElement) {
        countElement.textContent = `${count} edad${count !== 1 ? 'es' : ''} seleccionada${count !== 1 ? 's' : ''}`;
        countElement.style.color = count > 0 ? '#28a745' : '#666';
        countElement.style.fontWeight = count > 0 ? '600' : 'normal';
    }
}


function agregarFilasEgresados() {
    // Obtener valores de los filtros
    const programa = document.getElementById('programa');
    const modalidad = document.getElementById('modalidad');
    const turnoSelect = document.getElementById('filtro-turno');
    const boleta = document.getElementById('filtro-boleta');
    const generacion = document.getElementById('filtro-generacion');
    
    // Validar que todos los campos estén llenos
    if (!programa || !programa.value) {
        alert('⚠️ Por favor seleccione un Programa');
        return;
    }
    
    if (!modalidad || !modalidad.value) {
        alert('⚠️ Por favor seleccione una Modalidad');
        return;
    }
    
    if (!turnoSelect || !turnoSelect.value) {
        alert('⚠️ Por favor seleccione un Turno');
        return;
    }
    
    if (!boleta || !boleta.value) {
        alert('⚠️ Por favor seleccione una Boleta');
        return;
    }
    
    if (!generacion || !generacion.value) {
        alert('⚠️ Por favor seleccione una Generación');
        return;
    }
    
    // Obtener edades seleccionadas
    const checkboxesSeleccionados = document.querySelectorAll('.checkbox-edad:checked');
    
    if (checkboxesSeleccionados.length === 0) {
        alert('⚠️ Por favor seleccione al menos una edad');
        return;
    }
    
    // Obtener el turno seleccionado del selector
    const turnoId = turnoSelect.value;
    const turnoNombre = turnoSelect.options[turnoSelect.selectedIndex].text;
    
    let filasAgregadas = 0;
    let filasDuplicadas = 0;
    
    // Crear una fila por cada edad seleccionada
    checkboxesSeleccionados.forEach(checkbox => {
        const edadValor = checkbox.value;
        const edadNombre = checkbox.dataset.nombre;
        
        // Verificar si ya existe una fila con la misma combinación
        const existe = filasEgresados.some(fila => 
            fila.programa === programa.value &&
            fila.modalidad === modalidad.value &&
            fila.turno === turnoId &&
            fila.boleta === boleta.value &&
            fila.generacion === generacion.value &&
            fila.edad === edadValor
        );
        
        if (existe) {
            filasDuplicadas++;
            console.warn(`⚠️ Ya existe una fila para edad: ${edadNombre}`);
            return; // Skip this edad
        }
        
        // Crear objeto de fila
        const fila = {
            id: Date.now() + Math.random(), // ID único
            programa: programa.value,
            programaNombre: programa.options[programa.selectedIndex].text,
            modalidad: modalidad.value,
            modalidadNombre: modalidad.options[modalidad.selectedIndex].text,
            turno: turnoId,
            turnoNombre: turnoNombre,
            boleta: boleta.value,
            boletaNombre: boleta.options[boleta.selectedIndex].text,
            generacion: generacion.value,
            generacionNombre: generacion.options[generacion.selectedIndex].text,
            edad: edadValor,
            edadNombre: edadNombre,
            hombres: '',
            mujeres: ''
        };
        
        // Agregar al almacén
        filasEgresados.push(fila);
        

        filasAgregadas++;
        
        console.log('✅ Fila agregada:', fila);
    });

    filasEgresados.sort((a, b) => {

        if (a.programa !== b.programa)
            return a.programaNombre.localeCompare(b.programaNombre);
        
        if (a.modalidad !== b.modalidad)
            return a.modalidadNombre.localeCompare(b.modalidadNombre);
        
        if (a.turno !== b.turno)
            return a.turnoNombre.localeCompare(b.turnoNombre);
        
        if (a.boleta !== b.boleta)
            return String(b.boleta).localeCompare(String(a.boleta));
    
        if (a.generacion !== b.generacion)
            return a.generacion.localeCompare(b.generacion);
    
        
        return obtenerValorOrdenEdad(a.edad) - obtenerValorOrdenEdad(b.edad);
    });
 
    // Renderizar tabla
    renderizarTablaEgresados();
    
    // Mostrar mensaje de resultado
    let mensaje = `✅ ${filasAgregadas} fila${filasAgregadas !== 1 ? 's' : ''} agregada${filasAgregadas !== 1 ? 's' : ''}`;
    if (filasDuplicadas > 0) {
        mensaje += `\n⚠️ ${filasDuplicadas} edad${filasDuplicadas !== 1 ? 'es' : ''} ya existía${filasDuplicadas !== 1 ? 'n' : ''} y no se agregó${filasDuplicadas !== 1 ? 'aron' : ''}`;
    }
    alert(mensaje);
    
    console.log(`📊 Resumen: ${filasAgregadas} agregadas, ${filasDuplicadas} duplicadas`);
}

function renderizarTablaEgresados() {
    const tbody = document.getElementById('egresados-tbody');
    
    if (filasEgresados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 15px;">📚</div>
                    <p style="font-size: 16px; margin: 0;">No hay registros agregados. Use los filtros arriba para agregar filas.</p>
                </td>
            </tr>
        `;
        return;
    }
    console.log('Total de filas a renderizar:', filasEgresados.length);
    //filasEgresados.sort
    tbody.innerHTML = '';
    filasEgresados.forEach((fila, index) => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #dee2e6';
        tr.style.transition = 'background-color 0.2s';
        tr.innerHTML = `
            <td style="padding: 12px; text-align: center;">${fila.boletaNombre}</td>
            <td style="padding: 12px; text-align: center;">${fila.generacionNombre}</td>
            <td style="padding: 12px; text-align: center; font-weight: 600;">${fila.edadNombre}</td>
            <td style="padding: 12px; text-align: center;">
                <div style="display:inline-flex; align-items:center; gap:3px; padding:2px 4px; background:#e3f2fd; border-radius:4px; border:1px solid #90caf9; line-height:1;">
                    <div style="font-weight:700;color:#1976d2;font-size:11px;min-width:14px;text-align:center;">H</div>
                    <input type="number" 
                           min="0" 
                           value="${fila.hombres}" 
                           onchange="actualizarValorFila(${fila.id}, 'hombres', this.value)"
                           style="width:42px;padding:2px 3px;border:2px solid #2196f3;border-radius:3px;background:#fff;color:#1976d2;font-weight:600;text-align:center;font-size:11px;line-height:1.1;"
                           placeholder="">
                </div>
            </td>
            <td style="padding: 12px; text-align: center;">
                <div style="display:inline-flex; align-items:center; gap:3px; padding:2px 4px; background:#fce4ec; border-radius:4px; border:1px solid #f48fb1; line-height:1;">
                    <div style="font-weight:700;color:#c2185b;font-size:11px;min-width:14px;text-align:center;">M</div>
                    <input type="number" 
                           min="0" 
                           value="${fila.mujeres}" 
                           onchange="actualizarValorFila(${fila.id}, 'mujeres', this.value)"
                           style="width:42px;padding:2px 3px;border:2px solid #e91e63;border-radius:3px;background:#fff;color:#c2185b;font-weight:600;text-align:center;font-size:11px;line-height:1.1;"
                           placeholder="">
                </div>
            </td>
            <td style="padding: 12px; text-align: center;">
                <button type="button" 
                        onclick="eliminarFilaEgresado(${fila.id})" 
                        style="padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;"
                        title="Eliminar fila">
                    🗑️
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    console.log(`Tabla renderizada con ${filasEgresados.length} filas`);
    
   
    actualizarInformeEgresados();
}

function limpiarTabla() {
    if (filasEgresados.length === 0) {
        alert('ℹ️ No hay registros para limpiar');
        return;
    }
    
    if (confirm(`¿Está seguro de eliminar los ${filasEgresados.length} registros?`)) {
        filasEgresados = [];
        renderizarTablaEgresados();
        console.log('Tabla limpiada completamente');
    }
}

function eliminarFilaEgresado(id) {
    if (confirm('¿Está seguro de eliminar este registro?')) {
        filasEgresados = filasEgresados.filter(f => f.id !== id);
        renderizarTablaEgresados();
        console.log(`🗑️ Fila eliminada: ${id}`);
    }
}

