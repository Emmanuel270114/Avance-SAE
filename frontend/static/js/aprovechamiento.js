// ==========================================
// 1. Variables Globales y Estado
// ==========================================
let semestreActual = 0; // Se define dinámicamente según los datos
let maxSemestres = 0;
let turnosEnPantalla = [];
let cambiosGlobales = {}; // Memoria de cambios pendientes
let scrollPendiente = null; // Variable para restaurar la posición de la pantalla

// ==========================================
// 2. Funciones de Utilidad
// ==========================================
function normalizarSemestre(semestre) {
    if (typeof semestre === "number") return semestre;
    const mapa = {
        "primer": 1, "primero": 1, "segundo": 2, "tercer": 3, "tercero": 3,
        "cuarto": 4, "quinto": 5, "sexto": 6, "septimo": 7, "séptimo": 7,
        "octavo": 8, "noveno": 9, "decimo": 10, "décimo": 10
    };
    const texto = String(semestre).toLowerCase().trim();
    // Si es número en string ("3"), lo convierte. Si es texto ("tercero"), usa el mapa.
    return mapa[texto] ?? parseInt(texto, 10);
}

function semestreNumeroATexto(num) {
    const mapaInverso = {
        1: "Primero", 2: "Segundo", 3: "Tercero", 4: "Cuarto",
        5: "Quinto", 6: "Sexto", 7: "Septimo", 8: "Octavo",
        9: "Noveno", 10: "Decimo"
    };
    return mapaInverso[num] || num.toString();
}

function obtenerColorSemaforo(sem, programa, modalidad) {
    if (!window.aprovechamientos) return "#d32f2f";

    const registros = window.aprovechamientos.filter(r => {
        const rProg = String(r.Nombre_Programa || "").trim().toUpperCase();
        const rMod = String(r.Modalidad || "").trim().toUpperCase();
        const rSem = normalizarSemestre(r.Semestre || r.semestre);
        return rProg === String(programa).trim().toUpperCase() &&
            rMod === String(modalidad).trim().toUpperCase() &&
            rSem === Number(sem);
    });

    if (registros.length === 0) return "#d32f2f";

    const idSemaforo = registros[0].Id_Semaforo ?? registros[0].id_semaforo;

    if (idSemaforo === 3) return "#2e7d32"; // Verde
    if (idSemaforo === 2) return "#f57c00"; // Naranja
    return "#d32f2f"; // Rojo
}

// ==========================================
// 3. Renderizado de Pestañas (Lógica Flexible)
// ==========================================
window.cargarSemestresTabs = function (prog, mod, semForzado = null) {
    const semestresTabs = document.getElementById("semestres-tabs");
    const semestreNumSpan = document.getElementById("semestre-num");

    if (!semestresTabs) return;
    semestresTabs.innerHTML = "";

    if (!window.aprovechamientos) return;

    // Obtenemos solo los semestres que existen para este programa
    const semestresUnicos = [...new Set(window.aprovechamientos
        .filter(item => item.Nombre_Programa === prog && item.Modalidad === mod)
        .map(item => normalizarSemestre(item.Semestre))
        .filter(s => !isNaN(s) && s > 0))]
        .sort((a, b) => a - b); // Ordenar numéricamente (ej: 3, 4, 5...)

    if (semestresUnicos.length === 0) {
        const tbody = document.getElementById("tabla-body") || document.getElementById("aprovechamiento-tbody");
        if (tbody) tbody.innerHTML = "";
        return;
    }

    maxSemestres = semestresUnicos[semestresUnicos.length - 1] || 0;

    // LÓGICA DE SELECCIÓN DE SEMESTRE:
    // 1. Si hay uno forzado (guardado), úsalo.
    // 2. Si no, usa el PRIMERO de la lista disponible (aunque sea el 3 o el 5).
    if (semForzado !== null && semestresUnicos.includes(Number(semForzado))) {
        semestreActual = Number(semForzado);
    } else {
        semestreActual = semestresUnicos[0]; // El menor semestre disponible
    }

    if (semestreNumSpan) semestreNumSpan.textContent = semestreActual;

    semestresUnicos.forEach((sem) => {
        const tab = document.createElement("button");
        tab.className = "semestre-tab";
        tab.textContent = `Semestre ${sem}`;
        tab.dataset.semestre = sem;

        const colorBase = obtenerColorSemaforo(sem, prog, mod);

        // Estilos del Tab
        tab.style.padding = "10px 20px";
        tab.style.marginRight = "5px";
        tab.style.border = "none";
        tab.style.cursor = "pointer";
        tab.style.color = "white";
        tab.style.borderRadius = "5px 5px 0 0";
        tab.style.backgroundColor = colorBase;
        tab.style.opacity = "0.7";
        tab.style.fontWeight = "bold";
        tab.style.transition = "all 0.2s ease";

        if (sem === semestreActual) {
            tab.style.opacity = "1";
            tab.style.borderBottom = "4px solid #fff";
            tab.style.transform = "translateY(-2px)";
            tab.style.boxShadow = "0 -2px 5px rgba(0,0,0,0.1)";
        }

        tab.onclick = function () {
            semestreActual = Number(sem);
            if (semestreNumSpan) semestreNumSpan.textContent = semestreActual;
            window.cargarSemestresTabs(prog, mod, semestreActual);
            // La carga de la tabla se hace al final de esta función
        };
        semestresTabs.appendChild(tab);
    });

    // Cargar la tabla del semestre seleccionado
    window.cargarTablaAprovechamiento(prog, mod, semestreActual);
};

// ==========================================
// 4. Renderizado de la Tabla Unificada
// ==========================================
window.cargarTablaAprovechamiento = function (programa, modalidad, semestre) {
    const thead = document.getElementById("tabla-header");
    const tbody = document.getElementById("tabla-body") || document.getElementById("aprovechamiento-tbody");

    if (!tbody) return;
    tbody.innerHTML = "";
    if (thead) thead.innerHTML = "";

    const prog = String(programa).trim().toUpperCase();
    const mod = String(modalidad).trim().toUpperCase();
    const sem = Number(semestre);

    // A. DETECTAR BLOQUEO
    let esSemestreBloqueado = false;
    if (window.aprovechamientos) {
        const registroRef = window.aprovechamientos.find(r => {
            const rProg = String(r.Nombre_Programa || "").trim().toUpperCase();
            const rMod = String(r.Modalidad || "").trim().toUpperCase();
            const rSem = normalizarSemestre(r.Semestre || r.semestre);
            return rProg === prog && rMod === mod && rSem === sem;
        });
        if (registroRef) {
            const idSem = registroRef.Id_Semaforo ?? registroRef.id_semaforo;
            if (idSem === 3) esSemestreBloqueado = true;
        }
    }

    const btnGuardar = document.getElementById('btn-guardar-matricula');
    const btnValidar = document.getElementById('btn-validar-matricula');

    if (btnGuardar) {
        btnGuardar.disabled = esSemestreBloqueado;
        btnGuardar.style.display = esSemestreBloqueado ? "none" : "inline-block";
        btnGuardar.innerHTML = esSemestreBloqueado ? '<i class="fas fa-lock"></i> Finalizado' : '💾 Guardar Todo';
        btnGuardar.className = esSemestreBloqueado ? "btn btn-secondary" : "btn btn-primary";
    }
    if (btnValidar) {
        btnValidar.disabled = esSemestreBloqueado;
        btnValidar.innerHTML = esSemestreBloqueado ? '<i class="fas fa-check-circle"></i>✅ Semestre Validado' : '✅ Validar Semestre';

        if (esSemestreBloqueado) {
            btnValidar.classList.remove("btn-primary", "btn-outline-success");
            btnValidar.classList.add("btn-success");
        } else {
            btnValidar.classList.remove("btn-success", "btn-secondary");
            btnValidar.classList.add("btn-primary"); // Clase original
        }
    }

    // B. DETECTAR TURNOS
    const setTurnos = new Set();
    const fuentes = [window.inscritos, window.reincorporados, window.aprovechamientos];
    fuentes.forEach(fuente => {
        if (!fuente) return;
        fuente.forEach(r => {
            const rProg = String(r.Nombre_Programa || r.nombre_programa || "").trim().toUpperCase();
            const rMod = String(r.Modalidad || r.modalidad || "").trim().toUpperCase(); // <-- MODIFICACIÓN AQUI
            const rSem = normalizarSemestre(r.Semestre || r.semestre);
            if (rProg === prog && rMod === mod && rSem === sem) { // <-- MODIFICACIÓN AQUI
                const t = r.Turno || r.turno;
                if (t && t !== "NULL") setTurnos.add(String(t).trim());
            }
        });
    });

    let turnos = Array.from(setTurnos);
    const orden = { "MATUTINO": 1, "VESPERTINO": 2, "MIXTO": 3, "COMPLETO": 4 };
    turnos.sort((a, b) => (orden[a.toUpperCase()] || 99) - (orden[b.toUpperCase()] || 99));
    if (turnos.length === 0) turnos = ["Matutino"];
    window.turnosActualesPantalla = turnos;

    // C. HEADER
    if (thead) {
        let row1 = `<tr><th rowspan="2" style="vertical-align:middle; text-align:center; background:#f8f9fa; color:black; min-width:180px; white-space:nowrap; border:1px solid #dee2e6;">Situación Academica</th>`;
        let row2 = `<tr>`;
        turnos.forEach(t => {
            // Agregamos 'color: black;' y 'white-space: nowrap;' a los turnos
            row1 += `<th colspan="2" style="text-align:center; background:#e9ecef; color:black; font-weight:bold; white-space:nowrap; border:1px solid #dee2e6;">${t}</th>`;
            row2 += `<th style="text-align:center; font-size:12px; background:#e3f2fd; color:#0d47a1; border:1px solid #dee2e6; min-width:70px;">Hombre</th><th style="text-align:center; font-size:12px; background:#fce4ec; color:#880e4f; border:1px solid #dee2e6; min-width:70px;">Mujer</th>`;
        });
        row1 += `</tr>`; row2 += `</tr>`;
        thead.innerHTML = row1 + row2;
    }

    // D. DATOS
    function mapearDatos(fuente) {
        const mapa = {}; if (!fuente) return mapa;
        fuente.forEach(r => {
            const rProg = String(r.Nombre_Programa || r.nombre_programa || "").trim().toUpperCase();
            const rMod = String(r.Modalidad || r.modalidad || "").trim().toUpperCase(); // <-- MODIFICACIÓN AQUI
            const rSem = normalizarSemestre(r.Semestre || r.semestre);
            if (rProg === prog && rMod === mod && rSem === sem) { // <-- MODIFICACIÓN AQUI
                const t = String(r.Turno || r.turno || "Sin Turno").trim();
                const s = String(r.Sexo || r.sexo || "").toUpperCase().trim();
                const val = parseInt(r.Alumnos || r.alumnos || r.Matricula || r.matricula || 0);
                if (!mapa[t]) mapa[t] = { H: 0, M: 0 };
                if (s.startsWith("H") || s === "1") mapa[t].H += val; else if (s.startsWith("M") || s === "2") mapa[t].M += val;
            }
        });
        return mapa;
    }

    const datosInscritos = mapearDatos(window.inscritos);
    const datosReincorporados = mapearDatos(window.reincorporados);
    const datosAprovechamiento = {};

    (window.aprovechamientos || []).forEach(r => {
        const rProg = String(r.Nombre_Programa || r.nombre_programa || "").trim().toUpperCase();
        const rMod = String(r.Modalidad || r.modalidad || "").trim().toUpperCase(); // <-- MODIFICACIÓN AQUI
        const rSem = normalizarSemestre(r.Semestre || r.semestre);
        if (rProg === prog && rMod === mod && rSem === sem) { // <-- MODIFICACIÓN AQUI
            const sit = r.Aprovechamiento || r.aprovechamiento || r.Situacion || r.situacion || "Sin especificar";
            const t = String(r.Turno || r.turno || "Sin Turno").trim();
            const s = String(r.Sexo || r.sexo || "").toUpperCase().trim();
            const val = parseInt(r.Alumnos || r.alumnos || 0);
            if (!datosAprovechamiento[sit]) datosAprovechamiento[sit] = {};
            if (!datosAprovechamiento[sit][t]) datosAprovechamiento[sit][t] = { H: 0, M: 0 };
            if (s.startsWith("H")) datosAprovechamiento[sit][t].H += val; else if (s.startsWith("M")) datosAprovechamiento[sit][t].M += val;
        }
    });

    crearFilaInput(tbody, "Inscritos", turnos, datosInscritos, true, "fila-matricula", esSemestreBloqueado);
    crearFilaInput(tbody, "Reincorporados", turnos, datosReincorporados, false, "fila-matricula", esSemestreBloqueado);
    crearFilaTotalizador(tbody, "Total Matrícula", turnos, "total-matricula", "#e8f5e9");

    const trSep = document.createElement("tr");
    trSep.innerHTML = `<td colspan="${1 + (turnos.length * 2)}" style="background:#dee2e6; height:6px; padding:0;"></td>`;
    tbody.appendChild(trSep);

    const situaciones = Object.keys(datosAprovechamiento);
    const listaSit = situaciones.length > 0 ? situaciones : ["Aprobado", "Reprobado", "Desertor"];
    listaSit.forEach(sit => {
        const datosSit = datosAprovechamiento[sit] || {};
        crearFilaInput(tbody, sit, turnos, datosSit, false, "fila-aprovechamiento", esSemestreBloqueado);
    });

    crearFilaTotalizador(tbody, "Total Aprovechamiento", turnos, "total-aprovechamiento", "#fff3e0");
    calcularTablaUnificada();

    // --- MAGIA: RESTAURAR SCROLL SI EXISTE ---
    if (scrollPendiente !== null) {
        setTimeout(() => {
            window.scrollTo({ top: scrollPendiente, behavior: 'auto' });
            scrollPendiente = null;
        }, 100);
    }
};

function crearFilaInput(tbody, titulo, turnos, datosMapa, esSoloLectura, claseFila, esBloqueadoGral) {
    const tr = document.createElement("tr"); tr.className = claseFila;
    let html = `<td style="font-weight:600; padding:10px; border:1px solid #dee2e6; vertical-align:middle;">${titulo}</td>`;

    turnos.forEach(t => {
        const valoresDB = datosMapa[t] || { H: 0, M: 0 };
        const keyH = `${semestreActual}|${titulo}|${t}|Hombre`;
        const keyM = `${semestreActual}|${titulo}|${t}|Mujer`;

        let valH = cambiosGlobales.hasOwnProperty(keyH) ? cambiosGlobales[keyH] : (valoresDB.H !== 0 || esSoloLectura ? valoresDB.H : "");
        let valM = cambiosGlobales.hasOwnProperty(keyM) ? cambiosGlobales[keyM] : (valoresDB.M !== 0 || esSoloLectura ? valoresDB.M : "");

        let attr = ""; let bg = "#fff";
        if (esBloqueadoGral) { attr = "disabled"; bg = "#e9ecef"; }
        else if (esSoloLectura) { attr = "readonly"; bg = "#f8f9fa"; }

        html += `<td style="padding:6px; text-align:center; border:1px solid #dee2e6; background:${bg};"><input type="number" class="form-control form-control-sm" data-tipo="${titulo}" data-turno="${t}" data-sexo="Hombre" value="${valH}" oninput="registrarCambio(this)" ${attr} style="text-align:center; font-weight:350; color:#0d47a1;"></td>`;
        html += `<td style="padding:6px; text-align:center; border:1px solid #dee2e6; background:${bg};"><input type="number" class="form-control form-control-sm" data-tipo="${titulo}" data-turno="${t}" data-sexo="Mujer" value="${valM}" oninput="registrarCambio(this)" ${attr} style="text-align:center; font-weight:350; color:#880e4f;"></td>`;
    });
    tr.innerHTML = html; tbody.appendChild(tr);
}

function crearFilaTotalizador(tbody, titulo, turnos, idBase, colorFondo) {
    const tr = document.createElement("tr"); tr.style.backgroundColor = colorFondo;
    let html = `<td style="text-align:right; padding:10px; font-weight:bold;">${titulo}:</td>`;
    turnos.forEach(t => {
        html += `<td style="text-align:center; font-weight:bold; color:#0d47a1; border:1px solid #dee2e6; vertical-align:middle;"><span id="${idBase}-${t}-Hombre">0</span></td><td style="text-align:center; font-weight:bold; color:#880e4f; border:1px solid #dee2e6; vertical-align:middle;"><span id="${idBase}-${t}-Mujer">0</span></td>`;
    });
    tr.innerHTML = html; tbody.appendChild(tr);
}

// ==========================================
// 5. Cálculos
// ==========================================
window.registrarCambio = function (input) {
    const key = `${semestreActual}|${input.dataset.tipo}|${input.dataset.turno}|${input.dataset.sexo}`;
    cambiosGlobales[key] = input.value === "" ? "" : parseInt(input.value);
    calcularTablaUnificada();
};

window.calcularTablaUnificada = function () {
    const inputsMatricula = document.querySelectorAll('.fila-matricula input');
    const sumaMatricula = {};
    inputsMatricula.forEach(input => {
        const key = `${input.dataset.turno}-${input.dataset.sexo}`;
        sumaMatricula[key] = (sumaMatricula[key] || 0) + (parseInt(input.value) || 0);
    });
    for (const [key, val] of Object.entries(sumaMatricula)) {
        const span = document.getElementById(`total-matricula-${key}`);
        if (span) span.textContent = val;
    }

    const inputsAprov = document.querySelectorAll('.fila-aprovechamiento input');
    const sumaAprov = {};
    inputsAprov.forEach(input => {
        const key = `${input.dataset.turno}-${input.dataset.sexo}`;
        sumaAprov[key] = (sumaAprov[key] || 0) + (parseInt(input.value) || 0);
    });

    if (window.turnosActualesPantalla) {
        window.turnosActualesPantalla.forEach(t => {
            ["Hombre", "Mujer"].forEach(s => {
                const key = `${t}-${s}`;
                const spanA = document.getElementById(`total-aprovechamiento-${key}`);
                if (spanA) {
                    const totalM = sumaMatricula[key] || 0;
                    const totalA = sumaAprov[key] || 0;
                    spanA.textContent = totalA;
                    if (totalM !== totalA) {
                        spanA.style.color = "#dc3545";
                        spanA.innerHTML = `${totalA} <i class="fas fa-exclamation-circle"></i>`;
                    } else {
                        spanA.style.color = "#198754";
                        spanA.innerHTML = `${totalA} <i class="fas fa-check"></i>`;
                    }
                }
            });
        });
    }
};

function hayErroresDeTotales() {
    calcularTablaUnificada();
    return document.body.innerHTML.includes("fa-exclamation-circle");
}

// ==========================================
// 6. HELPER FUNCTIONS
// ==========================================

function prepararDatosParaEnvio(claves) {
    const programaVal = document.getElementById("programa")?.value.trim();
    const modalidadVal = document.getElementById("modalidad")?.value.trim();
    const periodoVal = document.getElementById('periodo-texto')?.textContent.trim() || "";

    let rama = "", sigla = "", nivel = "Superior";
    const fuentes = [window.aprovechamientos, window.inscritos, window.reincorporados];

    for (const fuente of fuentes) {
        if (fuente && fuente.length > 0) {
            const registro = fuente.find(r =>
                String(r.Nombre_Programa || r.nombre_programa).trim().toUpperCase() === String(programaVal).toUpperCase()
            );
            if (registro) {
                rama = registro.Nombre_Rama || registro.nombre_rama || registro.Rama || registro.rama || "";
                sigla = registro.Sigla || registro.sigla || "";
                nivel = registro.Nivel || registro.nivel || "Superior";
                break;
            }
        }
    }

    if (!rama) {
        const el = document.getElementById('rama-texto');
        if (el) rama = el.textContent.trim();
    }

    const datos = [];
    // Usamos un Set para asegurar que solo procesamos una combinación única de semestre|concepto|turno|sexo
    const clavesProcesadas = new Set();

    claves.forEach(key => {
        // --- REGLA 2: Mandar solo el primer registro si el dato ya se procesó ---
        if (clavesProcesadas.has(key)) return;
        clavesProcesadas.add(key);

        const partes = key.split('|');
        const semNum = parseInt(partes[0]);
        const concepto = partes[1];

        // --- REGLA 1: Validar nulos o vacíos y mandarlos a cero ---
        let valor = cambiosGlobales[key];
        if (valor === "" || valor === null || valor === undefined) {
            valor = 0;
        } else {
            valor = parseInt(valor);
        }

        if (concepto === "Inscritos") return;

        datos.push({
            periodo: periodoVal,
            programa: programaVal,
            modalidad: modalidadVal,
            semestre: semestreNumeroATexto(semNum),
            rama: rama,
            Nombre_Rama: rama,
            sigla: sigla,
            nivel: nivel,
            id_semaforo: 2,
            situacion_academica: concepto,
            turno: partes[2],
            sexo: partes[3],
            alumnos: valor
        });
    });

    return datos;
}

function actualizarMemoriaLocalConCambios(datosGuardados) {
    if (!window.aprovechamientos) window.aprovechamientos = [];
    const programaVal = document.getElementById("programa")?.value.trim().toUpperCase();
    const modalidadVal = document.getElementById("modalidad")?.value.trim().toUpperCase();

    datosGuardados.forEach(dato => {
        const semNum = normalizarSemestre(dato.semestre);
        const registroExistente = window.aprovechamientos.find(r => {
            const rProg = String(r.Nombre_Programa || "").trim().toUpperCase();
            const rMod = String(r.Modalidad || "").trim().toUpperCase();
            const rSem = normalizarSemestre(r.Semestre || r.semestre);
            const rSit = r.Aprovechamiento || r.aprovechamiento || r.Situacion || r.situacion;
            const rTurno = r.Turno || r.turno;
            const rSexo = r.Sexo || r.sexo;
            return rProg === programaVal && rMod === modalidadVal && rSem === semNum &&
                rSit === dato.situacion_academica && rTurno === dato.turno &&
                String(rSexo).charAt(0) === String(dato.sexo).charAt(0);
        });

        if (registroExistente) {
            registroExistente.Alumnos = dato.alumnos;
            if (registroExistente.alumnos) registroExistente.alumnos = dato.alumnos;
        } else {
            window.aprovechamientos.push({
                Nombre_Programa: programaVal, Modalidad: modalidadVal, Semestre: dato.semestre,
                Aprovechamiento: dato.situacion_academica, Situacion: dato.situacion_academica,
                Turno: dato.turno, Sexo: dato.sexo, Alumnos: dato.alumnos,
                Id_Semaforo: 2, Nivel: dato.nivel, Rama: dato.rama, Sigla: dato.sigla, Nombre_Rama: dato.Nombre_Rama
            });
        }
    });
}

function guardarEstadoYRecargar() {
    const programaVal = document.getElementById("programa")?.value.trim();
    const modalidadVal = document.getElementById("modalidad")?.value.trim();
    const scrollPos = window.scrollY;

    localStorage.setItem("filtro_aprovechamiento", JSON.stringify({
        programa: programaVal,
        modalidad: modalidadVal,
        semestre: semestreActual,
        scrollPos: scrollPos
    }));

    window.location.reload();
}

// ==========================================
// 7. Acciones (Guardar y Validar)
// ==========================================
window.guardarTablaUnificada = async function () {
    if (hayErroresDeTotales()) {
        const result = await Swal.fire({
            title: '⚠️ Totales no coinciden',
            text: "¿Deseas guardar de todos modos?",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, guardar'
        });
        if (!result.isConfirmed) return;
    }

    const claves = Object.keys(cambiosGlobales);
    if (claves.length === 0) {
        Swal.fire('Información', 'No hay cambios pendientes.', 'info');
        return;
    }

    const datos = prepararDatosParaEnvio(claves);
    if (datos.length === 0) return;

    Swal.fire({ title: 'Guardando...', allowOutsideClick: false, didOpen: () => { Swal.showLoading() } });

    try {
        const res = await fetch('/aprovechamiento/guardar_progreso_aprovechamiento', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(datos)
        });
        if (!res.ok) throw new Error(await res.text());

        const periodoVal = document.getElementById('periodo-texto')?.textContent.trim() || "";
        await fetch('/aprovechamiento/actualizar_aprovechamiento', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ periodo: periodoVal })
        });

        actualizarMemoriaLocalConCambios(datos);
        cambiosGlobales = {};

        await Swal.fire({
            title: '¡Guardado!',
            text: 'Datos actualizados correctamente.',
            icon: 'success',
            timer: 1500,
            showConfirmButton: false
        });

        guardarEstadoYRecargar();

    } catch (e) {
        Swal.fire('Error', e.message, 'error');
    }
};

window.validarCapturaSemestre = async function () {
    // 1. Validar errores
    if (hayErroresDeTotales()) {
        const r = await Swal.fire({
            title: '⚠️ Error en Totales',
            text: "¿Forzar validación con errores?",
            icon: 'error',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            confirmButtonText: 'Sí, forzar'
        });
        if (!r.isConfirmed) return;
    }

    // 2. Datos Clave
    const programaVal = document.getElementById("programa")?.value.trim();
    const modalidadVal = document.getElementById("modalidad")?.value.trim();
    const semestreTexto = semestreNumeroATexto(semestreActual);

    if (!programaVal || !modalidadVal) {
        Swal.fire("Error", "Selecciona Programa y Modalidad", "error");
        return;
    }

    // 3. Confirmación Personalizada
    const confirmResult = await Swal.fire({
        title: `¿Finalizar ${semestreTexto} Semestre?`,
        html: `
            Estás a punto de validar:<br>
            <b>Programa:</b> ${programaVal}<br>
            <b>Modalidad:</b> ${modalidadVal}<br>
            <b>Semestre:</b> <span style="color: #d33; font-weight: bold;">${semestreTexto}</span><br><br>
            El semáforo cambiará a <b>VERDE</b> y la edición se bloqueará.
        `,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#198754',
        confirmButtonText: 'Sí, Finalizar'
    });

    if (!confirmResult.isConfirmed) return;

    Swal.fire({ title: 'Validando...', html: 'Recopilando toda la información...', allowOutsideClick: false, didOpen: () => { Swal.showLoading() } });

    const periodoVal = document.getElementById('periodo-texto')?.textContent.trim() || "";

    // Metadata
    let rama = "", sigla = "", nivel = "Superior";
    const fuentes = [window.aprovechamientos, window.inscritos, window.reincorporados];
    for (const fuente of fuentes) {
        if (fuente && fuente.length > 0) {
            const r = fuente.find(reg =>
                String(reg.Nombre_Programa || reg.nombre_programa).trim().toUpperCase() === programaVal.toUpperCase()
            );
            if (r) {
                rama = r.Nombre_Rama || r.nombre_rama || r.Rama || r.rama || "";
                sigla = r.Sigla || r.sigla || "";
                nivel = r.Nivel || r.nivel || "Superior";
                break;
            }
        }
    }
    if (!rama) { const el = document.getElementById('rama-texto'); if (el) rama = el.textContent.trim(); }

    try {
        // =========================================================================
        // A. RECOPILAR TODA LA TABLA A "TEMPORAL" Y CONVERTIR NULOS A CEROS
        // =========================================================================

        // 1. Obtenemos todos los inputs numéricos que estén en el cuerpo de la tabla
        const todosLosInputs = document.querySelectorAll('#tabla-body input[type="number"]');

        todosLosInputs.forEach(input => {
            let valorActual = input.value.trim();

            // 2. Si es vacío, nulo o no es un número válido, lo forzamos a 0
            if (valorActual === "" || valorActual === null || isNaN(valorActual)) {
                valorActual = 0;
                input.value = 0; // Se actualiza visualmente en la tabla a 0
            } else {
                valorActual = parseInt(valorActual);
            }

            // 3. Generamos la llave y lo metemos en cambiosGlobales para engañar 
            // a la función prepararDatosParaEnvio y que empaquete TODO.
            const key = `${semestreActual}|${input.dataset.tipo}|${input.dataset.turno}|${input.dataset.sexo}`;
            cambiosGlobales[key] = valorActual;
        });

        // 4. Transformamos todo ese barrido de pantalla en nuestro arreglo "temporal"
        const clavesTotales = Object.keys(cambiosGlobales);
        const temporal = prepararDatosParaEnvio(clavesTotales);

        if (temporal.length > 0) {
            // Mandamos a guardar toda la data procesada
            const resG = await fetch('/aprovechamiento/guardar_progreso_aprovechamiento', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(temporal)
            });
            if (!resG.ok) throw new Error("Error guardando los datos completos del semestre.");

            actualizarMemoriaLocalConCambios(temporal);
            cambiosGlobales = {}; // Limpiamos la memoria
        }

        // =========================================================================
        // B. Finalizar
        // =========================================================================
        const payload = {
            programa: programaVal, modalidad: modalidadVal, semestre: semestreTexto,
            periodo: periodoVal, rama: rama, Nombre_Rama: rama, sigla: sigla, nivel: nivel
        };

        const resValidar = await fetch('/aprovechamiento/finalizar_captura_semestre', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const jsonValidar = await resValidar.json();

        if (resValidar.ok) {
            await Swal.fire({
                title: '¡Finalizado!',
                text: 'Semestre validado correctamente.',
                icon: 'success',
                timer: 1500,
                showConfirmButton: false
            });
            guardarEstadoYRecargar();
        } else {
            throw new Error(jsonValidar.detail);
        }
    } catch (e) {
        Swal.fire('Error', e.message, 'error');
    }
};

// ==========================================
// 8. Inicialización (CON PANTALLA DE CARGA Y RESTORE)
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
    const loader = document.getElementById("pantalla-carga");
    const programaSelect = document.getElementById("programa");
    const modalidadSelect = document.getElementById("modalidad");

    const ocultarLoader = () => {
        if (loader) {
            loader.style.opacity = "0";
            setTimeout(() => { loader.style.display = "none"; }, 500);
        }
    };

    if (!window.aprovechamientos) {
        console.warn("⚠️ No hay datos cargados en window.aprovechamientos");
        ocultarLoader();
        return;
    }

    // Funciones de carga
    function cargarProgramas(estadoGuardado = null) {
        programaSelect.innerHTML = "";
        const programasSet = new Set();
        const opciones = [];
        for (let i = 0; i < window.aprovechamientos.length; i++) {
            const item = window.aprovechamientos[i];
            if (item.Nombre_Programa && !programasSet.has(item.Nombre_Programa)) {
                programasSet.add(item.Nombre_Programa);
                const opt = document.createElement("option");
                opt.value = item.Nombre_Programa;
                opt.textContent = item.Nombre_Programa;
                opciones.push(opt);
            }
        }
        programaSelect.append(...opciones);

        if (opciones.length > 0) {
            if (estadoGuardado && estadoGuardado.programa) {
                programaSelect.value = estadoGuardado.programa;
            } else {
                programaSelect.value = opciones[0].value;
            }
            cargarModalidades(programaSelect.value, estadoGuardado);
        }
    }

    function cargarModalidades(prog, estadoGuardado = null) {
        modalidadSelect.innerHTML = "";
        const modalidadesSet = new Set();
        const opciones = [];
        for (let i = 0; i < window.aprovechamientos.length; i++) {
            const item = window.aprovechamientos[i];
            if (item.Nombre_Programa === prog && item.Modalidad && !modalidadesSet.has(item.Modalidad)) {
                modalidadesSet.add(item.Modalidad);
                const opt = document.createElement("option");
                opt.value = item.Modalidad;
                opt.textContent = item.Modalidad;
                opciones.push(opt);
            }
        }
        modalidadSelect.append(...opciones);

        if (opciones.length > 0) {
            if (estadoGuardado && estadoGuardado.modalidad) {
                modalidadSelect.value = estadoGuardado.modalidad;
            } else {
                modalidadSelect.value = opciones[0].value;
            }
            window.cargarSemestresTabs(prog, modalidadSelect.value, estadoGuardado ? estadoGuardado.semestre : null);
        }
    }

    programaSelect.addEventListener("change", function () {
        semestreActual = 0; cambiosGlobales = {};
        cargarModalidades(this.value);
    });

    modalidadSelect.addEventListener("change", function () {
        cambiosGlobales = {};
        window.cargarSemestresTabs(programaSelect.value, this.value);
    });

    // EJECUCIÓN ASÍNCRONA
    setTimeout(() => {
        try {
            const guardado = JSON.parse(localStorage.getItem("filtro_aprovechamiento"));

            if (guardado) {
                localStorage.removeItem("filtro_aprovechamiento");

                if (guardado.scrollPos) {
                    scrollPendiente = parseInt(guardado.scrollPos);
                }
                cargarProgramas(guardado);
            } else {
                cargarProgramas();
            }
        } catch (e) {
            console.error("Error en carga inicial:", e);
        } finally {
            ocultarLoader();
        }
    }, 100);
});