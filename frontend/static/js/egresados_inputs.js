// ===================================================================
// CONFIGURACIÓN GLOBAL PARA EGRESADOS
// ===================================================================

const EGRESADOS_CONFIG = {
    inputStyles: {
        container: 'display:inline-flex;flex-direction:row;gap:6px;justify-content:center;align-items:center;width:auto;',
        boxMale: 'display:inline-flex;align-items:center;gap:3px;padding:2px 4px;background:#e3f2fd;border-radius:4px;border:1px solid #90caf9;line-height:1;',
        boxFemale: 'display:inline-flex;align-items:center;gap:3px;padding:2px 4px;background:#fce4ec;border-radius:4px;border:1px solid #f48fb1;line-height:1;',
        labelMale: 'font-weight:700;color:#1976d2;font-size:11px;min-width:14px;text-align:center;',
        labelFemale: 'font-weight:700;color:#c2185b;font-size:11px;min-width:14px;text-align:center;',
        inputMale: 'width:60px;padding:4px 6px;border:2px solid #2196f3;border-radius:4px;background:#fff;color:#1976d2;font-weight:600;text-align:center;font-size:13px;',
        inputFemale: 'width:60px;padding:4px 6px;border:2px solid #e91e63;border-radius:4px;background:#fff;color:#c2185b;font-weight:600;text-align:center;font-size:13px;',
        inputFilled: 'border-color: #4caf50; background-color: #e8f5e9;'
    },
    labels: {
        male: 'H',
        female: 'M'
    }
};

// Variables globales
let catalogoBoletas = [];
let catalogoGeneraciones = [];
let catalogoSexos = [];
let catalogoProgramas = [];
let catalogoModalidades = [];
let catalogoTurnos = [];

let turnoActual = 1;
let periodoActual = null;
let unidadAcademicaActual = null;
let programaActual = null;
let modalidadActual = null;

// Estructura de datos de la tabla dinámica
let tablaEgresados = {
    generaciones: [], // Array de {id_generacion, nombre_generacion}
    boletas: [], // Array de {id_boleta, nombre_boleta}
    datos: {} // Objeto con estructura: [id_boleta][id_generacion][id_turno][id_sexo] = cantidad
};

// ===================================================================
// FUNCIONES DE INICIALIZACIÓN
// ===================================================================

document.addEventListener('DOMContentLoaded', async function() {
    await cargarCatalogosIniciales();
    configurarEventListeners();
    
    // Si no es rol superior, cargar datos automáticamente
    const esRolSuperior = typeof window.esRolSuperior !== 'undefined' && window.esRolSuperior;
    if (!esRolSuperior) {
        await inicializarVistaStandard();
    } else {
        await inicializarVistaRolSuperior();
    }
});

async function cargarCatalogosIniciales() {
    try {
        // Cargar catálogos en paralelo
        const [boletasRes, generacionesRes, sexosRes, turnosRes] = await Promise.all([
            fetch('/boletas'),
            fetch('/generaciones'),
            fetch('/sexos'),
            fetch('/api/turnos')
        ]);
        
        catalogoBoletas = await boletasRes.json();
        catalogoGeneraciones = await generacionesRes.json();
        catalogoSexos = await sexosRes.json();
        catalogoTurnos = await turnosRes.json();
        
    } catch (error) {
        console.error('❌ Error al cargar catálogos:', error);
        mostrarMensaje('Error al cargar catálogos iniciales', 'error');
    }
}

function configurarEventListeners() {
    // Listener para cambio de programa
    const selectPrograma = document.getElementById('programa');
    if (selectPrograma) {
        selectPrograma.addEventListener('change', async function() {
            await cargarModalidades(this.value);
        });
    }
    
    // Listener para cambio de modalidad
    const selectModalidad = document.getElementById('modalidad');
    if (selectModalidad) {
        selectModalidad.addEventListener('change', async function() {
            if (this.value) {
                await cargarDatosEgresados();
            }
        });
    }
}

async function inicializarVistaStandard() {
    // Obtener periodo y unidad académica desde los campos ocultos
    periodoActual = document.getElementById('periodo')?.value;
    unidadAcademicaActual = document.getElementById('unidad_academica')?.value;
    
    // Cargar programas
    await cargarProgramasDisponibles();
    
    // Inicializar tabla vacía
    inicializarTablaVacia();
}

async function inicializarVistaRolSuperior() {
    // Configurar listeners para filtros superiores
    const selectNivel = document.getElementById('select-nivel-superior');
    const selectUA = document.getElementById('select-ua-superior');
    const btnConsultar = document.getElementById('btn-consultar-egresados');
    
    if (selectNivel) {
        selectNivel.addEventListener('change', function() {
            cargarUnidadesAcademicasPorNivel(this.value);
        });
    }
    
    if (btnConsultar) {
        btnConsultar.addEventListener('click', consultarEgresadosRolSuperior);
    }
    
    // Habilitar validación de selección
    validarSeleccionRolSuperior();
}

// ===================================================================
// FUNCIONES DE CARGA DE DATOS
// ===================================================================

async function cargarProgramasDisponibles() {
    try {
        const selectPrograma = document.getElementById('programa');
        if (!selectPrograma) return;
        
        // Usar los programas desde el backend (programasData)
        selectPrograma.innerHTML = '<option value="">-- Seleccione un Programa --</option>';
        
        if (typeof programasData !== 'undefined' && programasData.length > 0) {
            programasData.forEach(programa => {
                const option = document.createElement('option');
                option.value = programa.id;
                option.textContent = programa.nombre;
                selectPrograma.appendChild(option);
            });
        } else {
            console.warn('⚠️ No hay programas disponibles en programasData');
        }
        
    } catch (error) {
        console.error('❌ Error al cargar programas:', error);
    }
}

async function cargarModalidades(idPrograma) {
    try {
        const selectModalidad = document.getElementById('modalidad');
        if (!selectModalidad) return;
        
        selectModalidad.innerHTML = '<option value="">-- Seleccione una Modalidad --</option>';
        
        if (!idPrograma) {
            return;
        }
        
        // Usar las modalidades desde el backend (modalidadesData)
        if (typeof modalidadesData !== 'undefined' && modalidadesData.length > 0) {
            modalidadesData.forEach(mod => {
                const option = document.createElement('option');
                option.value = mod.id;
                option.textContent = mod.nombre;
                selectModalidad.appendChild(option);
            });
        } else {
            console.warn('⚠️ No hay modalidades disponibles en modalidadesData');
        }
        
    } catch (error) {
        console.error('❌ Error al cargar modalidades:', error);
        mostrarMensaje('Error al cargar modalidades', 'error');
    }
}

async function cargarDatosEgresados() {
    try {
        const periodo = document.getElementById('periodo')?.value;
        const unidad = document.getElementById('unidad_academica')?.value;
        const programa = document.getElementById('programa')?.value;
        const modalidad = document.getElementById('modalidad')?.value;
        
        if (!periodo || !unidad || !programa || !modalidad) {
            console.warn('⚠️ Faltan datos para consultar egresados');
            return;
        }
        
        const response = await fetch('/egresados/consultar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_periodo: parseInt(periodo),
                id_unidad_academica: parseInt(unidad),
                id_programa: parseInt(programa),
                id_modalidad: parseInt(modalidad)
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            procesarDatosEgresados(result.data);
        } else {
            console.error('❌ Error en respuesta:', result);
            inicializarTablaVacia();
        }
        
    } catch (error) {
        console.error('❌ Error al cargar datos de egresados:', error);
        inicializarTablaVacia();
    }
}

function procesarDatosEgresados(datos) {
    // Resetear estructura
    tablaEgresados = {
        generaciones: [],
        boletas: [],
        datos: {}
    };
    
    // Extraer generaciones y boletas únicas
    const generacionesSet = new Set();
    const boletasSet = new Set();
    
    datos.forEach(registro => {
        if (registro.Id_Generacion) {
            generacionesSet.add(JSON.stringify({
                id: registro.Id_Generacion,
                nombre: registro.Generacion || `Gen ${registro.Id_Generacion}`
            }));
        }
        if (registro.Id_Boleta) {
            boletasSet.add(JSON.stringify({
                id: registro.Id_Boleta,
                nombre: registro.Boleta || `Bol ${registro.Id_Boleta}`
            }));
        }
    });
    
    tablaEgresados.generaciones = Array.from(generacionesSet).map(s => JSON.parse(s));
    tablaEgresados.boletas = Array.from(boletasSet).map(s => JSON.parse(s));
    
    // Ordenar descendentemente
    tablaEgresados.generaciones.sort((a, b) => b.id - a.id);
    tablaEgresados.boletas.sort((a, b) => b.id - a.id);
    
    // Procesar datos
    datos.forEach(registro => {
        const key = `${registro.Id_Boleta}_${registro.Id_Generacion}_${registro.Id_Turno}_${registro.Id_Sexo}`;
        if (!tablaEgresados.datos[registro.Id_Boleta]) {
            tablaEgresados.datos[registro.Id_Boleta] = {};
        }
        if (!tablaEgresados.datos[registro.Id_Boleta][registro.Id_Generacion]) {
            tablaEgresados.datos[registro.Id_Boleta][registro.Id_Generacion] = {};
        }
        if (!tablaEgresados.datos[registro.Id_Boleta][registro.Id_Generacion][registro.Id_Turno]) {
            tablaEgresados.datos[registro.Id_Boleta][registro.Id_Generacion][registro.Id_Turno] = {};
        }
        
        tablaEgresados.datos[registro.Id_Boleta][registro.Id_Generacion][registro.Id_Turno][registro.Id_Sexo] = registro.Egresados || 0;
    });
    
    renderizarTabla();
}

function inicializarTablaVacia() {
    // Inicializar con una generación y una boleta por defecto
    if (catalogoGeneraciones.length > 0 && catalogoBoletas.length > 0) {
        tablaEgresados = {
            generaciones: [{ id: catalogoGeneraciones[0].Id_Generacion, nombre: catalogoGeneraciones[0].Generacion }],
            boletas: [{ id: catalogoBoletas[0].Id_Boleta, nombre: catalogoBoletas[0].Boleta }],
            datos: {}
        };
    } else {
        tablaEgresados = {
            generaciones: [],
            boletas: [],
            datos: {}
        };
    }
    
    renderizarTabla();
}

// ===================================================================
// FUNCIONES DE RENDERIZADO DE TABLA
// ===================================================================

function renderizarTabla() {
    const thead = document.querySelector('#tabla-egresados thead tr');
    const tbody = document.getElementById('egresados-tbody');
    
    if (!thead || !tbody) {
        console.error('❌ No se encontraron elementos de la tabla');
        return;
    }
    
    // Limpiar contenido existente (excepto la primera celda del header)
    thead.innerHTML = '<th style="background-color: #6e0343;">Boleta / Generación</th>';
    tbody.innerHTML = '';
    
    // Renderizar columnas de generación en el header
    tablaEgresados.generaciones.forEach((gen, index) => {
        const th = document.createElement('th');
        th.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px; align-items: center;">
                <select class="selector-generacion" data-gen-index="${index}" onchange="cambiarGeneracion(${index}, this.value)">
                    ${catalogoGeneraciones.map(g => 
                        `<option value="${g.Id_Generacion}" ${g.Id_Generacion === gen.id ? 'selected' : ''}>${g.Generacion}</option>`
                    ).join('')}
                </select>
                <button class="btn-eliminar" onclick="eliminarColumnaGeneracion(${index})" title="Eliminar columna">🗑️</button>
            </div>
        `;
        thead.appendChild(th);
    });
    
    // Renderizar filas de boletas
    tablaEgresados.boletas.forEach((bol, indexBoleta) => {
        const tr = document.createElement('tr');
        
        // Primera celda: selector de boleta
        const tdBoleta = document.createElement('td');
        tdBoleta.className = 'col-boleta';
        tdBoleta.innerHTML = `
            <div style="display: flex; gap: 8px; align-items: center; justify-content: center;">
                <select class="selector-boleta" data-bol-index="${indexBoleta}" onchange="cambiarBoleta(${indexBoleta}, this.value)">
                    ${catalogoBoletas.map(b => 
                        `<option value="${b.Id_Boleta}" ${b.Id_Boleta === bol.id ? 'selected' : ''}>${b.Boleta}</option>`
                    ).join('')}
                </select>
                <button class="btn-eliminar" onclick="eliminarFilaBoleta(${indexBoleta})" title="Eliminar fila">🗑️</button>
            </div>
        `;
        tr.appendChild(tdBoleta);
        
        // Celdas de datos: inputs H y M para cada generación
        tablaEgresados.generaciones.forEach((gen, indexGen) => {
            const td = document.createElement('td');
            td.innerHTML = crearCeldaEgresados(bol.id, gen.id, indexBoleta, indexGen);
            tr.appendChild(td);
        });
        
        tbody.appendChild(tr);
    });
    
}

function crearCeldaEgresados(idBoleta, idGeneracion, indexBoleta, indexGen) {
    const turno = turnoActual;
    
    // Obtener IDs de sexos (H=1, M=2 típicamente)
    const sexoH = catalogoSexos.find(s => s.Sexo.toLowerCase() === 'hombre' || s.Sexo.toLowerCase() === 'masculino');
    const sexoM = catalogoSexos.find(s => s.Sexo.toLowerCase() === 'mujer' || s.Sexo.toLowerCase() === 'femenino');
    
    if (!sexoH || !sexoM) {
        console.error('❌ No se encontraron los sexos en el catálogo');
        return '<span>Error: Sexos no disponibles</span>';
    }
    
    // Obtener valores actuales
    const valorH = obtenerValorEgresado(idBoleta, idGeneracion, turno, sexoH.Id_Sexo);
    const valorM = obtenerValorEgresado(idBoleta, idGeneracion, turno, sexoM.Id_Sexo);
    
    const containerStyle = EGRESADOS_CONFIG.inputStyles.container;
    const boxMale = EGRESADOS_CONFIG.inputStyles.boxMale;
    const boxFemale = EGRESADOS_CONFIG.inputStyles.boxFemale;
    const labelMale = EGRESADOS_CONFIG.inputStyles.labelMale;
    const labelFemale = EGRESADOS_CONFIG.inputStyles.labelFemale;
    const inputMale = EGRESADOS_CONFIG.inputStyles.inputMale;
    const inputFemale = EGRESADOS_CONFIG.inputStyles.inputFemale;
    
    return `
        <div class="egresados-pair-horizontal" style="${containerStyle}">
            <div class="egresados-box egresados-hombre" style="${boxMale}">
                <span class="egresados-label" style="${labelMale}">H</span>
                <input type="number" 
                       class="input-egresado" 
                       data-boleta="${idBoleta}" 
                       data-generacion="${idGeneracion}" 
                       data-turno="${turno}" 
                       data-sexo="${sexoH.Id_Sexo}"
                       data-index-bol="${indexBoleta}"
                       data-index-gen="${indexGen}"
                       value="${valorH || ''}" 
                       min="0" 
                       onchange="actualizarValorEgresado(this)"
                       oninput="this.value = this.value.replace(/[^0-9]/g, '')" 
                       style="${inputMale}" 
                       placeholder="0">
            </div>
            <div class="egresados-box egresados-mujer" style="${boxFemale}">
                <span class="egresados-label" style="${labelFemale}">M</span>
                <input type="number" 
                       class="input-egresado" 
                       data-boleta="${idBoleta}" 
                       data-generacion="${idGeneracion}" 
                       data-turno="${turno}" 
                       data-sexo="${sexoM.Id_Sexo}"
                       data-index-bol="${indexBoleta}"
                       data-index-gen="${indexGen}"
                       value="${valorM || ''}" 
                       min="0" 
                       onchange="actualizarValorEgresado(this)"
                       oninput="this.value = this.value.replace(/[^0-9]/g, '')" 
                       style="${inputFemale}" 
                       placeholder="0">
            </div>
        </div>
    `;
}

function obtenerValorEgresado(idBoleta, idGeneracion, idTurno, idSexo) {
    try {
        return tablaEgresados.datos[idBoleta]?.[idGeneracion]?.[idTurno]?.[idSexo] || 0;
    } catch (error) {
        return 0;
    }
}

function actualizarValorEgresado(input) {
    const idBoleta = parseInt(input.dataset.boleta);
    const idGeneracion = parseInt(input.dataset.generacion);
    const idTurno = parseInt(input.dataset.turno);
    const idSexo = parseInt(input.dataset.sexo);
    const valor = parseInt(input.value) || 0;
    
    // Inicializar estructura si no existe
    if (!tablaEgresados.datos[idBoleta]) {
        tablaEgresados.datos[idBoleta] = {};
    }
    if (!tablaEgresados.datos[idBoleta][idGeneracion]) {
        tablaEgresados.datos[idBoleta][idGeneracion] = {};
    }
    if (!tablaEgresados.datos[idBoleta][idGeneracion][idTurno]) {
        tablaEgresados.datos[idBoleta][idGeneracion][idTurno] = {};
    }
    
    tablaEgresados.datos[idBoleta][idGeneracion][idTurno][idSexo] = valor;
    
}

// ===================================================================
// FUNCIONES DE MANIPULACIÓN DE TABLA
// ===================================================================

function agregarColumnaGeneracion() {
    if (catalogoGeneraciones.length === 0) {
        mostrarMensaje('No hay generaciones disponibles', 'warning');
        return;
    }
    
    // Buscar una generación que no esté ya en uso
    const generacionesEnUso = tablaEgresados.generaciones.map(g => g.id);
    const generacionDisponible = catalogoGeneraciones.find(g => !generacionesEnUso.includes(g.Id_Generacion));
    
    if (!generacionDisponible) {
        mostrarMensaje('No hay más generaciones disponibles para agregar', 'warning');
        return;
    }
    
    tablaEgresados.generaciones.push({
        id: generacionDisponible.Id_Generacion,
        nombre: generacionDisponible.Generacion
    });
    
    renderizarTabla();
    mostrarMensaje('Columna de generación agregada', 'success');
}

function eliminarColumnaGeneracion(index) {
    if (tablaEgresados.generaciones.length <= 1) {
        mostrarMensaje('Debe mantener al menos una generación', 'warning');
        return;
    }
    
    const generacionEliminada = tablaEgresados.generaciones[index];
    
    if (confirm(`¿Está seguro de eliminar la columna de generación "${generacionEliminada.nombre}"?`)) {
        tablaEgresados.generaciones.splice(index, 1);
        
        // Limpiar datos asociados
        Object.keys(tablaEgresados.datos).forEach(idBoleta => {
            if (tablaEgresados.datos[idBoleta][generacionEliminada.id]) {
                delete tablaEgresados.datos[idBoleta][generacionEliminada.id];
            }
        });
        
        renderizarTabla();
        mostrarMensaje('Columna eliminada correctamente', 'success');
    }
}

function agregarFilaBoleta() {
    if (catalogoBoletas.length === 0) {
        mostrarMensaje('No hay boletas disponibles', 'warning');
        return;
    }
    
    // Buscar una boleta que no esté ya en uso
    const boletasEnUso = tablaEgresados.boletas.map(b => b.id);
    const boletaDisponible = catalogoBoletas.find(b => !boletasEnUso.includes(b.Id_Boleta));
    
    if (!boletaDisponible) {
        mostrarMensaje('No hay más boletas disponibles para agregar', 'warning');
        return;
    }
    
    tablaEgresados.boletas.push({
        id: boletaDisponible.Id_Boleta,
        nombre: boletaDisponible.Boleta
    });
    
    renderizarTabla();
    mostrarMensaje('Fila de boleta agregada', 'success');
}

function eliminarFilaBoleta(index) {
    if (tablaEgresados.boletas.length <= 1) {
        mostrarMensaje('Debe mantener al menos una boleta', 'warning');
        return;
    }
    
    const boletaEliminada = tablaEgresados.boletas[index];
    
    if (confirm(`¿Está seguro de eliminar la fila de boleta "${boletaEliminada.nombre}"?`)) {
        tablaEgresados.boletas.splice(index, 1);
        
        // Limpiar datos asociados
        if (tablaEgresados.datos[boletaEliminada.id]) {
            delete tablaEgresados.datos[boletaEliminada.id];
        }
        
        renderizarTabla();
        mostrarMensaje('Fila eliminada correctamente', 'success');
    }
}

function cambiarGeneracion(index, nuevoIdGeneracion) {
    nuevoIdGeneracion = parseInt(nuevoIdGeneracion);
    
    // Verificar que no esté duplicada
    const yaExiste = tablaEgresados.generaciones.some((g, i) => i !== index && g.id === nuevoIdGeneracion);
    if (yaExiste) {
        mostrarMensaje('Esta generación ya está siendo utilizada', 'warning');
        renderizarTabla(); // Revertir el cambio
        return;
    }
    
    const generacionAnterior = tablaEgresados.generaciones[index];
    const nuevaGeneracion = catalogoGeneraciones.find(g => g.Id_Generacion === nuevoIdGeneracion);
    
    if (nuevaGeneracion) {
        tablaEgresados.generaciones[index] = {
            id: nuevaGeneracion.Id_Generacion,
            nombre: nuevaGeneracion.Generacion
        };
        
        // Migrar datos si existen
        Object.keys(tablaEgresados.datos).forEach(idBoleta => {
            if (tablaEgresados.datos[idBoleta][generacionAnterior.id]) {
                tablaEgresados.datos[idBoleta][nuevoIdGeneracion] = tablaEgresados.datos[idBoleta][generacionAnterior.id];
                delete tablaEgresados.datos[idBoleta][generacionAnterior.id];
            }
        });
        
        renderizarTabla();
    }
}

function cambiarBoleta(index, nuevoIdBoleta) {
    nuevoIdBoleta = parseInt(nuevoIdBoleta);
    
    // Verificar que no esté duplicada
    const yaExiste = tablaEgresados.boletas.some((b, i) => i !== index && b.id === nuevoIdBoleta);
    if (yaExiste) {
        mostrarMensaje('Esta boleta ya está siendo utilizada', 'warning');
        renderizarTabla(); // Revertir el cambio
        return;
    }
    
    const boletaAnterior = tablaEgresados.boletas[index];
    const nuevaBoleta = catalogoBoletas.find(b => b.Id_Boleta === nuevoIdBoleta);
    
    if (nuevaBoleta) {
        tablaEgresados.boletas[index] = {
            id: nuevaBoleta.Id_Boleta,
            nombre: nuevaBoleta.Boleta
        };
        
        // Migrar datos si existen
        if (tablaEgresados.datos[boletaAnterior.id]) {
            tablaEgresados.datos[nuevoIdBoleta] = tablaEgresados.datos[boletaAnterior.id];
            delete tablaEgresados.datos[boletaAnterior.id];
        }
        
        renderizarTabla();
    }
}

// ===================================================================
// FUNCIONES DE TURNOS
// ===================================================================

function cambiarTurno(direccion) {
    const nuevoTurno = turnoActual + direccion;
    
    if (nuevoTurno < 1 || nuevoTurno > catalogoTurnos.length) {
        console.warn('⚠️ Turno fuera de rango');
        return;
    }
    
    turnoActual = nuevoTurno;
    
    // Actualizar UI
    const turnoObj = catalogoTurnos.find(t => t.Id_Turno === turnoActual);
    if (turnoObj) {
        document.getElementById('turno-nombre').textContent = turnoObj.Turno;
    }
    
    document.getElementById('turno').value = turnoActual;
    
    // Actualizar botones
    document.getElementById('btn-turno-anterior').disabled = turnoActual === 1;
    document.getElementById('btn-turno-siguiente').disabled = turnoActual === catalogoTurnos.length;
    
    // Re-renderizar tabla con datos del nuevo turno
    renderizarTabla();
    
}

// ===================================================================
// FUNCIONES DE GUARDADO Y VALIDACIÓN
// ===================================================================

async function guardarEgresados() {
    try {
        const periodo = document.getElementById('periodo')?.value;
        const unidad = document.getElementById('unidad_academica')?.value;
        const programa = document.getElementById('programa')?.value;
        const modalidad = document.getElementById('modalidad')?.value;
        
        if (!periodo || !unidad || !programa || !modalidad) {
            mostrarMensaje('Debe seleccionar periodo, unidad académica, programa y modalidad', 'warning');
            return;
        }
        
        // Recopilar todos los registros
        const registros = [];
        
        Object.keys(tablaEgresados.datos).forEach(idBoleta => {
            Object.keys(tablaEgresados.datos[idBoleta]).forEach(idGeneracion => {
                Object.keys(tablaEgresados.datos[idBoleta][idGeneracion]).forEach(idTurno => {
                    Object.keys(tablaEgresados.datos[idBoleta][idGeneracion][idTurno]).forEach(idSexo => {
                        const cantidad = tablaEgresados.datos[idBoleta][idGeneracion][idTurno][idSexo];
                        
                        if (cantidad > 0) {
                            registros.push({
                                id_boleta: parseInt(idBoleta),
                                id_generacion: parseInt(idGeneracion),
                                id_turno: parseInt(idTurno),
                                id_sexo: parseInt(idSexo),
                                cantidad: cantidad
                            });
                        }
                    });
                });
            });
        });
        
        const response = await fetch('/egresados/guardar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_periodo: parseInt(periodo),
                id_unidad_academica: parseInt(unidad),
                id_programa: parseInt(programa),
                id_modalidad: parseInt(modalidad),
                registros: registros
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            mostrarMensaje(`Egresados guardados correctamente (${result.guardados} nuevos, ${result.actualizados} actualizados)`, 'success');
        } else {
            mostrarMensaje('Error al guardar egresados', 'error');
        }
        
    } catch (error) {
        console.error('❌ Error al guardar egresados:', error);
        mostrarMensaje('Error al guardar egresados', 'error');
    }
}

async function validarCapturaEgresados() {
    if (!confirm('¿Está seguro de validar y enviar los datos de egresados? Esta acción los enviará para revisión.')) {
        return;
    }
    
    try {
        // Primero guardar
        await guardarEgresados();
        
        // Luego validar
        const periodo = document.getElementById('periodo')?.value;
        const unidad = document.getElementById('unidad_academica')?.value;
        
        const response = await fetch('/egresados/validar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_periodo: parseInt(periodo),
                id_unidad_academica: parseInt(unidad),
                nota: 'Validado por capturista'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            mostrarMensaje('Egresados validados y enviados correctamente', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
        
    } catch (error) {
        console.error('❌ Error al validar egresados:', error);
        mostrarMensaje('Error al validar egresados', 'error');
    }
}

async function validarEgresados() {
    if (!confirm('¿Está seguro de validar estos datos de egresados?')) {
        return;
    }
    
    try {
        const periodo = document.getElementById('periodo')?.value;
        const unidad = document.getElementById('unidad_academica')?.value;
        
        const response = await fetch('/egresados/validar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_periodo: parseInt(periodo),
                id_unidad_academica: parseInt(unidad),
                nota: 'Validado'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            mostrarMensaje('Egresados validados correctamente', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
        
    } catch (error) {
        console.error('❌ Error al validar:', error);
        mostrarMensaje('Error al validar egresados', 'error');
    }
}

function rechazarEgresados() {
    document.getElementById('panel-rechazo').style.display = 'block';
}

function cerrarPanelRechazo() {
    document.getElementById('panel-rechazo').style.display = 'none';
    document.getElementById('motivo-rechazo').value = '';
}

async function confirmarRechazoEgresados() {
    const motivo = document.getElementById('motivo-rechazo')?.value?.trim();
    
    if (!motivo) {
        mostrarMensaje('Debe proporcionar un motivo de rechazo', 'warning');
        return;
    }
    
    try {
        const periodo = document.getElementById('periodo')?.value;
        const unidad = document.getElementById('unidad_academica')?.value;
        
        const response = await fetch('/egresados/rechazar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_periodo: parseInt(periodo),
                id_unidad_academica: parseInt(unidad),
                motivo: motivo
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            mostrarMensaje('Egresados rechazados correctamente', 'success');
            cerrarPanelRechazo();
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
        
    } catch (error) {
        console.error('❌ Error al rechazar:', error);
        mostrarMensaje('Error al rechazar egresados', 'error');
    }
}

function limpiarFormulario() {
    if (!confirm('¿Está seguro de limpiar todos los datos? Esta acción no se puede deshacer.')) {
        return;
    }
    
    // Limpiar datos
    tablaEgresados.datos = {};
    
    // Re-renderizar
    renderizarTabla();
    
    mostrarMensaje('Formulario limpiado', 'success');
}

// ===================================================================
// FUNCIONES DE NOTIFICACIONES
// ===================================================================

function togglePanelNotificaciones() {
    const panel = document.getElementById('panel-notificaciones');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
}

function mostrarBannerRechazo() {
    const banner = document.getElementById('banner-rechazo');
    if (banner) {
        banner.style.display = 'flex';
        togglePanelNotificaciones();
    }
}

function cerrarBannerRechazo() {
    const banner = document.getElementById('banner-rechazo');
    if (banner) {
        banner.style.display = 'none';
    }
}

// ===================================================================
// FUNCIONES PARA ROLES SUPERIORES
// ===================================================================

function cargarUnidadesAcademicasPorNivel(idNivel) {
    if (!idNivel) {
        const selectUA = document.getElementById('select-ua-superior');
        selectUA.innerHTML = '<option value="">-- Primero seleccione un Nivel --</option>';
        selectUA.disabled = true;
        return;
    }
    
    // Filtrar unidades por nivel (esto debe venir del backend)
    const selectUA = document.getElementById('select-ua-superior');
    selectUA.disabled = false;
    selectUA.innerHTML = '<option value="">-- Seleccione una Unidad Académica --</option>';
    
    // Aquí deberías hacer una llamada al backend para obtener las UAs por nivel
}

function validarSeleccionRolSuperior() {
    const selectPeriodo = document.getElementById('select-periodo-superior');
    const selectNivel = document.getElementById('select-nivel-superior');
    const selectUA = document.getElementById('select-ua-superior');
    const btnConsultar = document.getElementById('btn-consultar-egresados');
    
    function verificar() {
        const valido = selectPeriodo?.value && selectNivel?.value && selectUA?.value;
        if (btnConsultar) {
            btnConsultar.disabled = !valido;
        }
    }
    
    [selectPeriodo, selectNivel, selectUA].forEach(select => {
        if (select) {
            select.addEventListener('change', verificar);
        }
    });
}

async function consultarEgresadosRolSuperior() {
    const periodo = document.getElementById('select-periodo-superior')?.value;
    const nivel = document.getElementById('select-nivel-superior')?.value;
    const unidad = document.getElementById('select-ua-superior')?.value;
    
    if (!periodo || !nivel || !unidad) {
        mostrarMensaje('Seleccione todos los filtros', 'warning');
        return;
    }
    
    // Mostrar spinner
    document.getElementById('mensaje-carga-superior').style.display = 'block';
    
    // Aquí deberías cargar los datos de egresados para esa UA
    // Similar a cargarDatosEgresados pero con los parámetros de rol superior
    
    // Ocultar spinner y mostrar contenedor
    setTimeout(() => {
        document.getElementById('mensaje-carga-superior').style.display = 'none';
        document.getElementById('contenedor-egresados-principal').style.display = 'block';
    }, 1000);
}

// ===================================================================
// UTILIDADES
// ===================================================================

function mostrarMensaje(mensaje, tipo = 'info') {
    // Aquí puedes implementar un sistema de notificaciones más sofisticado
    const colores = {
        success: '#28a745',
        error: '#dc3545',
        warning: '#ffc107',
        info: '#17a2b8'
    };
    
    const color = colores[tipo] || colores.info;
    
    // Crear notificación temporal
    const notif = document.createElement('div');
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${color};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 10000;
        font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
    notif.textContent = mensaje;
    
    document.body.appendChild(notif);
    
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

