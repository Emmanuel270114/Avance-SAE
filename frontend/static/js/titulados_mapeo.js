const selectPrograma = document.getElementById('programa');
const selectModalidad = document.getElementById('modalidad');
const selectBoleta = document.getElementById('filtro-boleta');
const selectTipoTitulacion = document.getElementById('filtro-generacion');
const selectTurno = document.getElementById('filtro-turno');


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
});


selectModalidad.addEventListener('change', function() {
    resetSelect(selectBoleta, '-- Seleccione Boleta --');
    resetSelect(selectTipoTitulacion, '-- Seleccione Tipo de Titulación --');
    resetSelect(selectTurno, '-- Seleccione Turno --');

    if (!this.value) return;
   
    llenarSelect(selectBoleta, boletas);
    selectBoleta.disabled = false;
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