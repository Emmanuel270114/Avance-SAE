const selectPrograma = document.getElementById('programa');
const selectModalidad = document.getElementById('modalidad');
const selectBoleta = document.getElementById('filtro-boleta');
const selectTipoTitulacion = document.getElementById('filtro-generacion');
const selectTurno = document.getElementById('filtro-turno');
const contenedor = document.getElementById("tabla-edades-seleccion");

function resetSelect(select, placeholder) {
    select.innerHTML = `<option value="">${placeholder}</option>`;
    select.disabled = true;
}

function llenarSelect(select, opciones) {
    opciones.forEach(opcion => {
        const opt = document.createElement('option');
        opt.value = opcion;
        opt.textContent = opcion;
        select.appendChild(opt);
    });
}

selectPrograma.addEventListener('change', function() {
    const programaSeleccionado = this.value;
    
    resetSelect(selectModalidad, '-- Seleccione una Modalidad --');
    resetSelect(selectBoleta, '-- Seleccione Boleta --');
    selectBoleta.disabled = true;
    selectTipoTitulacion.disabled = true;
    selectTurno.disabled = true;
    resetSelect(selectTipoTitulacion, '-- Seleccione Tipo de Titulación --');
    resetSelect(selectTurno, '-- Seleccione Turno --');

    if (!programaSeleccionado) return;

    const modalidades = [...new Set(
        datosFilas
            .filter(f => f.Nombre_Programa === programaSeleccionado)
            .map(f => f.Modalidad)
    )];

    llenarSelect(selectModalidad, modalidades);
    selectModalidad.disabled = false;

    if (typeof actualizarBarraTitulados === 'function') {
        actualizarBarraTitulados();
    }
});


selectModalidad.addEventListener('change', function() {
    resetSelect(selectBoleta, '-- Seleccione Boleta --');
    resetSelect(selectTipoTitulacion, '-- Seleccione Tipo de Titulación --');
    resetSelect(selectTurno, '-- Seleccione Turno --');

    if (!this.value) return;
   
    llenarSelect(selectBoleta, boletas);
    selectBoleta.disabled = false;

    if (typeof actualizarBarraTitulados === 'function') {
        actualizarBarraTitulados();
    }
});

selectBoleta.addEventListener('change', function() {
    //const boletaSeleccionada = this.value;
    
    resetSelect(selectTipoTitulacion, '-- Seleccione Tipo de Titulación --');
    resetSelect(selectTurno, '-- Seleccione Turno --');
    
    if (!this.value) return;
    const tipoTitulacion = [...new Set(datosFilas.map(f => f.Tipo_Titulacion))];
    llenarSelect(selectTipoTitulacion, tipoTitulacion);
    selectTipoTitulacion.disabled = false;
});

selectTipoTitulacion.addEventListener('change', function() {

    resetSelect(selectTurno, '-- Seleccione Turno --');

    if (!this.value) return;
    const turno = [...new Set(datosFilas.map(f => f.Turno))];
       
    llenarSelect(selectTurno, turno);
    selectTurno.disabled = false;
});

function actualizarBarraTitulados() {
    const headers = document.querySelectorAll('.tabla-matricula-container .tabla-header');

    // Obtener solo Programa y Modalidad
    const selPrograma = document.getElementById('programa');
    const selModalidad = document.getElementById('modalidad');

    let nombrePrograma = '';
    let nombreModalidad = '';

    if (selPrograma && selPrograma.value && selPrograma.selectedOptions.length > 0) {
        nombrePrograma = selPrograma.selectedOptions[0].textContent.trim();
    }
    if (selModalidad && selModalidad.value && selModalidad.selectedOptions.length > 0) {
        nombreModalidad = selModalidad.selectedOptions[0].textContent.trim();
    }

    headers.forEach(header => {
    
        let contenido = '';
        
        if (nombrePrograma) {
            contenido += `<span class="header-programa">${nombrePrograma}</span>`;
        }
        if (nombreModalidad) {
            if (nombrePrograma) contenido += ' • '; // Separador
            contenido += `<span class="header-modalidad">${nombreModalidad}</span>`;
        }

        // Si no hay selecciones, mostrar mensaje por defecto
        if (!contenido) {
            contenido = 'Seleccione Programa y Modalidad';
        }

        // Buscar o crear el elemento h3 para el título
        let h3 = header.querySelector('h3');
        if (!h3) {
            h3 = document.createElement('h3');
            //h3.style.margin = '0';
            //h3.style.fontSize = '18px';
            //h3.style.fontWeight = '600';
            header.insertBefore(h3, header.firstChild); // Insertar antes del botón
        }
        
        h3.innerHTML = contenido;
    });
    
    console.log('Barra actualizada:', nombrePrograma, nombreModalidad);
}

const edades =  [...new Set(datosFilas.map(f => f.Grupo_Edad))];
console.log('Edades únicas antes de ordenar:', edades);
edades.sort ((a, b) => obtenerValorOrdenEdad(a) - obtenerValorOrdenEdad(b));
console.log('Edades únicas después de ordenar:', edades);

edades.forEach(edad => {

    const label = document.createElement("label");
    label.style = `
        display:flex;
        align-items:center;
        gap:8px;
        padding:8px 12px;
        background:#f8f9fa;
        border:1px solid #dee2e6;
        border-radius:6px;
        cursor:pointer;
    `;

    label.innerHTML = `
        <input type="checkbox"
            class="checkbox-edad"
            value="${edad}"
            data-nombre="${edad}"
            style="width:18px;height:18px;cursor:pointer;">
        <span style="font-weight:500;color:#333;font-size:14px;">
            ${edad}
        </span>
    `;

    contenedor.appendChild(label);

});