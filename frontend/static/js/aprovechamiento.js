// ==========================================
// 1. Variables Globales y Estado
// ==========================================
let turnoActual = "Matutino";
let semestreActual = 1;
let maxSemestres = 0;

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

// ==========================================
// 3. Sincronización Tabla Superior (ESTRICTA POR TURNO)
// ==========================================

function actualizarCifrasMatriculaSuperior() {
    console.log(`--- ACTUALIZANDO CIFRAS SUPERIORES (${turnoActual}) ---`);

    if (!window.inscritos || !window.reincorporados) return;

    const progBuscado = String(document.getElementById("programa").value).trim().toUpperCase();
    const semBuscado = semestreActual;
    const turnoBuscado = String(turnoActual).trim().toUpperCase(); // EJ: "MATUTINO"

    // 1. Filtrar Reincorporados (ESTRICTO: Debe coincidir el turno)
    const rei = window.reincorporados.filter(r => {
        const keys = Object.keys(r);
        const keyProg = keys.find(k => k.toLowerCase().includes('programa'));
        const keySem = keys.find(k => k.toLowerCase().includes('semestre'));
        const keyTurno = keys.find(k => k.toLowerCase().includes('turno')); // Buscamos columna turno

        const rProg = keyProg ? String(r[keyProg] || "").trim().toUpperCase() : "";
        const rSem = keySem ? normalizarSemestre(r[keySem]) : 0;
        const rTurno = keyTurno ? String(r[keyTurno] || "").trim().toUpperCase() : "";

        // AHORA SÍ FILTRAMOS POR TURNO
        // Si en la BD el turno viene vacío, NO lo mostramos en el turno específico
        // para obligar a capturar uno nuevo por turno correcto.
        return rProg === progBuscado &&
            rSem === semBuscado &&
            rTurno === turnoBuscado;
    });

    console.log(`✅ Reincorporados para ${turnoBuscado}: ${rei.length}`);

    // 2. Sumar Reincorporados
    let h_rei = 0, m_rei = 0;

    rei.forEach(r => {
        const keys = Object.keys(r);
        const keyCant = keys.find(k => /alumnos|matricula|total|cantidad/i.test(k));
        const keySexo = keys.find(k => /sexo|genero/i.test(k));

        const val = keyCant ? parseInt(r[keyCant] || 0) : 0;
        const sexoVal = keySexo ? String(r[keySexo] || "").toUpperCase().trim() : "";

        if (sexoVal.startsWith("H") || sexoVal.includes("MASC") || sexoVal == "1") {
            h_rei += val;
        } else if (sexoVal.startsWith("M") || sexoVal.includes("FEM") || sexoVal == "2") {
            m_rei += val;
        }
    });

    // 3. Filtrar Inscritos (También estricto por turno para que cuadre la matrícula)
    const ins = window.inscritos.filter(r => {
        const keys = Object.keys(r);
        const keyProg = keys.find(k => k.toLowerCase().includes('programa'));
        const keySem = keys.find(k => k.toLowerCase().includes('semestre'));
        const keyTurno = keys.find(k => k.toLowerCase().includes('turno'));

        const rProg = keyProg ? String(r[keyProg] || "").trim().toUpperCase() : "";
        const rSem = keySem ? normalizarSemestre(r[keySem]) : 0;
        const rTurno = keyTurno ? String(r[keyTurno] || "").trim().toUpperCase() : "";

        // Si la matrícula en BD no tiene turno, intentamos mostrarla en ambos (opcional)
        // Pero lo ideal es estricto:
        return rProg === progBuscado &&
            rSem === semBuscado &&
            (rTurno === turnoBuscado || rTurno === ""); // Aceptamos vacío en inscritos por si acaso
    });

    let h_ins = 0, m_ins = 0;
    ins.forEach(r => {
        const keys = Object.keys(r);
        const keyCant = keys.find(k => /alumnos|matricula|total/i.test(k));
        const keySexo = keys.find(k => /sexo|genero/i.test(k));

        const val = keyCant ? parseInt(r[keyCant] || 0) : 0;
        const s = keySexo ? String(r[keySexo] || "").toUpperCase() : "";

        if (s.startsWith("H")) h_ins += val;
        else if (s.startsWith("M")) m_ins += val;
    });

    console.log(`📊 TOTALES (${turnoBuscado}) -> Reinc: H=${h_rei}, M=${m_rei}`);

    // 4. Asignación al DOM
    if (document.getElementById('inscritos-h')) document.getElementById('inscritos-h').value = h_ins;
    if (document.getElementById('inscritos-m')) document.getElementById('inscritos-m').value = m_ins;

    // Limpiamos los inputs de Reincorporados cada vez que cambia el turno/semestre
    // Si hay datos en BD para ESTE turno, se ponen. Si no, se queda en blanco para capturar.
    const inputReH = document.getElementById('reinc-h');
    const inputReM = document.getElementById('reinc-m');

    if (inputReH) inputReH.value = h_rei > 0 ? h_rei : "";
    if (inputReM) inputReM.value = m_rei > 0 ? m_rei : "";

    calcularTotalMatricula();
}

// ==========================================
// 4. Cálculos y Auditoría
// ==========================================
function calcularTotalMatricula() {
    const insH = parseInt(document.getElementById('inscritos-h')?.value) || 0;
    const insM = parseInt(document.getElementById('inscritos-m')?.value) || 0;
    const reH = parseInt(document.getElementById('reinc-h')?.value) || 0;
    const reM = parseInt(document.getElementById('reinc-m')?.value) || 0;

    const totalH = insH + reH;
    const totalM = insM + reM;

    if (document.getElementById('total-h')) document.getElementById('total-h').value = totalH;
    if (document.getElementById('total-m')) document.getElementById('total-m').value = totalM;

    let sumaAprovH = 0;
    let sumaAprovM = 0;

    const filas = document.querySelectorAll('#aprovechamiento-tbody tr:not(.fila-totales)');
    filas.forEach(fila => {
        const inputs = fila.querySelectorAll('input[type="number"]');
        if (inputs.length >= 2) {
            sumaAprovH += parseInt(inputs[0].value) || 0;
            sumaAprovM += parseInt(inputs[1].value) || 0;
        }
    });

    if (document.getElementById('total_masculino')) document.getElementById('total_masculino').textContent = sumaAprovH;
    if (document.getElementById('total_femenino')) document.getElementById('total_femenino').textContent = sumaAprovM;
    if (document.getElementById('total_general')) document.getElementById('total_general').textContent = sumaAprovH + sumaAprovM;

    const inputTotalH = document.getElementById('total-h');
    const inputTotalM = document.getElementById('total-m');

    if (inputTotalH) inputTotalH.style.color = (totalH === sumaAprovH) ? "#1976d2" : "#d32f2f";
    if (inputTotalM) inputTotalM.style.color = (totalM === sumaAprovM) ? "#c2185b" : "#d32f2f";
}

// ==========================================
// 5. Renderizado Tabla Dinámica (CON FILTRO DE TURNO)
// ==========================================
window.cargarTablaAprovechamiento = function (programa, modalidad, semestre) {
    console.log("--- RENDERIZANDO TABLA ---");
    const tbody = document.getElementById("aprovechamiento-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!window.aprovechamientos) return;

    const turnoBuscado = String(turnoActual).trim().toUpperCase();
    const progBuscado = String(programa).trim().toUpperCase();
    const modBuscada = String(modalidad).trim().toUpperCase();
    const semBuscado = Number(semestre);

    // 1. FILTRO (Aquí SÍ usamos turno porque la tabla de abajo se desglosa por turno)
    const filtrados = window.aprovechamientos.filter(reg => {
        const rProg = String(reg.Nombre_Programa || reg.nombre_programa || "").trim().toUpperCase();
        const rMod = String(reg.Modalidad || reg.modalidad || "").trim().toUpperCase();
        const rSem = normalizarSemestre(reg.Semestre || reg.semestre);
        const rTurno = String(reg.Turno || reg.turno || "").trim().toUpperCase();

        return (
            rProg === progBuscado &&
            rMod === modBuscada &&
            rSem === semBuscado &&
            (rTurno === "" || rTurno === "NULL" || rTurno === turnoBuscado)
        );
    });

    // 2. AGRUPACIÓN
    const agrupado = {};
    filtrados.forEach(reg => {
        const sit = reg.Aprovechamiento || reg.aprovechamiento ||
            reg.Situacion || reg.situacion || "Sin especificar";

        if (!agrupado[sit]) agrupado[sit] = { H: null, M: null };

        const datoSexo = reg.Sexo || reg.sexo || "";
        const sexo = String(datoSexo).toUpperCase().trim();
        const datoValor = reg.Alumnos || reg.alumnos || reg.Matricula || reg.matricula || 0;
        const valor = parseInt(datoValor);

        if (sexo.startsWith("H")) agrupado[sit].H = (agrupado[sit].H || 0) + valor;
        else if (sexo.startsWith("M")) agrupado[sit].M = (agrupado[sit].M || 0) + valor;
    });

    // 3. GENERAR HTML
    const situaciones = Object.keys(agrupado);
    if (situaciones.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="padding:20px; text-align:center; color:#777;">No hay datos para mostrar en este turno.</td></tr>';
    } else {
        situaciones.forEach(situacion => {
            const valores = agrupado[situacion];
            const tr = document.createElement('tr');
            tr.style.borderBottom = "1px solid #eee";
            tr.innerHTML = `
                <td style="padding:15px; text-align:center; font-weight:700; color:#444;">${situacion}</td>
                <td style="text-align:center;">
                    <div style="display:inline-flex; align-items:center; gap:8px; background:#e3f2fd; padding:6px 10px; border-radius:8px; border:1px solid #90caf9;">
                        <span style="color:#1976d2; font-weight:bold;">H</span>
                        <input type="number" oninput="calcularTotalMatricula()" 
                            value="${valores.H !== null ? valores.H : ''}" placeholder="" 
                            style="width:52px; text-align:center; border:2px solid #2196f3; border-radius:4px; font-weight:bold; color:#1565c0;">
                    </div>
                </td>
                <td style="text-align:center;">
                    <div style="display:inline-flex; align-items:center; gap:8px; background:#fce4ec; padding:6px 10px; border-radius:8px; border:1px solid #f48fb1;">
                        <span style="color:#c2185b; font-weight:bold;">M</span>
                        <input type="number" oninput="calcularTotalMatricula()" 
                            value="${valores.M !== null ? valores.M : ''}" placeholder="" 
                            style="width:52px; text-align:center; border:2px solid #e91e63; border-radius:4px; font-weight:bold; color:#ad1457;">
                    </div>
                </td>`;
            tbody.appendChild(tr);
        });
    }

    // 4. TOTALES
    const trTot = document.createElement('tr');
    trTot.className = "fila-totales";
    trTot.innerHTML = `
        <td style="padding:12px;text-align:center;font-weight:700;font-size:16px;background:#6e0343;color:white;">TOTALES</td>
        <td style="padding:12px;text-align:center;" colspan="2">
            <div style="display:flex;justify-content:space-around;align-items:center;flex-wrap:wrap;gap:15px;">
                <div style="flex:1;min-width:120px;">
                    <div style="background:#e3f2fd;padding:8px;border-radius:8px;border:2px solid #2196f3;">
                        <div style="font-size:13px;color:#1976d2;font-weight:600;margin-bottom:4px;">Masculino</div>
                        <div id="total_masculino" style="font-size:24px;color:#1976d2;font-weight:700;">0</div>
                    </div>
                </div>
                <div style="flex:1;min-width:120px;">
                    <div style="background:#fce4ec;padding:8px;border-radius:8px;border:2px solid #e91e63;">
                        <div style="font-size:13px;color:#c2185b;font-weight:600;margin-bottom:4px;">Femenino</div>
                        <div id="total_femenino" style="font-size:24px;color:#c2185b;font-weight:700;">0</div>
                    </div>
                </div>
                <div style="flex:1;min-width:140px;">
                    <div style="background:#e8f5e9;padding:8px;border-radius:8px;border:2px solid #4caf50;">
                        <div style="font-size:13px;color:#2e7d32;font-weight:600;margin-bottom:4px;">TOTAL GENERAL</div>
                        <div id="total_general" style="font-size:26px;color:#2e7d32;font-weight:700;">0</div>
                    </div>
                </div>
            </div>
        </td>`;
    tbody.appendChild(trTot);

    actualizarCifrasMatriculaSuperior();
};

// ==========================================
// 6. Semáforo y Tabs
// ==========================================
function obtenerColorSemaforo(sem, programa, modalidad) {
    if (!window.aprovechamientos) return "#9e9e9e"; // Gris si no hay datos cargados

    // Filtramos los registros para este semestre específico
    const registros = window.aprovechamientos.filter(r => {
        const rProg = String(r.Nombre_Programa || "").trim().toUpperCase();
        const rMod = String(r.Modalidad || "").trim().toUpperCase();
        const rSem = normalizarSemestre(r.Semestre);
        return rProg === String(programa).toUpperCase() &&
            rMod === String(modalidad).toUpperCase() &&
            rSem === Number(sem);
    });

    if (registros.length === 0) return "#f40707ff"; // Rojo: Sin registros

    // Buscamos el ID del semáforo (probando ambas nomenclaturas)
    const idSemaforo = registros[0].Id_Semaforo ?? registros[0].id_semaforo;

    // Lógica de colores según el estándar del sistema
    if (idSemaforo === 3) return "#067733ff"; // Verde: Completo/Validado
    if (idSemaforo === 2) return "#ffaa00ff"; // Amarillo: En proceso/Guardado
    return "#f40707ff"; // Rojo: Inicial/Sin datos
}

function actualizarEstiloTabs() {
    const programa = document.getElementById("programa").value;
    const modalidad = document.getElementById("modalidad").value;

    document.querySelectorAll(".semestre-tab").forEach(tab => {
        const sem = tab.dataset.semestre;
        const colorBase = obtenerColorSemaforo(sem, programa, modalidad);
        const esActivo = Number(sem) === Number(semestreActual);

        // Diseño mejorado de la pestaña
        tab.style.backgroundColor = colorBase;
        tab.style.border = "none";
        tab.style.color = "white";
        tab.style.padding = "12px 24px";
        tab.style.margin = "0 5px";
        tab.style.borderRadius = "8px 8px 0 0";
        tab.style.cursor = "pointer";
        tab.style.transition = "all 0.3s ease";
        tab.style.fontSize = "14px";
        tab.style.fontWeight = esActivo ? "bold" : "normal";
        tab.style.opacity = esActivo ? "1" : "0.7";
        tab.style.boxShadow = esActivo ? "0 -4px 10px rgba(0,0,0,0.2)" : "none";
        tab.style.transform = esActivo ? "translateY(-3px)" : "none";

        // Indicador inferior para el activo
        if (esActivo) {
            tab.style.borderBottom = "4px solid rgba(255,255,255,0.8)";
        } else {
            tab.style.borderBottom = "none";
        }
    });
}

// ==========================================
// 7. Guardado Completo
// ==========================================

async function guardarYActualizarAprovechamiento() {
    console.log("--- INICIANDO PROCESO DE GUARDADO ---");

    // 1. Asegurar cálculos
    calcularTotalMatricula();

    // 2. Validación No Bloqueante
    const matH = parseInt(document.getElementById('total-h').value) || 0;
    const matM = parseInt(document.getElementById('total-m').value) || 0;
    const aprovH = parseInt(document.getElementById('total_masculino').textContent) || 0;
    const aprovM = parseInt(document.getElementById('total_femenino').textContent) || 0;

    if (matH !== aprovH || matM !== aprovM) {
        const seguir = confirm(
            `⚠️ ADVERTENCIA:\n\n` +
            `Matrícula Total (H:${matH}, M:${matM})\n` +
            `Situaciones (H:${aprovH}, M:${aprovM})\n\n` +
            `Los totales no coinciden. ¿Deseas guardar de todas formas?`
        );
        if (!seguir) return;
    }

    const btn = document.getElementById('btn-guardar-matricula');

    // 3. Obtener datos del DOM
    const programaVal = document.getElementById("programa").value.trim();
    const modalidadVal = document.getElementById("modalidad").value.trim();
    const periodoVal = document.getElementById('periodo-texto').textContent.trim();

    // Captura de RAMA
    const ramaElement = document.getElementById('rama-texto');
    const ramaVal = ramaElement ? ramaElement.textContent.trim() : "";

    // Referencia para Nivel y Sigla
    let registroRef = null;
    if (window.aprovechamientos) {
        registroRef = window.aprovechamientos.find(r =>
            String(r.Nombre_Programa).trim() === programaVal
        );
    }

    const datosParaEnviar = [];
    const baseObj = {
        periodo: periodoVal,
        programa: programaVal,
        modalidad: modalidadVal,
        semestre: semestreNumeroATexto(semestreActual),
        turno: turnoActual,
        rama: ramaVal,
        sigla: registroRef ? registroRef.Sigla : "",
        nivel: registroRef ? registroRef.Nivel : "",
        id_semaforo: 2
    };

    // 4. Capturar Reincorporados (Inputs Superiores)
    const reH = document.getElementById('reinc-h');
    const reM = document.getElementById('reinc-m');

    if (reH && reH.value.trim() !== "") {
        datosParaEnviar.push({ ...baseObj, situacion_academica: "Reincorporados", sexo: 'Hombre', alumnos: parseInt(reH.value) });
    }
    if (reM && reM.value.trim() !== "") {
        datosParaEnviar.push({ ...baseObj, situacion_academica: "Reincorporados", sexo: 'Mujer', alumnos: parseInt(reM.value) });
    }

    // 5. Capturar Situaciones (Tabla Inferior)
    const filas = document.querySelectorAll('#aprovechamiento-tbody tr:not(.fila-totales)');
    filas.forEach(fila => {
        const celdaNombre = fila.querySelector('td:first-child');
        const inputs = fila.querySelectorAll('input[type="number"]');

        if (celdaNombre && inputs.length >= 2) {
            const nombreSituacion = celdaNombre.textContent.trim();
            const vH = inputs[0].value.trim();
            const vM = inputs[1].value.trim();

            if (vH !== "") datosParaEnviar.push({ ...baseObj, situacion_academica: nombreSituacion, sexo: 'Hombre', alumnos: parseInt(vH) });
            if (vM !== "") datosParaEnviar.push({ ...baseObj, situacion_academica: nombreSituacion, sexo: 'Mujer', alumnos: parseInt(vM) });
        }
    });

    if (datosParaEnviar.length === 0) return alert("⚠️ No hay datos capturados para guardar.");

    // 6. Enviar al Servidor
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = '⏳ Enviando...';

    try {
        const res1 = await fetch('/aprovechamiento/guardar_progreso_aprovechamiento', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datosParaEnviar)
        });

        if (!res1.ok) {
            const errorTxt = await res1.text();
            throw new Error(`Error BD: ${errorTxt}`);
        }

        await fetch('/aprovechamiento/actualizar_aprovechamiento', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ periodo: periodoVal })
        });

        localStorage.setItem("filtro_aprovechamiento", JSON.stringify({
            programa: programaVal, modalidad: modalidadVal,
            semestre: semestreActual, turno: turnoActual,
            scrollPos: window.scrollY
        }));

        alert("✅ Guardado exitoso.");
        window.location.reload();

    } catch (e) {
        console.error(e);
        alert("❌ Error al guardar: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ==========================================
// 8. Inicialización
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
    const programaSelect = document.getElementById("programa");
    const modalidadSelect = document.getElementById("modalidad");
    const semestreNumSpan = document.getElementById("semestre-num");
    const turnoNombreSpan = document.getElementById("turno-nombre");

    function cargarProgramas(estadoGuardado = null) {
        if (!programaSelect || !window.aprovechamientos) return;
        programaSelect.innerHTML = "";
        const programasUnicos = [...new Set(window.aprovechamientos.map(item => item.Nombre_Programa).filter(Boolean))];
        programasUnicos.forEach(prog => {
            const opt = document.createElement("option");
            opt.value = prog; opt.textContent = prog;
            programaSelect.appendChild(opt);
        });
        if (estadoGuardado && estadoGuardado.programa) {
            programaSelect.value = estadoGuardado.programa;
            cargarModalidades(estadoGuardado.programa, estadoGuardado);
        } else if (programasUnicos.length > 0) {
            cargarModalidades(programaSelect.value);
        }
    }

    function cargarModalidades(prog, estadoGuardado = null) {
        modalidadSelect.innerHTML = "";
        const modalidadesUnicas = [...new Set(window.aprovechamientos
            .filter(item => item.Nombre_Programa === prog)
            .map(item => item.Modalidad).filter(Boolean))];
        modalidadesUnicas.forEach(mod => {
            const opt = document.createElement("option");
            opt.value = mod; opt.textContent = mod;
            modalidadSelect.appendChild(opt);
        });
        if (estadoGuardado && estadoGuardado.modalidad) {
            modalidadSelect.value = estadoGuardado.modalidad;
            cargarSemestresTabs(prog, estadoGuardado.modalidad, estadoGuardado.semestre);
        } else if (modalidadesUnicas.length > 0) {
            cargarSemestresTabs(prog, modalidadSelect.value);
        }
    }

    function cargarSemestresTabs(prog, mod, semForzado = null) {
        const semestresTabs = document.getElementById("semestres-tabs");
        semestresTabs.innerHTML = "";
        const semestresUnicos = [...new Set(window.aprovechamientos
            .filter(item => item.Nombre_Programa === prog && item.Modalidad === mod)
            .map(item => normalizarSemestre(item.Semestre))
            .filter(s => !isNaN(s)))].sort((a, b) => a - b);

        maxSemestres = semestresUnicos[semestresUnicos.length - 1] || 0;
        semestreActual = semForzado !== null ? Number(semForzado) : (semestresUnicos[0] || 1);
        if (semestreNumSpan) semestreNumSpan.textContent = semestreActual;

        semestresUnicos.forEach((sem) => {
            const tab = document.createElement("button");
            tab.className = "semestre-tab";
            tab.textContent = `Semestre ${sem}`;
            tab.dataset.semestre = sem;
            tab.onclick = function () {
                semestreActual = Number(sem);
                if (semestreNumSpan) semestreNumSpan.textContent = semestreActual;
                actualizarEstiloTabs();
                window.cargarTablaAprovechamiento(prog, mod, semestreActual);
                actualizarEstadoBotones();
            };
            semestresTabs.appendChild(tab);
        });
        actualizarEstiloTabs();
        window.cargarTablaAprovechamiento(prog, mod, semestreActual);
        actualizarEstadoBotones();
    }

    programaSelect.addEventListener("change", function () {
        semestreActual = 1; turnoActual = "Matutino";
        if (turnoNombreSpan) turnoNombreSpan.textContent = turnoActual;
        cargarModalidades(this.value);
    });

    modalidadSelect.addEventListener("change", function () {
        cargarSemestresTabs(programaSelect.value, this.value);
    });

    const guardado = JSON.parse(localStorage.getItem("filtro_aprovechamiento"));
    if (guardado) {
        localStorage.removeItem("filtro_aprovechamiento");
        turnoActual = guardado.turno || "Matutino";
        if (turnoNombreSpan) turnoNombreSpan.textContent = turnoActual;
        cargarProgramas(guardado);
        if (guardado.scrollPos) setTimeout(() => window.scrollTo({ top: guardado.scrollPos, behavior: 'instant' }), 200);
    } else {
        cargarProgramas();
    }
});

function cambiarTurno(direccion) {
    if (maxSemestres === 0) return;
    if (direccion === 1) {
        if (turnoActual === "Matutino") turnoActual = "Vespertino";
        else if (semestreActual < maxSemestres) { semestreActual++; turnoActual = "Matutino"; }
    } else {
        if (turnoActual === "Vespertino") turnoActual = "Matutino";
        else if (semestreActual > 1) { semestreActual--; turnoActual = "Vespertino"; }
    }
    document.getElementById("turno-nombre").textContent = turnoActual;
    document.getElementById("semestre-num").textContent = semestreActual;
    actualizarEstiloTabs();
    window.cargarTablaAprovechamiento(document.getElementById("programa").value, document.getElementById("modalidad").value, semestreActual);
    actualizarEstadoBotones();
}

function actualizarEstadoBotones() {
    const btnA = document.getElementById("btn-turno-anterior");
    const btnS = document.getElementById("btn-turno-siguiente");
    if (btnA) btnA.disabled = (semestreActual === 1 && turnoActual === "Matutino");
    if (btnS) btnS.disabled = (semestreActual === maxSemestres && turnoActual === "Vespertino");
}

async function validarCapturaSemestre() {
    // 1. Confirmación del usuario
    const confirmar = confirm("¿Estás seguro de finalizar la captura de este semestre? Una vez finalizado, el semáforo cambiará a verde y ya no podrás editarlo.");
    if (!confirmar) return;

    // 2. Obtener datos del contexto actual
    const programaVal = document.getElementById("programa").value.trim();
    const modalidadVal = document.getElementById("modalidad").value.trim();
    const periodoVal = document.getElementById('periodo-texto').textContent.trim();
    const semestreTexto = semestreNumeroATexto(semestreActual);

    // Obtenemos nivel del primer registro disponible
    let nivelVal = "Superior";
    if (window.aprovechamientos && window.aprovechamientos.length > 0) {
        nivelVal = window.aprovechamientos[0].Nivel || window.aprovechamientos[0].nivel || "Superior";
    }

    const btn = document.getElementById('btn-validar-matricula');
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = '⏳ Finalizando...';

    try {
        const response = await fetch('/aprovechamiento/finalizar_captura_semestre', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                programa: programaVal,
                modalidad: modalidadVal,
                semestre: semestreTexto,
                periodo: periodoVal,
                nivel: nivelVal
            })
        });

        const result = await response.json();

        if (response.ok) {
            alert("✅ " + result.message);
            window.location.reload(); // Recargamos para ver el semáforo en verde
        } else {
            throw new Error(result.detail || "Error desconocido");
        }

    } catch (e) {
        console.error(e);
        alert("❌ Error al finalizar: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}