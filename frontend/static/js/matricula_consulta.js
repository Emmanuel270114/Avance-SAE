const __MAT = window.__MAT || window.__MAT__ || {};
const gruposEdad = __MAT.gruposEdad ?? [];
const tiposIngreso = __MAT.tiposIngreso ?? [];
const semestresData = __MAT.semestresData ?? [];
const semestresMapJson = __MAT.semestresMapJson ?? {};
const periodoLiteral = __MAT.periodoLiteral ?? "";
const rowsInicialesSp = __MAT.rowsInicialesSp ?? [];
const programaAModalidades = __MAT.programaAModalidades ?? {};
let todasLasModalidades = __MAT.todasLasModalidades ?? [];
const esCapturista = !!__MAT.esCapturista;
const modoVista = __MAT.modoVista ?? "captura";
const idRol = __MAT.idRol ?? null;
const esRolSuperior = !!__MAT.esRolSuperior;
let turnosDisponibles = __MAT.turnosDisponibles ?? [];
let semaforoEstados = __MAT.semaforoEstados ?? [];


    /**
     * Cargar datos de matrícula dinámica para roles superiores
     */
    function cargarDatosMatriculaDinamica(data) {
        // 1. Actualizar metadatos globales
        const metadata = data.metadata;
        
        // Actualizar variables globales con los datos recibidos
        if (metadata.grupos_edad) {
            // Reasignar completamente el array
            gruposEdad.length = 0;
            gruposEdad.push(...metadata.grupos_edad);
        }
        
        if (metadata.tipos_ingreso) {
            tiposIngreso.length = 0;
            tiposIngreso.push(...metadata.tipos_ingreso);
        }
        
        if (metadata.semestres) {
            semestresData.length = 0;
            semestresData.push(...metadata.semestres);
            // Actualizar mapa de semestres
            if (metadata.semestres_map) {
                for (const key in semestresMap) delete semestresMap[key];
                Object.assign(semestresMap, metadata.semestres_map);
            }
        }
        
        if (metadata.turnos) {
            const rawTurnos = metadata.turnos;
            const turnosNormalizados = Array.isArray(rawTurnos)
                ? rawTurnos.map((t, index) => {
                    if (typeof t === 'string') {
                        return { Id_Turno: index + 1, Turno: t };
                    }
                    if (t && typeof t === 'object') {
                        return {
                            Id_Turno: t.Id_Turno ?? t.id_turno ?? t.id ?? index + 1,
                            Turno: t.Turno ?? t.nombre ?? t.Nombre ?? String(t)
                        };
                    }
                    return { Id_Turno: index + 1, Turno: String(t) };
                })
                : [];

            turnosDisponibles.length = 0;
            turnosDisponibles.push(...turnosNormalizados);

            // Alinear UI con el primer turno disponible
            if (turnosDisponibles.length > 0) {
                turnoActualIndex = 0;
                const primerTurno = turnosDisponibles[0];
                const turnoNombreEl = document.getElementById('turno-nombre');
                const turnoInputEl = document.getElementById('turno');
                if (turnoNombreEl) turnoNombreEl.textContent = primerTurno.Turno;
                if (turnoInputEl) turnoInputEl.value = primerTurno.Id_Turno;
            }
        }
        
        // 2. Actualizar selectores con metadatos
        const selectPrograma = document.getElementById('programa');
        if (selectPrograma && metadata.programas) {
            // Placeholder inicial
            selectPrograma.innerHTML = '<option value="">-- Seleccione un Programa --</option>';
            metadata.programas.forEach(prog => {
                const option = document.createElement('option');
                option.value = prog.Id_Programa;
                option.textContent = prog.Nombre_Programa;
                option.dataset.maxSemestre = prog.Id_Semestre;
                selectPrograma.appendChild(option);
            });
        }
        
        const selectModalidad = document.getElementById('modalidad');
        if (selectModalidad) {
            // Actualizar catálogo base de modalidades con lo que venga del SP
            if (metadata.modalidades && Array.isArray(metadata.modalidades)) {
                todasLasModalidades = metadata.modalidades.slice();
            } else {
                todasLasModalidades = [];
            }

            // Reiniciar opciones y dejar que el filtro dependiente las genere
            filtrarModalidadesPorPrograma();
        }
        
        // 3. Procesar estados de semáforo desde las filas del SP
        estadosSemaforoPorSemestre = {};
        if (typeof procesarEstadosSemaforoDelSP === 'function') {
            procesarEstadosSemaforoDelSP(data.rows);
        }
        
        // 4. Procesar y guardar datos por semestre
        if (typeof procesarYGuardarDatosPorSemestre === 'function') {
            procesarYGuardarDatosPorSemestre(data.rows);
        }
        
        // 5. Generar pestañas de semestres
        if (typeof generarPestanasSemestres === 'function') {
            if (semestresDisponiblesSP && semestresDisponiblesSP.length > 0) {
                generarPestanasSemestres(semestresDisponiblesSP);
            } else {
                generarPestanasSemestres(8); // Fallback: 8 semestres por defecto
            }
        }
        
        // 6. Renderizar la tabla de matrícula usando la misma función que roles normales
        if (typeof renderMatriculaFromSP === 'function') {
            (async () => {
                await renderMatriculaFromSP(data.rows, {});
            })();
        } else {
            console.error('❌ Función renderMatriculaFromSP no disponible');
        }
        
        // 7. Aplicar bloqueos y modo vista
        setTimeout(() => {
            if (typeof aplicarTotalGruposParaSemestreYTurnoActual === 'function') {
                aplicarTotalGruposParaSemestreYTurnoActual();
            }
            if (typeof aplicarBloqueoPorSemaforo === 'function') {
                aplicarBloqueoPorSemaforo();
            }
            if (typeof aplicarModoVista === 'function') {
                aplicarModoVista();
            }
        }, 200);
        
        // 8. Procesar estado de validación (NUEVO para roles superiores)
        if (data.validacion_estado) {
            procesarEstadoValidacion(data.validacion_estado);
        }
    }
    
    /**
     * Procesar estado de validación y actualizar UI
     */
    function procesarEstadoValidacion(validacionEstado) {
        // Actualizar variables globales (si existen)
        if (typeof window !== 'undefined') {
            window.usuarioYaValido = validacionEstado.usuario_ya_valido;
            window.usuarioYaRechazo = validacionEstado.usuario_ya_rechazo;
            window.puedeValidar = validacionEstado.puede_validar;
            window.matriculaRechazada = validacionEstado.matricula_rechazada;
        }
        
        // Actualizar botones de validación
        actualizarBotonesValidacionRolSuperior(validacionEstado);
        
        // Mostrar banner de rechazo si existe
        if (validacionEstado.rechazo_info) {
            mostrarBannerRechazoRolSuperior(validacionEstado.rechazo_info);
        }
        
        // Mostrar mensaje de estado en la UI
        //mostrarMensajeEstadoValidacion(validacionEstado);
    }
    
    /**
     * Actualizar visibilidad de botones de validación según estado
     */
    function actualizarBotonesValidacionRolSuperior(validacionEstado) {
        // Buscar botones por su función onclick (son los botones reales en el HTML)
        const botones = document.querySelectorAll('.acciones-validacion button');
        let btnValidar = null;
        let btnRechazar = null;
        
        botones.forEach(btn => {
            if (btn.onclick && btn.onclick.toString().includes('validarSemestre')) {
                btnValidar = btn;
            } else if (btn.onclick && btn.onclick.toString().includes('rechazarSemestre')) {
                btnRechazar = btn;
            }
        });
        
        const contenedorBotones = document.querySelector('.acciones-validacion');
        const mensajeValidacionPrevia = document.querySelector('.mensaje-validacion-previa');
        
        if (contenedorBotones) {
            if (validacionEstado.usuario_ya_valido || validacionEstado.usuario_ya_rechazo) {
                // Usuario ya actuó - OCULTAR botones completamente
                contenedorBotones.style.display = 'none';
                
                // Crear o actualizar mensaje de validación previa
                let mensaje = mensajeValidacionPrevia;
                if (!mensaje) {
                    mensaje = document.createElement('div');
                    mensaje.className = 'mensaje-validacion-previa';
                    mensaje.style.cssText = 'margin-top: 20px; padding: 15px; border-radius: 8px; text-align: center; font-size: 16px;';
                    contenedorBotones.parentNode.insertBefore(mensaje, contenedorBotones);
                }
                
                mensaje.style.display = 'block';
                if (validacionEstado.usuario_ya_valido) {
                    mensaje.className = 'mensaje-validacion-previa validada';
                    mensaje.style.backgroundColor = '#d4edda';
                    mensaje.style.color = '#155724';
                    mensaje.style.border = '1px solid #c3e6cb';
                    mensaje.innerHTML = '<span class="icono-info">✅</span> Ya has <strong>validado</strong> esta matrícula previamente.';
                } else {
                    mensaje.className = 'mensaje-validacion-previa rechazada';
                    mensaje.style.backgroundColor = '#f8d7da';
                    mensaje.style.color = '#721c24';
                    mensaje.style.border = '1px solid #f5c6cb';
                    mensaje.innerHTML = '<span class="icono-info">❌</span> Ya has <strong>rechazado</strong> esta matrícula previamente.';
                }
                
            } else if (!validacionEstado.puede_validar) {
                // Usuario no puede validar aún - OCULTAR botones
                contenedorBotones.style.display = 'none';
                
                // Crear o actualizar mensaje
                let mensaje = mensajeValidacionPrevia;
                if (!mensaje) {
                    mensaje = document.createElement('div');
                    mensaje.className = 'mensaje-validacion-previa';
                    mensaje.style.cssText = 'margin-top: 20px; padding: 15px; border-radius: 8px; text-align: center; font-size: 16px;';
                    contenedorBotones.parentNode.insertBefore(mensaje, contenedorBotones);
                }
                
                mensaje.style.display = 'block';
                mensaje.style.backgroundColor = '#fff3cd';
                mensaje.style.color = '#856404';
                mensaje.style.border = '1px solid #ffeeba';
                mensaje.innerHTML = '<span class="icono-info">⏳</span> Esperando validación de nivel anterior.';
                
            } else {
                // Usuario puede validar - MOSTRAR botones
                contenedorBotones.style.display = '';
                
                if (btnValidar) {
                    btnValidar.disabled = false;
                    btnValidar.title = 'Validar matrícula';
                }
                if (btnRechazar) {
                    btnRechazar.disabled = false;
                    btnRechazar.title = 'Rechazar matrícula';
                }
                
                // Ocultar mensaje si existe
                if (mensajeValidacionPrevia) {
                    mensajeValidacionPrevia.style.display = 'none';
                }
                
            }
        }
    }
    
    /**
     * Mostrar banner de rechazo para roles superiores
     */
    function mostrarBannerRechazoRolSuperior(rechazoInfo) {
        let banner = document.getElementById('banner-rechazo-rol-superior');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'banner-rechazo-rol-superior';
            banner.className = 'banner-rechazo';
            document.getElementById('contenedor-matricula-principal').prepend(banner);
        }
        
        banner.innerHTML = `
            <div class="banner-rechazo-icon">
                <span class="icono-advertencia-grande">⚠️</span>
            </div>
            <div class="banner-rechazo-content">
                <div class="banner-rechazo-header">
                    <h3>❌ MATRÍCULA RECHAZADA - CORRECCIONES REQUERIDAS</h3>
                    <button class="btn-cerrar-banner" onclick="cerrarBannerRechazo()" title="Cerrar">✕</button>
                </div>
                <div class="banner-rechazo-body">
                    <div class="rechazo-motivo">
                        <strong>Motivo del Rechazo:</strong>
                        <p>${rechazoInfo.motivo}</p>
                    </div>
                    <div class="rechazo-meta">
                        <span><strong>Rechazado por:</strong> ${rechazoInfo.rechazado_por}</span>
                        <span class="separador">•</span>
                        <span><strong>Fecha:</strong> ${rechazoInfo.fecha}</span>
                        <span class="separador">•</span>
                        <span><strong>UA:</strong> ${rechazoInfo.unidad}</span>
                    </div>
                </div>
            </div>
        `;
        
        banner.style.display = 'flex';
    }
    /**
     * Mostrar mensaje de estado de validación
     */
    /**
    function mostrarMensajeEstadoValidacion(validacionEstado) {
        const contenedor = document.getElementById('contenedor-matricula-principal');
        let mensajeExito = contenedor.querySelector('.mensaje-exito-carga');
        if (!mensajeExito) {
            mensajeExito = document.createElement('div');
            mensajeExito.className = 'mensaje-exito-carga';
            mensajeExito.style.cssText = 'padding: 20px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; margin: 20px 0; color: #155724; text-align: center;';
            contenedor.prepend(mensajeExito);
        }
        
        const estadoTexto = validacionEstado.puede_validar ? 
            '✅ Puede validar esta matrícula' : 
            validacionEstado.usuario_ya_valido ? 
            '🔒 Ya validó esta matrícula' :
            validacionEstado.usuario_ya_rechazo ?
            '❌ Ya rechazó esta matrícula' :
            '⏳ En espera de validación previa';
        
        mensajeExito.innerHTML = `
            <strong>📊 Estado de Validación</strong><br>
            <small>${estadoTexto}</small>
        `;
    }
    **/
    /* ==============================================
       FIN FUNCIONALIDAD ROLES SUPERIORES
       ============================================== */
    
    // === BANDERAS GLOBALES DE ESTADO ===
    let spEnEjecucion = false; // Bandera para saber si hay un SP ejecutándose
    let interfazBloqueada = false; // Bandera para saber si la interfaz está bloqueada
    
    // ✨ CACHE DE ELEMENTOS DOM (OPTIMIZACIÓN)
    const domCache = {
        periodo: null,
        programa: null,
        modalidad: null,
        semestre: null,
        turno: null,
        tbody: null,
        totalGrupos: null,
        totalMasculino: null,
        totalFemenino: null,
        totalGeneral: null
    };
    
    // Función para inicializar cache DOM
    function inicializarCacheDOM() {
        domCache.periodo = document.getElementById('periodo');
        domCache.programa = document.getElementById('programa');
        domCache.modalidad = document.getElementById('modalidad');
        domCache.semestre = document.getElementById('semestre');
        domCache.turno = document.getElementById('turno');
        domCache.tbody = document.getElementById('matricula-tbody');
        domCache.totalGrupos = null; // ya no se usa input global
        domCache.totalMasculino = document.querySelector('#total_masculino');
        domCache.totalFemenino = document.querySelector('#total_femenino');
        domCache.totalGeneral = document.querySelector('#total_general');
        console.log('✅ Cache DOM inicializado');
    }
    
    //  DEBOUNCING UTILITY (OPTIMIZACIÓN)
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    //  THROTTLING UTILITY (OPTIMIZACIÓN)
    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Normalizar labels para comparaciones consistentes (acentos, mayusculas, espacios)
    function normalizeLabel(value) {
        return String(value || '')
            .trim()
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '');
    }

    function mapSemestreToId(valorSemestre) {
        if (valorSemestre === undefined || valorSemestre === null) return NaN;
        const raw = String(valorSemestre).trim();
        const byId = parseInt(raw);
        if (!isNaN(byId)) return byId;

        const norm = normalizeLabel(raw);
        const semestreIdPorNombre = Object.keys(semestresMap).find(
            id => normalizeLabel(semestresMap[id]) === norm
        );
        if (semestreIdPorNombre) return parseInt(semestreIdPorNombre);

        const ordinalMap = {
            primero: 1,
            segundo: 2,
            tercero: 3,
            cuarto: 4,
            quinto: 5,
            sexto: 6,
            septimo: 7,
            octavo: 8,
            noveno: 9,
            decimo: 10,
            undecimo: 11,
            duodecimo: 12
        };
        return ordinalMap[norm] || NaN;
    }

    function mapTurnoToId(valorTurno) {
        if (valorTurno === undefined || valorTurno === null) return NaN;
        const raw = String(valorTurno).trim();
        const byId = parseInt(raw);
        if (!isNaN(byId)) return byId;

        if (Array.isArray(turnosDisponibles)) {
            const turnoObj = turnosDisponibles.find(t => {
                if (typeof t === 'string') {
                    return normalizeLabel(t) === normalizeLabel(raw);
                }
                if (t && typeof t === 'object') {
                    return normalizeLabel(t.Turno) === normalizeLabel(raw);
                }
                return false;
            });
            if (turnoObj && typeof turnoObj === 'object') {
                return parseInt(turnoObj.Id_Turno);
            }
            if (typeof turnoObj === 'string') {
                const index = turnosDisponibles.findIndex(x => normalizeLabel(x) === normalizeLabel(raw));
                return index >= 0 ? index + 1 : NaN;
            }
        }

        return NaN;
    }

    function obtenerTiposIngresoPorSemestre(semestreNum) {
        const semestreId = parseInt(semestreNum);
        if (semestreId === 1) {
            return [
                { id: '1', nombre: 'Nuevo Ingreso' },
                { id: '3', nombre: 'Repetidores' }
            ];
        }
        return [
            { id: '2', nombre: 'Reingreso' },
            { id: '3', nombre: 'Repetidores' }
        ];
    }

    function renderizarEncabezadoTabla(semestreNum, turnosList) {
        const thead = document.getElementById('matricula-thead') || document.querySelector('.tabla-matricula-completa thead');
        if (!thead) return;

        const tiposIngresoVisibles = obtenerTiposIngresoPorSemestre(semestreNum);
        const turnos = Array.isArray(turnosList) && turnosList.length > 0 ? turnosList : [];

        thead.innerHTML = '';

        const row1 = document.createElement('tr');
        row1.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        row1.style.color = 'white';

        const thEdad = document.createElement('th');
        thEdad.className = 'col-edad';
        thEdad.style.padding = '15px';
        thEdad.style.textAlign = 'center';
        thEdad.style.fontWeight = '700';
        thEdad.style.fontSize = '30px';
        // Ancho fijo para que "Edad" quede alineado con la columna de edades
        thEdad.style.width = '160px';
        thEdad.style.minWidth = '160px';
        thEdad.style.maxWidth = '180px';
        // Línea divisoria vertical a la derecha de "Edad" solo en encabezados
        thEdad.style.borderRight = '3px solid rgba(255,255,255,0.9)';
        // Ocupa las filas del encabezado (Edad / Tipo de ingreso)
        thEdad.rowSpan = 2;
        thEdad.textContent = 'Edad';
        row1.appendChild(thEdad);

        turnos.forEach(turno => {
            const thTurno = document.createElement('th');
            thTurno.style.padding = '10px 8px';
            thTurno.style.textAlign = 'center';
            thTurno.style.fontWeight = '700';
            thTurno.style.fontSize = '30px';
            thTurno.colSpan = tiposIngresoVisibles.length;
            thTurno.style.borderRight = '3px solid rgba(255,255,255,0.9)';

            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.flexDirection = 'row';
            wrapper.style.alignItems = 'center';
            wrapper.style.justifyContent = 'center';
            wrapper.style.gap = '8px';

            const tituloTurno = document.createElement('span');
            tituloTurno.textContent = turno.nombre || `Turno ${turno.id}`;
            tituloTurno.style.fontWeight = '700';
            tituloTurno.style.fontSize = '30px';

            const sub = document.createElement('div');
            sub.style.display = 'flex';
            sub.style.alignItems = 'center';
            sub.style.gap = '4px';
            sub.style.fontSize = '11px';

            const label = document.createElement('span');
            label.textContent = 'Grupos:';

            const input = document.createElement('input');
            input.type = 'number';
            input.min = '0';
            input.className = 'input-total-grupos-turno';
            input.setAttribute('data-turno-id', turno.id);
            input.setAttribute('data-semestre-id', semestreNum);

            // Valor inicial desde el mapa (si ya hay datos del SP o localStorage)
            const claveInicial = `${semestreNum}_${turno.id}`;
            const valorInicial = totalGruposPorSemestreYTurno[claveInicial];
            if (valorInicial !== undefined && valorInicial !== null && valorInicial !== '') {
                input.value = valorInicial;
            }

            const actualizarTotalGrupos = () => {
                const valor = input.value;
                const clave = `${semestreNum}_${turno.id}`;
                if (valor === '' || isNaN(parseInt(valor)) || parseInt(valor) < 0) {
                    delete totalGruposPorSemestreYTurno[clave];
                } else {
                    totalGruposPorSemestreYTurno[clave] = parseInt(valor) || 0;
                }
                recalcularTotalGruposSemestre(semestreNum);
                guardarTotalGruposEnLocalStorage();
            };

            input.addEventListener('input', actualizarTotalGrupos);
            input.addEventListener('change', actualizarTotalGrupos);

            sub.appendChild(label);
            sub.appendChild(input);

            wrapper.appendChild(tituloTurno);
            wrapper.appendChild(sub);

            thTurno.appendChild(wrapper);
            row1.appendChild(thTurno);
        });

        const row2 = document.createElement('tr');
        row2.style.background = 'linear-gradient(135deg, #7b8cf0 0%, #8463b5 100%)';
        row2.style.color = 'white';

        turnos.forEach((turno, indexTurno) => {
            tiposIngresoVisibles.forEach((tipo, indexTipo) => {
                const thTipo = document.createElement('th');
                thTipo.className = 'col-tipo-ingreso';
                thTipo.style.padding = '12px';
                thTipo.style.textAlign = 'center';
                thTipo.style.fontWeight = '600';
                thTipo.style.fontSize = '15px';
                // Ancho mínimo suficiente para que el par de inputs H/M no rebase la línea divisoria
                thTipo.style.minWidth = '160px';
                // Línea divisoria más gruesa al final de cada turno (misma blanca que Turnos)
                if (indexTipo === tiposIngresoVisibles.length - 1) {
                    thTipo.style.borderRight = '3px solid rgba(255,255,255,0.9)';
                }
                thTipo.textContent = tipo.nombre;
                row2.appendChild(thTipo);
            });
        });
        thead.appendChild(row1);
        thead.appendChild(row2);
    }
    
    // Variables globales con datos del backend
    // Filas iniciales del SP que el backend ya ejecutó al renderizar la vista
    // (solo estarán presentes para roles que usan captura_matricula_sp_view)

    // Mapeo Programa -> Modalidades para filtros dependientes
    // Catálogo base de modalidades disponible para filtrado (roles 3-5).
    // Para roles superiores se actualizará posteriormente con los metadatos del SP.
    
    // Variables de control de acceso por rol
    // Indica si el usuario es rol superior (coordinador/validador en niveles altos)
    
    // Crear mapa de semestres (ID -> Nombre)
    const semestresMap = semestresMapJson || {};

    /**
     * Filtrar modalidades según el programa seleccionado usando el mapeo
     * programaAModalidades y el catálogo "todasLasModalidades".
     */
    function filtrarModalidadesPorPrograma() {
        const selectPrograma = document.getElementById('programa');
        const selectModalidad = document.getElementById('modalidad');

        if (!selectPrograma || !selectModalidad) {
            console.error('❌ No se encontraron los selectores de programa o modalidad');
            return;
        }

        const programaId = selectPrograma.value; // string

        if (!programaId) {
            selectModalidad.innerHTML = '<option value="">-- Primero seleccione un Programa --</option>';
            selectModalidad.disabled = true;
            return;
        }

        const mapping = programaAModalidades || {};
        const modalidadesDelPrograma = mapping[programaId] || mapping[parseInt(programaId)] || [];

        if (!Array.isArray(todasLasModalidades)) {
            todasLasModalidades = [];
        }

        if (modalidadesDelPrograma.length === 0) {
            console.warn(`⚠️ No hay modalidades configuradas para el programa ${programaId}`);
            selectModalidad.innerHTML = '<option value="">-- No hay modalidades para este programa --</option>';
            selectModalidad.disabled = true;
            return;
        }

        const modalidadesFiltradas = todasLasModalidades.filter(mod => {
            const id = mod.Id_Modalidad ?? mod.id ?? mod.Id ?? mod.ID;
            return modalidadesDelPrograma.includes(id);
        });

        if (modalidadesFiltradas.length === 0) {
            selectModalidad.innerHTML = '<option value="">-- No hay modalidades para este programa --</option>';
            selectModalidad.disabled = true;
            return;
        }

        selectModalidad.innerHTML = '<option value="">-- Seleccione una Modalidad --</option>';
        modalidadesFiltradas.forEach(mod => {
            const id = mod.Id_Modalidad ?? mod.id ?? mod.Id ?? mod.ID;
            const nombre = mod.Modalidad ?? mod.nombre ?? mod.Nombre ?? String(id);
            const option = document.createElement('option');
            option.value = id;
            option.textContent = nombre;
            selectModalidad.appendChild(option);
        });

        selectModalidad.disabled = false;
    }

    /**
     * Mostrar u ocultar la sección de captura (pestañas + tabla + totales)
     * según si ambos filtros (programa y modalidad) están seleccionados.
     */
    function actualizarVisibilidadCapturaSegunFiltros() {
        const contCaptura = document.getElementById('captura-matricula-container');
        if (!contCaptura) return;

        const selPrograma = document.getElementById('programa');
        const selModalidad = document.getElementById('modalidad');
        const programaValido = !!(selPrograma && selPrograma.value);
        const modalidadValida = !!(selModalidad && selModalidad.value);

        if (programaValido && modalidadValida) {
            contCaptura.style.display = '';
        } else {
            contCaptura.style.display = 'none';
        }
    }
    
    // === FUNCIONES DE CONTROL DE CARGA CON SWEETALERT2 ===
    function mostrarOverlayCarga(texto = 'Procesando...', subtexto = 'Por favor espere') {
        spEnEjecucion = true;
        interfazBloqueada = true;
        Swal.fire({
            title: texto,
            text: subtexto,
            allowOutsideClick: false,
            allowEscapeKey: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
    }
    
    function ocultarOverlayCarga() {
        spEnEjecucion = false;
        interfazBloqueada = false;
        Swal.close();
    }
    
    function verificarSiPuedeContinuar() {
        if (spEnEjecucion || interfazBloqueada) {
            console.warn('⚠️ Operación bloqueada: hay un SP en ejecución');
            return false;
        }
        return true;
    }

    // Mapa: Total Grupos por semestre (vista consolidada)
    let totalGruposPorSemestre = {};
    // Mapa: Total Grupos por semestre y turno
    let totalGruposPorSemestreYTurno = {};
    // Cache de filas del SP para fallback
    let lastRowsSp = [];
    if (typeof window !== 'undefined') {
        window.totalGruposPorSemestre = totalGruposPorSemestre;
        window.totalGruposPorSemestreYTurno = totalGruposPorSemestreYTurno;
        window.lastRowsSp = lastRowsSp;
    }

    function generarClaveTotalGrupos() {
        const periodo = document.getElementById('periodo').value;
        const programa = document.getElementById('programa').value;
        const modalidad = document.getElementById('modalidad').value;
        // No incluir turno: el mapa es por semestre en esta vista
        return `totalgrupos_${periodo}_${programa}_${modalidad}`;
    }

    function cargarTotalGruposDeLocalStorage() {
        try {
            const key = generarClaveTotalGrupos();
            const raw = localStorage.getItem(key);
            const parsed = raw ? JSON.parse(raw) : {};

            // Compatibilidad hacia atrás: si el objeto tiene forma antigua, asumir que son totales por semestre
            if (parsed && typeof parsed === 'object' && (parsed.porSemestre || parsed.porSemestreTurno)) {
                totalGruposPorSemestre = parsed.porSemestre || {};
                totalGruposPorSemestreYTurno = parsed.porSemestreTurno || {};
            } else {
                totalGruposPorSemestre = (parsed && typeof parsed === 'object') ? parsed : {};
                totalGruposPorSemestreYTurno = {};
            }

            if (typeof window !== 'undefined') {
                window.totalGruposPorSemestre = totalGruposPorSemestre;
                window.totalGruposPorSemestreYTurno = totalGruposPorSemestreYTurno;
            }
        } catch (e) {
            console.warn('No se pudo cargar totalGruposPorSemestre de localStorage', e);
            totalGruposPorSemestre = {};
            totalGruposPorSemestreYTurno = {};
            if (typeof window !== 'undefined') {
                window.totalGruposPorSemestre = totalGruposPorSemestre;
                window.totalGruposPorSemestreYTurno = totalGruposPorSemestreYTurno;
            }
        }
    }

    function guardarTotalGruposEnLocalStorage() {
        try {
            const key = generarClaveTotalGrupos();
            const payload = {
                porSemestre: totalGruposPorSemestre,
                porSemestreTurno: totalGruposPorSemestreYTurno
            };
            localStorage.setItem(key, JSON.stringify(payload));
        } catch (e) {
            console.warn('No se pudo guardar totalGruposPorSemestre en localStorage', e);
        }
    }

    function recalcularTotalGruposSemestre(semestreId) {
        if (!semestreId) return;
        const semIdNum = parseInt(semestreId);
        let suma = 0;
        Object.entries(totalGruposPorSemestreYTurno || {}).forEach(([clave, valor]) => {
            const [semKey] = clave.split('_');
            if (parseInt(semKey) === semIdNum) {
                const n = parseInt(valor);
                if (!isNaN(n) && n >= 0) {
                    suma += n;
                }
            }
        });
        totalGruposPorSemestre[semIdNum] = suma;
        if (typeof window !== 'undefined') {
            window.totalGruposPorSemestre = totalGruposPorSemestre;
        }
    }

    // Procesar y mapear los valores de "Grupos" que vienen del SP
    // a los mapas globales totalGruposPorSemestre y totalGruposPorSemestreYTurno
    function procesarTotalGruposDesdeSP(rows) {
        try {
            if (!Array.isArray(rows) || rows.length === 0) return;

            // Reiniciar mapas para el nuevo contexto (periodo/programa/modalidad)
            totalGruposPorSemestre = {};
            totalGruposPorSemestreYTurno = {};

            const first = rows[0] || {};
            const keys = Object.keys(first);

            const semestreCandidates = ['Semestre', 'Id_Semestre', 'IdSemestre', 'Nombre_Semestre'];
            const turnoCandidates = ['Turno', 'Nombre_Turno', 'Id_Turno', 'IdTurno'];
            const gruposCandidates = ['Grupos', 'Total_Grupos', 'Salones'];

            function findKey(cands) {
                for (let c of cands) if (keys.includes(c)) return c;
                const low = keys.reduce((acc, k) => { acc[k.toLowerCase()] = k; return acc; }, {});
                for (let c of cands) if (low[c.toLowerCase()]) return low[c.toLowerCase()];
                return null;
            }

            const semestreKey = findKey(semestreCandidates);
            const turnoKey = findKey(turnoCandidates);
            const gruposKey = findKey(gruposCandidates);

            if (!semestreKey || !turnoKey || !gruposKey) {
                console.warn('⚠️ No se pudieron identificar columnas de semestre/turno/grupos en los datos del SP');
                return;
            }

            // Obtener filtros actuales de programa y modalidad para no mezclar carreras
            const programaActualId = parseInt(document.getElementById('programa')?.value || '0');
            const programaActualNombre = document.getElementById('programa')?.selectedOptions[0]?.text || '';
            const modalidadActualId = parseInt(document.getElementById('modalidad')?.value || '0');
            const modalidadActualNombre = document.getElementById('modalidad')?.selectedOptions[0]?.text || '';

            const semestresARecalcular = new Set();

            rows.forEach(row => {
                // Filtro por programa si hay información en la fila
                if (row.Id_Programa || row.Nombre_Programa) {
                    const programaRowId = row.Id_Programa ? parseInt(row.Id_Programa) : null;
                    const programaRowNombre = row.Nombre_Programa ? String(row.Nombre_Programa) : '';
                    const programaMatch = (programaRowId === programaActualId) ||
                        (normalizeLabel(programaRowNombre) === normalizeLabel(programaActualNombre));
                    if (!programaMatch) {
                        return;
                    }
                }

                // Filtro por modalidad (por id o nombre)
                const modalidadEnRow = row.Id_Modalidad || row.Nombre_Modalidad || row.Modalidad;
                if (modalidadEnRow !== undefined && modalidadEnRow !== null) {
                    const modalidadRowId = row.Id_Modalidad ? parseInt(row.Id_Modalidad) : null;
                    const modalidadRowNombre = row.Nombre_Modalidad ? String(row.Nombre_Modalidad) : (row.Modalidad ? String(row.Modalidad) : '');
                    const modalidadMatch = (modalidadRowId === modalidadActualId) ||
                        (normalizeLabel(modalidadRowNombre) === normalizeLabel(modalidadActualNombre));
                    if (!modalidadMatch) {
                        return;
                    }
                }

                const semestreId = mapSemestreToId(row[semestreKey]);
                const turnoId = mapTurnoToId(row[turnoKey]);
                const valor = row[gruposKey];
                const num = parseInt(valor);

                // Solo considerar valores numéricos positivos
                if (isNaN(semestreId) || isNaN(turnoId) || isNaN(num) || num <= 0) {
                    return;
                }

                const clave = `${semestreId}_${turnoId}`;
                // Si hay múltiples filas para el mismo semestre/turno,
                // conservar el valor máximo reportado por el SP
                if (totalGruposPorSemestreYTurno[clave] === undefined || num > totalGruposPorSemestreYTurno[clave]) {
                    totalGruposPorSemestreYTurno[clave] = num;
                }
                semestresARecalcular.add(semestreId);
            });

            // Recalcular totales por semestre usando el helper existente
            semestresARecalcular.forEach(semId => {
                recalcularTotalGruposSemestre(semId);
            });

            // Persistir en localStorage para navegación posterior entre semestres/turnos
            guardarTotalGruposEnLocalStorage();

            if (typeof window !== 'undefined') {
                window.totalGruposPorSemestre = totalGruposPorSemestre;
                window.totalGruposPorSemestreYTurno = totalGruposPorSemestreYTurno;
            }
        } catch (e) {
            console.warn('⚠️ Error al procesar Total Grupos desde SP', e);
        }
    }

    function obtenerGruposDesdeRows(semestreId, turnoId, semestreNombre, turnoNombre) {
        if (!Array.isArray(lastRowsSp) || lastRowsSp.length === 0) return null;
        let gruposEncontrados = null;
        for (const row of lastRowsSp) {
            const rowSem = mapSemestreToId(row.Semestre ?? row.Id_Semestre ?? row.IdSemestre ?? row.Nombre_Semestre);
            const rowTur = mapTurnoToId(row.Turno ?? row.Nombre_Turno ?? row.Id_Turno ?? row.IdTurno);
            const semOk = (!isNaN(semestreId) && rowSem === semestreId) ||
                (semestreNombre && normalizeLabel(row.Semestre) === normalizeLabel(semestreNombre));
            const turOk = (!isNaN(turnoId) && rowTur === turnoId) ||
                (turnoNombre && normalizeLabel(row.Turno) === normalizeLabel(turnoNombre));
            if (semOk && turOk) {
                const valor = row.Grupos ?? row.grupos ?? row.GRUPOS;
                if (valor !== undefined && valor !== null) {
                    gruposEncontrados = parseInt(valor);
                    break;
                }
            }
        }
        return isNaN(gruposEncontrados) ? null : gruposEncontrados;
    }

    function obtenerGruposDesdeRowsPorSemestre(semestreId, semestreNombre) {
        if (!Array.isArray(lastRowsSp) || lastRowsSp.length === 0) return null;
        let total = 0;
        let encontrado = false;
        for (const row of lastRowsSp) {
            const rowSem = mapSemestreToId(row.Semestre ?? row.Id_Semestre ?? row.IdSemestre ?? row.Nombre_Semestre);
            const semOk = (!isNaN(semestreId) && rowSem === semestreId) ||
                (semestreNombre && normalizeLabel(row.Semestre) === normalizeLabel(semestreNombre));
            if (!semOk) continue;
            const valor = row.Grupos ?? row.grupos ?? row.GRUPOS;
            if (valor !== undefined && valor !== null && !isNaN(parseInt(valor))) {
                total += parseInt(valor);
                encontrado = true;
            }
        }
        return encontrado ? total : null;
    }

    // Aplicar Total Grupos a los inputs por turno del semestre actual
    function aplicarTotalGruposParaSemestreYTurnoActual() {
        let semestreActual = domCache.semestre?.value || document.getElementById('semestre')?.value;
        if (!semestreActual) return;

        const semestreNum = parseInt(semestreActual);
        const estado = estadosSemaforoPorSemestre[semestreNum];
        const debeBloquear = parseInt(estado) === 3;

        const inputsTurno = document.querySelectorAll(
            `.input-total-grupos-turno[data-semestre-id="${semestreNum}"]`
        );

        inputsTurno.forEach(input => {
            const turnoId = input.getAttribute('data-turno-id');
            const clave = `${semestreNum}_${turnoId}`;
            const valor = totalGruposPorSemestreYTurno[clave];
            input.value = (valor !== undefined && valor !== null && valor !== '') ? valor : '';

            input.disabled = !!debeBloquear;
            input.classList.toggle('input-disabled', !!debeBloquear);
            input.title = debeBloquear ? 'Semestre finalizado (bloqueado)' : '';
        });
    }

    // Función para cargar datos existentes cuando cambien los filtros usando SP
    async function cargarDatosExistentes() {
        // Si el acceso está restringido, no hacer nada
        if (accesoRestringido) {
            return;
        }
        
        // Verificar si ya hay un SP ejecutándose
        if (!verificarSiPuedeContinuar()) {
            return;
        }
        
        // Mostrar overlay de carga
        mostrarOverlayCarga('Cargando Datos...', 'Consultando datos del servidor');
        
        const periodo = document.getElementById('periodo').value;
        let programa = document.getElementById('programa').value;
        const modalidad = document.getElementById('modalidad').value;
        const semestre = document.getElementById('semestre').value;
        
        // **LÓGICA ESPECIAL PARA TRONCO COMÚN**
        // Obtener el nombre del programa seleccionado
        const programaSelect = document.getElementById('programa');
        const programaNombre = programaSelect?.selectedOptions[0]?.text || '';
        
        // Si el programa es "Tronco Común", forzar id_programa = 1
        if (programaNombre.toLowerCase().includes('tronco común')) {
            programa = '1';
        }
        
        if (!periodo || !programa || !modalidad || !semestre) {
            generarTablaVacia();
            ocultarOverlayCarga();
            return;
        }
        
        try {
            // ✨ OPTIMIZACIÓN MÁXIMA: NO enviar semestre/turno para traer TODO de una vez
            const requestData = {
                periodo: periodo,
                programa: programa,
                modalidad: modalidad
                // NO enviamos semestre ni turno para que el SP devuelva TODOS los datos
            };
            const contextoCarga = obtenerClaveContextoDatos();
            ultimoContextoCarga = contextoCarga;
            
            // Si es rol superior, agregar contexto seleccionado (UA y Nivel)
            if (esRolSuperior && window.contextoRolSuperior) {
                requestData.id_unidad_academica = window.contextoRolSuperior.id_unidad_academica;
                requestData.id_nivel = window.contextoRolSuperior.id_nivel;
            }
            
            const response = await fetch('/matricula/obtener_datos_existentes_sp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            const resultado = await response.json();
            if (ultimoContextoCarga !== obtenerClaveContextoDatos()) {
                ocultarOverlayCarga();
                return;
            }
            if (resultado && Array.isArray(resultado.rows)) {
                lastRowsSp = resultado.rows;
                if (typeof window !== 'undefined') {
                    window.lastRowsSp = lastRowsSp;
                }
            }
            
            // Al cambiar de programa/modalidad, limpiar estados de semáforo previos para no arrastrar bloqueos
            // Se reconstruirán con las filas del SP del nuevo contexto
            estadosSemaforoPorSemestre = {};

            if (resultado.error) {
                console.error('Error al cargar datos existentes:', resultado.error);
                generarTablaVacia();
                ocultarOverlayCarga();
                return;
            }
            
            // Si el backend devolvió rows (raw) preferimos reconstruir la tabla desde ellas
            if (resultado.rows && resultado.rows.length > 0) {
                // 1. Procesar estados de semáforo de TODOS los semestres
                procesarEstadosSemaforoDelSP(resultado.rows);
                
                // 2. Guardar TODOS los datos organizados por semestre y turno en memoria
                procesarYGuardarDatosPorSemestre(resultado.rows);

                // 2.2. Mapear los valores de "Grupos" del SP a los mapas globales
                // para que los inputs de Total Grupos por turno se rellenen correctamente
                procesarTotalGruposDesdeSP(resultado.rows);

                // 2.1. Derivar turnos visibles desde las rows del SP
                try {
                    const turnoCandidates = ['Turno', 'Nombre_Turno', 'Id_Turno', 'IdTurno'];
                    const first = resultado.rows[0] || {};
                    const keys = Object.keys(first);
                    const findKey = (cands) => {
                        for (let c of cands) if (keys.includes(c)) return c;
                        const low = keys.reduce((acc, k) => { acc[k.toLowerCase()] = k; return acc; }, {});
                        for (let c of cands) if (low[c.toLowerCase()]) return low[c.toLowerCase()];
                        return null;
                    };
                    const turnoKey = findKey(turnoCandidates);
                    const turnosMap = new Map();
                    if (turnoKey) {
                        resultado.rows.forEach(r => {
                            const turnoRaw = r[turnoKey];
                            const turnoId = mapTurnoToId(turnoRaw);
                            if (isNaN(turnoId)) return;
                            let turnoNombre = '';
                            const rawStr = String(turnoRaw || '').trim();
                            if (rawStr && isNaN(parseInt(rawStr))) {
                                turnoNombre = rawStr;
                            }
                            if (!turnoNombre && Array.isArray(turnosDisponibles)) {
                                const match = turnosDisponibles.find(t => parseInt(t.Id_Turno) === turnoId);
                                if (match) turnoNombre = match.Turno;
                            }
                            turnosMap.set(turnoId, { id: turnoId, nombre: turnoNombre || `Turno ${turnoId}` });
                        });
                    }
                    if (turnosMap.size === 0 && Array.isArray(turnosDisponibles)) {
                        turnosDisponibles.forEach(t => {
                            const turnoId = parseInt(t.Id_Turno);
                            if (!isNaN(turnoId)) {
                                turnosMap.set(turnoId, { id: turnoId, nombre: t.Turno });
                            }
                        });
                    }
                    turnosVisibles = Array.from(turnosMap.values()).sort((a, b) => a.id - b.id);
                } catch (e) {
                    console.warn('⚠️ No se pudieron derivar turnos visibles desde el SP', e);
                    turnosVisibles = [];
                }
                
                // 3. Renderizar tabla completa usando la lógica común basada en rows del SP
                //    (incluye reglas de semestres para Tronco Común y programas Técnicos)
                if (typeof renderMatriculaFromSP === 'function') {
                    await renderMatriculaFromSP(resultado.rows, {});
                } else {
                    console.error('❌ Función renderMatriculaFromSP no disponible');
                    generarTablaVacia(false);
                }

                // ✨ MARCAR que los datos completos ya fueron cargados
                datosCompletosYaCargados = true;

                // ✨ APLICAR TODAS las restricciones después de renderizar
                // Aplicar restricciones después de renderizar pestañas
                aplicarTotalGruposParaSemestreYTurnoActual();
                aplicarBloqueoPorSemaforo();
                aplicarModoVista();
                calcularTotales();
                
                // Auto-seleccionar el primer semestre disponible sin delays conflictivos
                autoSeleccionarPrimerSemestreDisponible();

            } else {
                generarTablaVacia();
                calcularTotales();
            }
            
            ocultarOverlayCarga();
            
        } catch (error) {
            console.error('❌ Error al cargar datos existentes:', error);
            generarTablaVacia();
            ocultarOverlayCarga();
        }
    }

    // Función para procesar los estados de semáforo que vienen del SP
    function procesarEstadosSemaforoDelSP(rows) {
        // ✅ Siempre limpiar antes de procesar para que al cambiar de modalidad/programa
        // no queden estados residuales de la modalidad anterior.
        // Los semestres finalizados (estado 3) se preservan igual vía localStorage (estadosValidados).
        estadosSemaforoPorSemestre = {};

        if (!rows || rows.length === 0) {
            return;
        }
        
        // Cargar estados validados desde localStorage
        const estadosValidados = cargarEstadosValidadosDeLocalStorage();
        
        // **OBTENER PROGRAMA Y MODALIDAD ACTUALES PARA FILTRAR**
        const programaSelect = document.getElementById('programa');
        const modalidadSelect = document.getElementById('modalidad');
        
        // Obtener el NOMBRE del programa y modalidad seleccionados (porque el SP NO trae IDs)
        const programaNombreSeleccionado = programaSelect?.selectedOptions[0]?.text || null;
        const modalidadNombreSeleccionada = modalidadSelect?.selectedOptions[0]?.text || null;
        
        // Mapeo de semestres a números
        const semestreANumero = {
            'Primero': 1, 'Primer': 1, '1': 1, 'I': 1,
            'Segundo': 2, '2': 2, 'II': 2,
            'Tercero': 3, 'Tercer': 3, '3': 3, 'III': 3,
            'Cuarto': 4, '4': 4, 'IV': 4,
            'Quinto': 5, '5': 5, 'V': 5,
            'Sexto': 6, '6': 6, 'VI': 6,
            'Séptimo': 7, 'Septimo': 7, '7': 7, 'VII': 7,
            'Octavo': 8, '8': 8, 'VIII': 8,
            'Noveno': 9, '9': 9, 'IX': 9,
            'Décimo': 10, 'Decimo': 10, '10': 10, 'X': 10
        };
        
        // Extraer semestres únicos disponibles del SP (FILTRADOS POR PROGRAMA Y MODALIDAD)
        const semestresUnicos = new Set();
        let filasDescartadas = 0;
        let filasProcesadas = 0;
        
        // Procesar cada fila del SP
        rows.forEach((row, index) => {
            // **FILTRAR POR NOMBRE DE PROGRAMA Y MODALIDAD** (el SP NO trae IDs)
            const nombreProgramaRow = row.Nombre_Programa || null;
            const nombreModalidadRow = row.Modalidad || null;
            
            // DEBUG: Mostrar primeras 3 filas para diagnóstico
            if (index < 3) {
                // Primeras filas revisadas para diagnostico durante desarrollo.
            }
            
            // Solo procesar filas que coincidan con el programa y modalidad seleccionados
            if (programaNombreSeleccionado && normalizeLabel(nombreProgramaRow) !== normalizeLabel(programaNombreSeleccionado)) {
                filasDescartadas++;
                return; // Saltar esta fila
            }
            if (modalidadNombreSeleccionada && normalizeLabel(nombreModalidadRow) !== normalizeLabel(modalidadNombreSeleccionada)) {
                filasDescartadas++;
                return; // Saltar esta fila  
            }
            
            filasProcesadas++;
            
            const semestre = row.Semestre;
            const idSemaforo = row.Id_Semaforo;
            
            if (semestre && idSemaforo) {
                const semestreNum = semestreANumero[semestre] || parseInt(semestre) || null;
                
                if (semestreNum) {
                    // Agregar a la lista de semestres únicos
                    semestresUnicos.add(semestreNum);
                    
                    // Preservar semestres ya finalizados (estado 3) desde localStorage
                    if (estadosValidados[semestreNum] === 3) {
                        // Este semestre ya fue validado/finalizado, NO sobrescribir
                        estadosSemaforoPorSemestre[semestreNum] = 3;
                    } else {
                        // Usar directamente el estado que viene del SP para esta modalidad.
                        // Como el diccionario se limpió al inicio, no hay riesgo de residuos
                        // de otra modalidad. Si el SP devuelve varias filas por semestre
                        // (múltiples turnos), se queda con el valor más alto de esas filas.
                        const valorActual = estadosSemaforoPorSemestre[semestreNum] ?? 0;
                        if (idSemaforo > valorActual) {
                            estadosSemaforoPorSemestre[semestreNum] = idSemaforo;
                        }
                    }
                }
            }
        });
        
        // Actualizar variable global con semestres disponibles (ordenados)
        semestresDisponiblesSP = Array.from(semestresUnicos).sort((a, b) => a - b);
        
    }

    // ============================================================
    // Procesar y guardar TODOS los datos en memoria
    // ============================================================
    function procesarYGuardarDatosPorSemestre(rows) {
        if (!rows || rows.length === 0) {
            console.warn('⚠️ No hay rows para procesar');
            return;
        }
        
        // Limpiar estructura del contexto antes de procesar
        limpiarDatosContexto();
        // Estos datos provienen directamente del SP (estado base),
        // por lo que al procesarlos no debemos considerarlos como
        // "cambios locales" realizados por el usuario.
        hayCambiosLocalesPendientes = false;
        
        // Heurísticas para columnas posibles (igual que renderMatriculaFromSP)
        const tipoCandidates = ['Id_Tipo_Ingreso','Id_TipoIngreso','Tipo_Id','Tipo_de_Ingreso','TipoIngreso','Tipo_Ingreso','Tipo'];
        const grupoCandidates = ['Id_Grupo_Edad','Id_GrupoEdad','IdGrupoEdad','Grupo_Edad','GrupoEdad','Grupo'];
        const sexoCandidates = ['Id_Sexo','IdSexo','Sexo','Genero','Nombre_Sexo'];
        const matriculaCandidates = ['Matricula','Total','Cantidad','Numero','Valor'];
        const semestreCandidates = ['Semestre', 'Id_Semestre', 'IdSemestre', 'Nombre_Semestre'];
        const turnoCandidates = ['Turno','Nombre_Turno','Id_Turno','IdTurno'];
        const programaCandidates = ['Id_Programa', 'Nombre_Programa', 'Programa'];
        const modalidadCandidates = ['Id_Modalidad', 'Nombre_Modalidad', 'Modalidad'];
        
        // Determinar columnas presentes
        const first = rows[0] || {};
        const keys = Object.keys(first);
        
        function findKey(cands) {
            for (let c of cands) if (keys.includes(c)) return c;
            const low = keys.reduce((acc,k)=>{acc[k.toLowerCase()]=k;return acc;},{})
            for (let c of cands) if (low[c.toLowerCase()]) return low[c.toLowerCase()];
            return null;
        }
        
        const tipoKey = findKey(tipoCandidates);
        const grupoKey = findKey(grupoCandidates);
        const sexoKey = findKey(sexoCandidates);
        const matriculaKey = findKey(matriculaCandidates);
        const semestreKey = findKey(semestreCandidates);
        const turnoKey = findKey(turnoCandidates);
        const programaKey = findKey(programaCandidates);
        const modalidadKey = findKey(modalidadCandidates);
        
        if (!tipoKey || !grupoKey || !sexoKey || !matriculaKey || !semestreKey || !turnoKey) {
            console.error('❌ No se pudieron identificar todas las columnas necesarias');
            return;
        }
        
        let filasProcessadas = 0;
        let filasSaltadas = 0;
        
        const programaActualId = parseInt(document.getElementById('programa')?.value || '0');
        const programaActualNombre = document.getElementById('programa')?.selectedOptions[0]?.text || '';
        const modalidadActualId = parseInt(document.getElementById('modalidad')?.value || '0');
        const modalidadActualNombre = document.getElementById('modalidad')?.selectedOptions[0]?.text || '';

        rows.forEach((row, index) => {
            // Filtrar por programa/modalidad si las columnas existen
            if (programaKey && row[programaKey] !== undefined && row[programaKey] !== null) {
                const programaRowId = row.Id_Programa ? parseInt(row.Id_Programa) : null;
                const programaRowNombre = row.Nombre_Programa ? String(row.Nombre_Programa) : (row.Programa ? String(row.Programa) : String(row[programaKey]));
                const programaMatch = (programaRowId === programaActualId) ||
                    (normalizeLabel(programaRowNombre) === normalizeLabel(programaActualNombre));
                if (!programaMatch) {
                    return;
                }
            }

            if (modalidadKey && row[modalidadKey] !== undefined && row[modalidadKey] !== null) {
                const modalidadRowId = row.Id_Modalidad ? parseInt(row.Id_Modalidad) : null;
                const modalidadRowNombre = row.Nombre_Modalidad ? String(row.Nombre_Modalidad) : (row.Modalidad ? String(row.Modalidad) : String(row[modalidadKey]));
                const modalidadMatch = (modalidadRowId === modalidadActualId) ||
                    (normalizeLabel(modalidadRowNombre) === normalizeLabel(modalidadActualNombre));
                if (!modalidadMatch) {
                    return;
                }
            }

            // Extraer valores RAW del SP
            const tipoRaw = row[tipoKey];
            const grupoRaw = row[grupoKey];
            const sexoRaw = row[sexoKey];
            const valorRaw = row[matriculaKey];
            
            // ✨ NORMALIZAR tipo de ingreso a ID numérico
            let tipoId = tipoRaw;
            if (typeof tipoRaw === 'string') {
                const tipoLower = tipoRaw.toLowerCase();
                if (tipoLower.includes('nuevo')) {
                    tipoId = '1';
                } else if (tipoLower.includes('reingreso') || tipoLower.includes('re-ingreso')) {
                    tipoId = '2';
                } else if (tipoLower.includes('repet')) {
                    tipoId = '3';
                } else {
                    tipoId = tipoRaw; // Mantener original si no coincide
                }
            }
            
            // ✨ NORMALIZAR grupo de edad a ID (acepta nombre o valor numerico)
            let grupoId = grupoRaw;
            if (grupoRaw !== undefined && grupoRaw !== null) {
                const grupoStr = String(grupoRaw).trim();
                const grupoEncontrado = gruposEdad.find(g =>
                    String(g.Id_Grupo_Edad) === grupoStr ||
                    String(g.Grupo_Edad) === grupoStr ||
                    String(g.Grupo_Edad).toLowerCase() === grupoStr.toLowerCase()
                );
                if (grupoEncontrado) {
                    grupoId = String(grupoEncontrado.Id_Grupo_Edad);
                }
            }
            
            // ✨ NORMALIZAR sexo a M/F
            let sexoId = sexoRaw;
            if (typeof sexoRaw === 'string') {
                const sexoLower = sexoRaw.toLowerCase();
                if (sexoLower.includes('hombre') || sexoLower === 'h' || sexoLower === 'm' || sexoLower === 'masculino') {
                    sexoId = 'M';
                } else if (sexoLower.includes('mujer') || sexoLower === 'f' || sexoLower === 'femenino') {
                    sexoId = 'F';
                }
            } else if (typeof sexoRaw === 'number') {
                // Si es ID numérico: 1=M, 2=F (ajustar según tu BD)
                sexoId = sexoRaw === 1 ? 'M' : 'F';
            }
            
            // Extraer Semestre
            let semestreId = null;
            if (row[semestreKey] !== undefined && row[semestreKey] !== null) {
                semestreId = mapSemestreToId(row[semestreKey]);
            }
            
            // Extraer Turno
            let turnoId = null;
            if (row[turnoKey] !== undefined && row[turnoKey] !== null) {
                turnoId = mapTurnoToId(row[turnoKey]);
            }
            
            if (isNaN(semestreId) || isNaN(turnoId)) {
                filasSaltadas++;
                if (filasSaltadas <= 3) {
                    console.warn(`⚠️ Fila ${index} saltada - Semestre o Turno inválido:`, { semestreId, turnoId, row });
                }
                return; // Saltar esta fila
            }
            
            // Crear estructuras si no existen
            const datosContexto = obtenerDatosContexto(true);
            if (!datosContexto[turnoId]) {
                datosContexto[turnoId] = {};
            }
            if (!datosContexto[turnoId][semestreId]) {
                datosContexto[turnoId][semestreId] = {};
            }
            
            // Crear clave única para identificar la celda
            // Formato: tipoIngreso_grupoEdad_sexo (para coincidir con los data attributes)
            if (valorRaw !== undefined && valorRaw !== null && String(valorRaw).trim() !== '') {
                const vNum = parseInt(valorRaw);
                if (!isNaN(vNum)) {
                    const clave = `${tipoId}_${grupoId}_${sexoId}`;
                    datosContexto[turnoId][semestreId][clave] = vNum;
                    filasProcessadas++;
                }
            }
            
            // Log de las primeras 5 asignaciones
            if (filasProcessadas <= 5) {
                // Primeras asignaciones revisadas durante desarrollo.
            }
        });
    }
    
    // ============================================================
    // ✨ NUEVA: Renderizar solo el semestre actual desde memoria (todos los turnos)
    // ============================================================
    function renderizarSemestreDesdeMemoria(semestre) {
        const tbody = domCache.tbody || document.querySelector('#tabla-matricula tbody');
        if (!tbody) {
            console.error('❌ No se encontró tbody');
            return;
        }
        
        // Verificar si hay datos en memoria para este semestre
        const datosContexto = obtenerDatosContexto(false);
        const inputs = tbody.querySelectorAll('input[type="number"]');
        if (inputs.length === 0) {
            console.warn('⚠️ No hay inputs para renderizar desde memoria');
            return;
        }
        
        // Recorrer todas las celdas de input y llenarlas con los datos
        let cellsUpdated = 0;
        let cellsNotFound = 0;
        
        inputs.forEach((input, index) => {
            // Usar los data attributes correctos (tipoIngreso, grupoEdad, sexo)
            const tipoIngreso = input.getAttribute('data-tipo-ingreso');
            const grupoEdad = input.getAttribute('data-grupo-edad');
            const sexo = input.getAttribute('data-sexo');
            const turnoId = parseInt(input.getAttribute('data-turno'));
            
            if (!tipoIngreso || !grupoEdad || !sexo || isNaN(turnoId)) {
                console.warn(`⚠️ Input ${index} sin atributos completos:`, { tipoIngreso, grupoEdad, sexo, turnoId, id: input.id });
                return; // Saltar si no tiene los atributos necesarios
            }
            
            // Crear clave para buscar en memoria (mismo formato que al guardar)
            const clave = `${tipoIngreso}_${grupoEdad}_${sexo}`;
            const datosTurno = (datosContexto[turnoId] || {})[semestre] || {};
            
            if (datosTurno[clave] !== undefined) {
                input.value = datosTurno[clave];
                cellsUpdated++;
            } else {
                input.value = ''; // Limpiar si no hay dato
                cellsNotFound++;
            }
        });
        
        // Aplicar TODAS las restricciones después de renderizar
        setTimeout(() => {
            updateInputsBySemestre(semestre);
            aplicarTotalGruposParaSemestreYTurnoActual();
            aplicarBloqueoPorSemaforo();
            aplicarModoVista();
            calcularTotales();
        }, 50);
    }

    // Renderiza la tabla de captura a partir de rows devueltas por el SP con nueva estructura
    // rows: array de objetos; datosMap: mapa opcional para poblar valores
        async function renderMatriculaFromSP(rows, datosMap) {
            lastRowsSp = Array.isArray(rows) ? rows : [];
            if (typeof window !== 'undefined') {
                window.lastRowsSp = lastRowsSp;
            }
            
            // Ahora: volvemos a permitir que el SP alimente los
            // "Total Grupos" por turno, pero sólo para rellenar
            // los mapas internos (totalGruposPorSemestreYTurno y
            // totalGruposPorSemestre). La UI sigue usando esos
            // mapas como fuente única de verdad.
            
            // PRIMERO: Cargar estados validados guardados en localStorage
            cargarEstadosValidadosDeLocalStorage();
            
            // NUEVA LÓGICA: Extraer estados de semáforo del SP (ahora respeta los estados validados)
            // IMPORTANTE: Esto también actualiza semestresDisponiblesSP con los semestres únicos del SP
            procesarEstadosSemaforoDelSP(rows);
            
            // REGENERAR PESTAÑAS basadas en los semestres reales del SP
            if (semestresDisponiblesSP && semestresDisponiblesSP.length > 0) {
                console.log('🔄 Regenerando pestañas con semestres del SP:', semestresDisponiblesSP);
                
                // Obtener información del programa y periodo
                const programaSelect = document.getElementById('programa');
                const programaTexto = programaSelect ? programaSelect.selectedOptions[0]?.text : '';
                
                // Usar la variable global periodoLiteral del backend
                const periodoTexto = periodoLiteral || '';
                
                let semestresAMostrar = [...semestresDisponiblesSP];
                
                // Detectar si el periodo termina en /1 o /2
                const esPeriodo1 = periodoTexto.includes('/1');
                const esPeriodo2 = periodoTexto.includes('/2');
                
                console.log('📊 Contexto actual:');
                console.log('   Programa:', programaTexto);
                console.log('   Periodo:', periodoTexto);
                console.log('   Es periodo /1:', esPeriodo1);
                console.log('   Es periodo /2:', esPeriodo2);
                
                // Obtener modalidad actual
                const modalidadSelect = document.getElementById('modalidad');
                const modalidadId = modalidadSelect ? parseInt(modalidadSelect.value) : null;
                const modalidadTexto = modalidadSelect ? modalidadSelect.selectedOptions[0]?.text : '';
                
                console.log('   Modalidad ID:', modalidadId);
                console.log('   Modalidad Texto:', modalidadTexto);
                
                // LÓGICA 1: Tronco Común
                if (programaTexto && programaTexto.toLowerCase().includes('tronco común')) {
                    console.log('🎓 TRONCO COMÚN detectado');
                    
                    if (esPeriodo1) {
                        semestresAMostrar = [1]; // Solo Semestre 1 para periodo /1
                        console.log('   ✅ Periodo /1 → Mostrando SOLO Semestre 1');
                    } else if (esPeriodo2) {
                        semestresAMostrar = [2]; // Solo Semestre 2 para periodo /2
                        console.log('   ✅ Periodo /2 → Mostrando SOLO Semestre 2');
                    } else {
                        console.warn('   ⚠️ Periodo sin /1 ni /2, mostrando semestres disponibles del SP');
                    }
                }
                // LÓGICA 2: Técnico + Modalidad No Escolarizada (id=2) o Mixta (id=3)
                else if (programaTexto && (programaTexto.toLowerCase().includes('técnico') || programaTexto.toLowerCase().includes('tecnico')) 
                         && (modalidadId === 2 || modalidadId === 3)) {
                    console.log('🔧 TÉCNICO con Modalidad NO ESCOLARIZADA o MIXTA detectado');
                    console.log('   📚 Modalidad ID:', modalidadId, '(' + modalidadTexto + ')');
                    
                    // Para estas modalidades, mostrar TODOS los semestres del SP sin filtrar
                    // semestresAMostrar ya contiene todos los semestres del SP
                    console.log('   ✅ Mostrando TODOS los semestres del SP:', semestresAMostrar);
                }
                // LÓGICA 3: Técnico con Modalidad Escolarizada (id=1) u otra
                else if (programaTexto && (programaTexto.toLowerCase().includes('técnico') || programaTexto.toLowerCase().includes('tecnico'))) {
                    console.log('🔧 TÉCNICO con Modalidad ESCOLARIZADA (Medio Superior) detectado');
                    
                    // Eliminar semestres 1 y 2 (exclusivos de Tronco Común)
                    semestresAMostrar = semestresAMostrar.filter(sem => sem > 2);
                    console.log('   🚫 Removidos semestres 1 y 2:', semestresAMostrar);
                    
                    if (esPeriodo1) {
                        // Periodo /1: Solo semestres IMPARES (3, 5, 7, 9...)
                        semestresAMostrar = semestresAMostrar.filter(sem => sem % 2 !== 0);
                        console.log('   ✅ Periodo /1 → Mostrando solo IMPARES:', semestresAMostrar);
                    } else if (esPeriodo2) {
                        // Periodo /2: Solo semestres PARES (4, 6, 8, 10...)
                        semestresAMostrar = semestresAMostrar.filter(sem => sem % 2 === 0);
                        console.log('   ✅ Periodo /2 → Mostrando solo PARES:', semestresAMostrar);
                    } else {
                        console.warn('   ⚠️ Periodo sin /1 ni /2, mostrando todos (excepto 1 y 2)');
                    }
                }
                // LÓGICA 4: Otros programas (usar semestres del SP)
                else {
                    console.log('📚 Otro tipo de programa, usando semestres del SP sin filtrar');
                }
                
                console.log('🎯 Semestres finales a mostrar:', semestresAMostrar);
                
                // Validar que haya al menos un semestre para mostrar
                if (semestresAMostrar.length === 0) {
                    console.error('❌ No hay semestres disponibles después del filtrado!');
                    await Swal.fire({
                        icon: 'warning',
                        title: 'Sin semestres',
                        text: 'No hay semestres disponibles para este programa y periodo.',
                        confirmButtonText: 'Entendido'
                    });
                    return;
                }
                
                // Generar las pestañas
                generarPestanasSemestres(semestresAMostrar);
                
                // **IMPORTANTE**: Actualizar colores de las pestañas después de regenerarlas
                actualizarColoresPestanas();
                
                // Validar que el semestre actual esté en la lista de disponibles
                let semestreActualElement = document.getElementById('semestre');
                let semestreActualId = semestreActualElement ? parseInt(semestreActualElement.value) : null;
                
                // Si el semestre actual no está en los disponibles, seleccionar el primero
                if (!semestresAMostrar.includes(semestreActualId)) {
                    const primerSemestre = semestresAMostrar[0];
                    console.log(`⚠️ Semestre ${semestreActualId} no disponible. Cambiando a semestre ${primerSemestre}`);
                    semestreActualElement.value = primerSemestre;
                    
                    // Actualizar pestaña activa
                    const tabs = document.querySelectorAll('.semestre-tab');
                    tabs.forEach(tab => {
                        if (parseInt(tab.getAttribute('data-semestre')) === primerSemestre) {
                            tab.classList.add('active');
                        } else {
                            tab.classList.remove('active');
                        }
                    });
                }
            } else {
                console.warn('⚠️ No se extrajeron semestres del SP, usando configuración por defecto');
            }
            
            // ❌ NO PROCESAR DATOS AQUÍ - Se procesarán después del filtrado por programa/modalidad
            // procesarYGuardarDatosPorSemestre(rows); // DESHABILITADO: mezcla datos de todos los programas
            
            const tbody = document.getElementById('matricula-tbody');
            
            // Validar que el tbody exista
            if (!tbody) {
                console.error('❌ Error: No se encontró el elemento tbody con id "matricula-tbody"');
                return;
            }
            
            tbody.innerHTML = '';

            if (!rows || rows.length === 0) {
                console.log('⚠️ No hay rows para renderizar, generando tabla vacía');
                generarTablaVacia();
                return;
            }

            // Obtener el semestre actualmente seleccionado (reasignar variables ya declaradas)
            semestreActualElement = document.getElementById('semestre');
            semestreActualId = semestreActualElement ? parseInt(semestreActualElement.value) : null;
            
            // Obtener el nombre del semestre actual desde el mapa
            // Si semestresMap está vacío (roles 3-5 sin mapa del backend), construirlo desde semestresData
            const effectiveSemestresMap = Object.keys(semestresMap).length > 0
                ? semestresMap
                : (Array.isArray(semestresData) ? semestresData.reduce((acc, s) => { acc[s.Id_Semestre] = s.Semestre; return acc; }, {}) : {});
            const semestreActualNombre = semestreActualId ? effectiveSemestresMap[semestreActualId] : null;
            
            console.log(`📌 Semestre seleccionado: ID=${semestreActualId}, Nombre="${semestreActualNombre}" (Map keys: ${Object.keys(effectiveSemestresMap)})`);

            // Heurísticas para columnas posibles
            const tipoCandidates = ['Id_Tipo_Ingreso','Id_TipoIngreso','Tipo_Id','Tipo_de_Ingreso','TipoIngreso','Tipo_Ingreso','Tipo'];
            const grupoCandidates = ['Id_Grupo_Edad','Id_GrupoEdad','IdGrupoEdad','Grupo_Edad','GrupoEdad','Grupo'];
            const sexoCandidates = ['Id_Sexo','IdSexo','Sexo','Genero','Nombre_Sexo'];
            const matriculaCandidates = ['Matricula','Total','Cantidad','Numero','Valor'];
            const semestreCandidates = ['Semestre', 'Id_Semestre', 'IdSemestre'];
            const turnoCandidates = ['Turno','Nombre_Turno','Id_Turno','IdTurno'];
            const gruposCandidates = ['Grupos','Total_Grupos','Salones'];
            
            console.log('Columnas disponibles en la primera fila:', Object.keys(rows[0]));

            // Determinar columnas presentes
            const first = rows[0] || {};
            const keys = Object.keys(first);

            function findKey(cands) {
                for (let c of cands) if (keys.includes(c)) return c;
                const low = keys.reduce((acc,k)=>{acc[k.toLowerCase()]=k;return acc;},{})
                for (let c of cands) if (low[c.toLowerCase()]) return low[c.toLowerCase()];
                return null;
            }

            const tipoKey = findKey(tipoCandidates);
            const grupoKey = findKey(grupoCandidates);
            const sexoKey = findKey(sexoCandidates);
            const matriculaKey = findKey(matriculaCandidates);
            const semestreKey = findKey(semestreCandidates);
            const turnoKey = findKey(turnoCandidates);
            const gruposKey = findKey(gruposCandidates);

            // **OBTENER PROGRAMA Y MODALIDAD ACTUALES PARA FILTRAR**
            const programaActualId = parseInt(document.getElementById('programa')?.value || '0');
            const programaActualNombre = document.getElementById('programa')?.selectedOptions[0]?.text || '';
            const modalidadActualId = parseInt(document.getElementById('modalidad')?.value || '0');
            const modalidadActualNombre = document.getElementById('modalidad')?.selectedOptions[0]?.text || '';
            
            console.log(`📋 Filtros activos: Programa="${programaActualNombre}" (ID:${programaActualId}), Modalidad="${modalidadActualNombre}" (ID:${modalidadActualId}), Semestre="${semestreActualNombre}" (ID:${semestreActualId})`);
            
            // **DEBUG: Verificar si las columnas de filtrado existen en las rows**
            if (rows.length > 0) {
                const primeraFila = rows[0];
                console.log('🔍 Verificando columnas para filtrado de modalidad:');
                console.log('  - Id_Programa:', primeraFila.Id_Programa || 'NO EXISTE');
                console.log('  - Nombre_Programa:', primeraFila.Nombre_Programa || 'NO EXISTE');
                console.log('  - Id_Modalidad:', primeraFila.Id_Modalidad || 'NO EXISTE');
                console.log('  - Nombre_Modalidad:', primeraFila.Nombre_Modalidad || 'NO EXISTE');
                console.log('  - Modalidad:', primeraFila.Modalidad || 'NO EXISTE');
                console.log('📊 Todas las columnas disponibles:', Object.keys(primeraFila));
            }

            // FILTRAR: Solo procesar filas del programa, modalidad y semestre actual
            const rowsFiltradas = rows.filter(r => {
                // **Filtro por programa**
                if (r.Id_Programa || r.Nombre_Programa) {
                    const programaRowId = r.Id_Programa ? parseInt(r.Id_Programa) : null;
                    const programaRowNombre = r.Nombre_Programa ? String(r.Nombre_Programa) : '';
                    const programaMatch = (programaRowId === programaActualId) || 
                        (normalizeLabel(programaRowNombre) === normalizeLabel(programaActualNombre));
                    if (!programaMatch) {
                        return false;
                    }
                }
                
                // **Filtro por modalidad** - Probar diferentes nombres de columna
                const modalidadEnRow = r.Id_Modalidad || r.Nombre_Modalidad || r.Modalidad;
                if (modalidadEnRow !== undefined && modalidadEnRow !== null) {
                    const modalidadRowId = r.Id_Modalidad ? parseInt(r.Id_Modalidad) : null;
                    const modalidadRowNombre = r.Nombre_Modalidad ? String(r.Nombre_Modalidad) : (r.Modalidad ? String(r.Modalidad) : '');
                    const modalidadMatch = (modalidadRowId === modalidadActualId) || 
                        (normalizeLabel(modalidadRowNombre) === normalizeLabel(modalidadActualNombre));
                    if (!modalidadMatch) {
                        console.log(`  ❌ Fila rechazada por modalidad: Row tiene "${modalidadRowNombre}" (ID:${modalidadRowId}), esperado "${modalidadActualNombre}" (ID:${modalidadActualId})`);
                        return false;
                    }
                } else {
                    console.warn('⚠️ Fila sin información de modalidad, pasando filtro...');
                }
                
                // Filtro por semestre — usa el mismo mapa que procesarEstadosSemaforoDelSP
                // para garantizar consistencia sin depender de semestresMap/effectiveSemestresMap
                const semestreANumeroFiltro = {
                    'Primero': 1, 'Primer': 1, '1': 1, 'I': 1,
                    'Segundo': 2, '2': 2, 'II': 2,
                    'Tercero': 3, 'Tercer': 3, '3': 3, 'III': 3,
                    'Cuarto': 4, '4': 4, 'IV': 4,
                    'Quinto': 5, '5': 5, 'V': 5,
                    'Sexto': 6, '6': 6, 'VI': 6,
                    'S\u00e9ptimo': 7, 'Septimo': 7, '7': 7, 'VII': 7,
                    'Octavo': 8, '8': 8, 'VIII': 8,
                    'Noveno': 9, '9': 9, 'IX': 9,
                    'D\u00e9cimo': 10, 'Decimo': 10, '10': 10, 'X': 10
                };
                let semestreMatch = true;
                if (semestreKey && semestreActualId) {
                    const semestreRowVal = String(r[semestreKey] ?? '').trim();
                    // Convertir el valor del SP a número usando el mapa
                    const rowSemNum = semestreANumeroFiltro[semestreRowVal]
                        ?? parseInt(semestreRowVal)
                        ?? (r['Id_Semestre'] !== undefined ? parseInt(r['Id_Semestre']) : NaN);
                    semestreMatch = rowSemNum === semestreActualId;
                    if (!semestreMatch) return false;
                }

                return semestreMatch;
            });

            console.log(`🔍 Filtrando: ${rows.length} filas totales → ${rowsFiltradas.length} filas para Programa "${programaActualNombre}", Modalidad "${modalidadActualNombre}", Semestre "${semestreActualNombre}"`);

            if (rowsFiltradas.length === 0) {
                console.log('⚠️ No hay datos para el semestre seleccionado, generando tabla vacía');
                generarTablaVacia();
                return;
            }

            // === NUEVO: extraer Total de Grupos por TURNO desde el SP ===
            if (gruposKey && turnoKey && typeof mapTurnoToId === 'function') {
                const totalesTurno = {};
                rowsFiltradas.forEach(r => {
                    const turnoVal = r[turnoKey];
                    const turnoId = mapTurnoToId(turnoVal);
                    if (isNaN(turnoId)) return;
                    const gVal = r[gruposKey];
                    const num = parseInt(gVal);
                    if (isNaN(num) || num <= 0) return;
                    const clave = `${semestreActualId}_${turnoId}`;
                    if (totalesTurno[clave] === undefined || num > totalesTurno[clave]) {
                        totalesTurno[clave] = num;
                    }
                });

                // Volcar en los mapas globales y recalcular suma del semestre
                Object.keys(totalesTurno).forEach(clave => {
                    totalGruposPorSemestreYTurno[clave] = totalesTurno[clave];
                });
                if (typeof recalcularTotalGruposSemestre === 'function') {
                    recalcularTotalGruposSemestre(semestreActualId);
                }
                if (typeof guardarTotalGruposEnLocalStorage === 'function') {
                    guardarTotalGruposEnLocalStorage();
                }
            }

            // Determinar turnos visibles a partir de las filas filtradas
            const turnosMap = new Map();
            if (turnoKey) {
                rowsFiltradas.forEach(r => {
                    const turnoRaw = r[turnoKey];
                    const turnoId = mapTurnoToId(turnoRaw);
                    if (isNaN(turnoId)) return;
                    let turnoNombre = '';
                    const rawStr = String(turnoRaw || '').trim();
                    if (rawStr && isNaN(parseInt(rawStr))) {
                        turnoNombre = rawStr;
                    }
                    if (!turnoNombre && Array.isArray(turnosDisponibles)) {
                        const match = turnosDisponibles.find(t => parseInt(t.Id_Turno) === turnoId);
                        if (match) turnoNombre = match.Turno;
                    }
                    turnosMap.set(turnoId, { id: turnoId, nombre: turnoNombre || `Turno ${turnoId}` });
                });
            }
            if (turnosMap.size === 0 && Array.isArray(turnosDisponibles)) {
                turnosDisponibles.forEach(t => {
                    const turnoId = parseInt(t.Id_Turno);
                    if (!isNaN(turnoId)) {
                        turnosMap.set(turnoId, { id: turnoId, nombre: t.Turno });
                    }
                });
            }
            const turnosOrdenados = Array.from(turnosMap.values()).sort((a, b) => a.id - b.id);
            turnosVisibles = turnosOrdenados;

            const tiposIngresoVisibles = obtenerTiposIngresoPorSemestre(semestreActualId);
            const tiposIngresoVisiblesNombres = new Set(tiposIngresoVisibles.map(t => t.nombre));

            // Renderizar encabezado dinámico de la tabla
            renderizarEncabezadoTabla(semestreActualId, turnosOrdenados);

            // Construir estructura: agrupar por edad y tipo de ingreso
            const edadMap = {};
            
            console.log('🔍 Procesando rows del SP para poblar inputs...');
            
            rowsFiltradas.forEach((r, index) => {
                const tipoVal = tipoKey ? r[tipoKey] : (r['Tipo_de_Ingreso'] || r['Tipo'] || r['TipoIngreso'] || null);
                const grupoVal = grupoKey ? r[grupoKey] : (r['Grupo_Edad'] || r['Grupo'] || r['GrupoEdad'] || null);
                const sexoVal = sexoKey ? r[sexoKey] : (r['Sexo'] || r['Genero'] || null);
                const matriculaVal = matriculaKey ? r[matriculaKey] : (r['Matricula'] ?? r['Total'] ?? null);
                const turnoVal = turnoKey ? r[turnoKey] : (r['Turno'] || r['Nombre_Turno'] || r['Id_Turno'] || r['IdTurno'] || null);
                const turnoId = mapTurnoToId(turnoVal);

                console.log(`Row ${index + 1}:`, {
                    tipo: tipoVal,
                    grupo: grupoVal,
                    sexo: sexoVal,
                    matricula: matriculaVal,
                    turno: turnoVal
                });

                // Normalizar grupo de edad: si SP trae ID, convertir a etiqueta usando gruposEdad
                let grupoId = String(grupoVal || '');
                let grupoLabel = String(grupoVal || '');
                const geByLabel = gruposEdad.find(g => String(g.Grupo_Edad) === String(grupoVal));
                const geById = gruposEdad.find(g => String(g.Id_Grupo_Edad) === String(grupoVal));
                const ge = geByLabel || geById || null;
                if (ge) {
                    grupoId = String(ge.Grupo_Edad);
                    grupoLabel = String(ge.Grupo_Edad);
                }
                
                // Determinar sexo: Hombre/M → M, Mujer/F → F
                // Id_Sexo numérico: 1=Hombre, 2=Mujer
                let sexo = 'M';
                if (sexoVal !== undefined && sexoVal !== null) {
                    const sexoStr = String(sexoVal).toLowerCase().trim();
                    if (
                        sexoStr === '2' ||
                        sexoStr.includes('mujer') ||
                        sexoStr === 'f' ||
                        sexoStr.startsWith('f')
                    ) {
                        sexo = 'F';
                    }
                }
                
                // Normalizar tipo de ingreso y mapear a ID
                let tipoCategoria = 'Nuevo Ingreso';
                let tipoId = '1'; // Default
                
                if (tipoVal) {
                    const tipoNorm = String(tipoVal).toLowerCase();
                    if (tipoNorm.includes('nuevo')) {
                        tipoCategoria = 'Nuevo Ingreso';
                        tipoId = '1';
                    } else if (tipoNorm.includes('reingreso') || tipoNorm.includes('re-ingreso')) {
                        tipoCategoria = 'Reingreso';
                        tipoId = '2';
                    } else if (tipoNorm.includes('repet') || tipoNorm.includes('repetidor')) {
                        tipoCategoria = 'Repetidores';
                        tipoId = '3';
                    }
                }

                if (!tiposIngresoVisiblesNombres.has(tipoCategoria)) {
                    return;
                }

                if (isNaN(turnoId)) {
                    console.warn(`⚠️ Turno inválido en fila ${index + 1}:`, turnoVal);
                    return;
                }

                console.log(`✅ Procesando: Grupo=${grupoId}, Tipo=${tipoCategoria}(ID:${tipoId}), Sexo=${sexo}, Valor=${matriculaVal}`);

                // Inicializar estructura para este grupo de edad
                if (!edadMap[grupoId]) {
                    edadMap[grupoId] = { grupoLabel: grupoLabel };
                }
                if (!edadMap[grupoId][turnoId]) {
                    edadMap[grupoId][turnoId] = {};
                    tiposIngresoVisibles.forEach(tipo => {
                        edadMap[grupoId][turnoId][tipo.nombre] = { tipoId: tipo.id, M: undefined, F: undefined };
                    });
                }
                
                // Asignar el valor de matrícula SOLO si es numérico válido (incluye 0 explícito).
                // Si el SP devuelve NULL el parseInt dará NaN → no se asigna → input queda vacío.
                const vNum = parseInt(matriculaVal);
                if (!isNaN(vNum)) {
                    edadMap[grupoId][turnoId][tipoCategoria][sexo] = vNum;
                    console.log(`🎯 Asignado: ${tipoCategoria} ${sexo} = ${vNum} (grupo ${grupoId})`);
                } else {
                    console.log(`⚪ Sin valor numérico (NULL) para ${tipoCategoria} ${sexo} en grupo ${grupoId}`);
                }
            });

            console.log('📊 edadMap con datos del SP:', edadMap);
            console.log('🔑 Claves en edadMap:', Object.keys(edadMap));

            // Usar TODOS los grupos de edad definidos, no solo los que tienen datos
            if (!gruposEdad || gruposEdad.length === 0) {
                console.log('⚠️ No hay grupos de edad definidos');
                generarTablaVacia();
                return;
            }

            console.log('📊 Grupos de edad disponibles (sin ordenar):', gruposEdad.map(g => `${g.Grupo_Edad} (ID:${g.Id_Grupo_Edad})`));

            // Función para ordenar grupos de edad correctamente
            function ordenarGruposEdad(grupos) {
                // Crear una copia del array para no modificar el original
                const gruposCopia = [...grupos];
                
                return gruposCopia.sort((a, b) => {
                    const edadA = String(a.Grupo_Edad).trim();
                    const edadB = String(b.Grupo_Edad).trim();
                    
                    console.log(`🔄 Comparando: "${edadA}" vs "${edadB}"`);
                    
                    // Casos especiales: <18 va primero
                    if (edadA.startsWith('<') && !edadB.startsWith('<')) {
                        console.log(`  → "${edadA}" va primero (es <)`);
                        return -1;
                    }
                    if (!edadA.startsWith('<') && edadB.startsWith('<')) {
                        console.log(`  → "${edadB}" va primero (es <)`);
                        return 1;
                    }
                    
                    // Casos especiales: >=40 va al final
                    if ((edadA.startsWith('>') || edadA.includes('>=')) && !(edadB.startsWith('>') || edadB.includes('>='))) {
                        console.log(`  → "${edadA}" va al final (es >)`);
                        return 1;
                    }
                    if (!(edadA.startsWith('>') || edadA.includes('>=')) && (edadB.startsWith('>') || edadB.includes('>='))) {
                        console.log(`  → "${edadB}" va al final (es >)`);
                        return -1;
                    }
                    
                    // Para números o rangos, extraer el primer número
                    const getNumero = (str) => {
                        // Extraer el primer número encontrado
                        const match = str.match(/\d+/);
                        return match ? parseInt(match[0]) : 999;
                    };
                    
                    const numA = getNumero(edadA);
                    const numB = getNumero(edadB);
                    
                    console.log(`  → Números extraídos: ${numA} vs ${numB}`);
                    
                    return numA - numB;
                });
            }

            // Ordenar grupos de edad
            console.log('🔀 Iniciando ordenamiento...');
            const gruposEdadOrdenados = ordenarGruposEdad(gruposEdad);
            console.log('✅ Grupos de edad ordenados:', gruposEdadOrdenados.map(g => `${g.Grupo_Edad} (ID:${g.Id_Grupo_Edad})`));

            // Renderizar filas por TODOS los grupos de edad (no solo los que tienen datos)
            gruposEdadOrdenados.forEach((edadObj, index) => {
                const grupoIdBD = edadObj.Id_Grupo_Edad; // Este es el ID en la BD: 4, 5, 6, etc.
                const grupoValor = String(edadObj.Grupo_Edad); // Este es el valor real: "18", "19", etc.
                const grupoLabel = grupoValor;
                
                // Buscar si hay datos para este grupo de edad en el edadMap
                // El edadMap usa el VALOR como clave ("18"), no el ID
                const edadData = edadMap[grupoValor] || { grupoLabel: grupoLabel };
                
                // Log detallado para depuración
                if (edadMap[grupoValor]) {
                    console.log(`✅ Fila ${index}: Grupo "${grupoValor}" (ID:${grupoIdBD}) - Tiene datos:`, edadMap[grupoValor]);
                } else {
                    console.log(`⚪ Fila ${index}: Grupo "${grupoValor}" (ID:${grupoIdBD}) - Sin datos (vacío)`);
                }
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid #e0e0e0';
                tr.style.transition = 'all 0.2s ease';
                tr.onmouseover = () => tr.style.backgroundColor = '#f5f5f5';
                tr.onmouseout = () => tr.style.backgroundColor = '';

                // Columna de Edad (solo una vez)
                const tdEdad = document.createElement('td');
                tdEdad.textContent = edadData.grupoLabel || grupoValor;
                tdEdad.style.padding = '8px 5px';
                tdEdad.style.textAlign = 'center';
                tdEdad.style.fontWeight = '600';
                tdEdad.style.fontSize = '13px';
                tdEdad.style.color = '#424242';
                tdEdad.style.background = '#f8f9fa';
                tdEdad.style.verticalAlign = 'middle';
                // Ancho controlado por CSS, no inline
                tr.appendChild(tdEdad);

                // Columnas para cada turno y tipo de ingreso visible
                turnosOrdenados.forEach((turno, indexTurno) => {
                    const turnoData = edadData[turno.id] || {};
                    tiposIngresoVisibles.forEach((tipo, indexTipo) => {
                        const tdTipo = document.createElement('td');
                        tdTipo.style.padding = '8px 5px';
                        tdTipo.style.verticalAlign = 'middle';
                        // Ancho controlado por CSS
                        // Línea divisoria más gruesa al final de cada turno
                        if (indexTipo === tiposIngresoVisibles.length - 1) {
                            tdTipo.style.borderRight = '3px solid #b71c1c';
                        }
                        
                        const datos = turnoData[tipo.nombre] || { tipoId: tipo.id, M: undefined, F: undefined };
                        const tipoId = datos.tipoId || tipo.id;

                        // Obtener valores del SP (preservar cero explícito). Si el semestre está finalizado (3), mostrar 0 en ausentes
                        const estadoSem = estadosSemaforoPorSemestre[parseInt(semestreActualId)];
                        const mostrarCeroSiVacio = parseInt(estadoSem) === 3;
                        const valorM = (datos.M === undefined || datos.M === null || datos.M === '') 
                            ? (mostrarCeroSiVacio ? '0' : '') 
                            : String(datos.M);
                        const valorF = (datos.F === undefined || datos.F === null || datos.F === '') 
                            ? (mostrarCeroSiVacio ? '0' : '') 
                            : String(datos.F);
                        
                        tdTipo.innerHTML = `
                        <div style="display:inline-flex; gap:4px; justify-content:center; align-items:center; width:100%; max-width:100%;">
                            <div style="display:inline-flex; align-items:center; gap:2px; padding:1px 3px; background:#e3f2fd; border-radius:4px; border:1px solid #90caf9; line-height:1;">
                                <div style="font-weight:700;color:#1976d2;font-size:10px;min-width:12px;text-align:center;">H</div>
                                <input type="number" 
                                    id="input_${tipoId}_${grupoIdBD}_${turno.id}_M" 
                                    value="${valorM}" 
                                    min="0" 
                                    class="input-matricula-nueva" 
                                    data-tipo-ingreso="${tipoId}" 
                                    data-grupo-edad="${grupoIdBD}" 
                                    data-turno="${turno.id}"
                                    data-sexo="M" 
                                    style="width:34px;padding:1px 2px;border:2px solid #2196f3;border-radius:3px;background:#fff;color:#1976d2;font-weight:600;text-align:center;font-size:10px;line-height:1.1;" 
                                    placeholder="">
                            </div>

                            <div style="display:inline-flex; align-items:center; gap:2px; padding:1px 3px; background:#fce4ec; border-radius:4px; border:1px solid #f48fb1; line-height:1;">
                                <div style="font-weight:700;color:#c2185b;font-size:10px;min-width:12px;text-align:center;">M</div>
                                <input type="number" 
                                    id="input_${tipoId}_${grupoIdBD}_${turno.id}_F" 
                                    value="${valorF}" 
                                    min="0" 
                                    class="input-matricula-nueva" 
                                    data-tipo-ingreso="${tipoId}" 
                                    data-grupo-edad="${grupoIdBD}" 
                                    data-turno="${turno.id}"
                                    data-sexo="F" 
                                    style="width:34px;padding:1px 2px;border:2px solid #e91e63;border-radius:3px;background:#fff;color:#c2185b;font-weight:600;text-align:center;font-size:10px;line-height:1.1;" 
                                    placeholder="">
                            </div>
                        </div>`;

                        tr.appendChild(tdTipo);
                    });
                });

                tbody.appendChild(tr);
            });

        // La fila de totales se muestra ahora en un bloque fijo
        // debajo de la tabla (totales-matricula-fixed), por lo que
        // ya no se agrega una fila especial dentro del tbody.

        // Re-bind events for inputs
        const inputs = document.querySelectorAll('input.input-matricula-nueva');
        console.log(`🔗 [renderMatriculaFromSP] Vinculando eventos a ${inputs.length} inputs...`);
        inputs.forEach(input => {
            input.addEventListener('input', calcularTotales);
            input.addEventListener('change', calcularTotales);
            input.addEventListener('focus', scrollToVisibleInput);
            // Guardar datos automáticamente cuando cambie el valor
            input.addEventListener('input', guardarDatosSemestreActual);
            input.addEventListener('change', guardarDatosSemestreActual);
        });
        console.log(`✅ [renderMatriculaFromSP] Eventos vinculados a ${inputs.length} inputs`);

        // Si se pasó un datosMap, poblar valores
        if (datosMap) {
            for (let key in datosMap) {
                const val = datosMap[key];
                const parts = key.split('_');
                if (parts.length === 4) {
                    const idTipo = parts[0], idGrupo = parts[1], idTurno = parts[2], sexo = parts[3];
                    const el = document.getElementById(`input_${idTipo}_${idGrupo}_${idTurno}_${sexo}`);
                    if (el) el.value = val;
                }
            }
        }

        // Restaurar datos guardados del semestre actual después de renderizar
        // Solo cuando existan CAMBIOS LOCALES del usuario; si no, conservar
        // los valores que vienen directamente del SP.
        const semestreActualRestaurar = parseInt(document.getElementById('semestre').value);
        setTimeout(() => {
            if (hayCambiosLocalesPendientes) {
                const datosContexto = obtenerDatosContexto(false);
                const hayDatos = Object.keys(datosContexto || {}).some(turnoId => {
                    const datosTurno = (datosContexto[turnoId] || {})[semestreActualRestaurar] || {};
                    return Object.keys(datosTurno).length > 0;
                });
                if (hayDatos) {
                    console.log('📦 Hay cambios locales guardados, restaurando sobre datos del SP...');
                    restaurarDatosSemestre(semestreActualRestaurar);
                }
            } else {
                console.log('📊 Sin cambios locales: se conservan valores que vienen del SP');
                // Solo aplicar reglas de validación por semestre
                updateInputsBySemestre(semestreActualRestaurar);
                // ✨ CALCULAR totales ya que no se restaurarán datos
                calcularTotales();
            }
        }, 100); // Pequeño delay para asegurar que los inputs estén renderizados

    calcularTotales();
    // Cargar Total Grupos del semestre-turno y aplicar bloqueo si corresponde
    cargarTotalGruposDeLocalStorage();
    aplicarTotalGruposParaSemestreYTurnoActual();
    // Si el semestre actual ya fue finalizado (semaforo=3), bloquear edición
    aplicarBloqueoPorSemaforo();
    
    // NUEVO: Inicializar sistema de validación por turnos
    inicializarSistemaValidacionTurnos();
    
    // NUEVO: Aplicar modo de vista según el rol
    aplicarModoVista();
    }

    // ✨ VERSIÓN OPTIMIZADA: Menos búsquedas DOM, cálculo más eficiente
    function calcularTotales() {
        let totalMasculino = 0;
        let totalFemenino = 0;
        let totalGeneral = 0;
        
        // Usar cache si está disponible, sino buscar una vez
        const tbody = domCache.tbody || document.getElementById('matricula-tbody');
        if (!tbody) {
            console.warn('⚠️ calcularTotales: tbody no encontrado');
            return;
        }
        
        // Seleccionar solo inputs dentro del tbody (más eficiente)
        const inputs = tbody.querySelectorAll('input.input-matricula-nueva');
        console.log(`🔢 calcularTotales: ${inputs.length} inputs encontrados`);
        
        // Optimización: usar for loop en lugar de forEach (más rápido)
        for (let i = 0; i < inputs.length; i++) {
            const input = inputs[i];
            const valor = parseInt(input.value) || 0;
            const sexo = input.dataset.sexo; // Más rápido que getAttribute
            
            totalGeneral += valor;
            if (sexo === 'M') {
                totalMasculino += valor;
            } else if (sexo === 'F') {
                totalFemenino += valor;
            }
        }
        
        console.log(`📊 Totales calculados: M=${totalMasculino}, F=${totalFemenino}, Total=${totalGeneral}`);
        
        // Buscar elementos de totales (con fallback si el cache no está listo)
        const totalMasculinoEl = domCache.totalMasculino || document.querySelector('#total_masculino');
        const totalFemeninoEl = domCache.totalFemenino || document.querySelector('#total_femenino');
        const totalGeneralEl = domCache.totalGeneral || document.querySelector('#total_general');
        
        // Actualizar si los elementos existen
        if (totalMasculinoEl) {
            totalMasculinoEl.textContent = totalMasculino;
        } else {
            console.warn('⚠️ Elemento total_masculino no encontrado');
        }
        
        if (totalFemeninoEl) {
            totalFemeninoEl.textContent = totalFemenino;
        } else {
            console.warn('⚠️ Elemento total_femenino no encontrado');
        }
        
        if (totalGeneralEl) {
            totalGeneralEl.textContent = totalGeneral;
        } else {
            console.warn('⚠️ Elemento total_general no encontrado');
        }
        
        // Actualizar colores del semáforo en las pestañas
        if (typeof actualizarColoresPestanas === 'function') {
            actualizarColoresPestanas();
        }
        actualizarInforme();
    }

    // Sincronizar el ancho de la celda "TOTALES" fija
    function sincronizarAnchoCeldaTotales() {
        try {
            const tabla = document.querySelector('.tabla-matricula-completa');
            const celdaEdad = tabla?.querySelector('tbody tr td:first-child') || tabla?.querySelector('thead tr th:first-child');
            const celdaTotales = document.getElementById('totales-label-cell');
            if (!tabla || !celdaEdad || !celdaTotales) return;

            const width = celdaEdad.getBoundingClientRect().width;
            if (!width || isNaN(width)) return;

            celdaTotales.style.width = width + 'px';
            celdaTotales.style.minWidth = width + 'px';
            celdaTotales.style.maxWidth = width + 'px';
        } catch (e) {
            console.warn('No se pudo sincronizar ancho de celda TOTALES', e);
        }
    }
    
    // ✨ VERSIÓN CON DEBOUNCING para eventos input (evita cálculos excesivos)
    const calcularTotalesDebounced = debounce(calcularTotales, 150);

    // Función para generar tabla vacía con estructura basada en grupos de edad del backend
    function generarTablaVacia(resetSemaforo = true) {
        // Limpiar estados de semáforo solo si se solicita
        if (resetSemaforo) {
            estadosSemaforoPorSemestre = {};
            console.log('🚦 Estados de semáforo limpiados (tabla vacía)');
        }
        
        const tbody = document.getElementById('matricula-tbody');
        
        // Validar que el tbody exista antes de intentar acceder a él
        if (!tbody) {
            console.error('❌ Error: No se encontró el elemento tbody con id "matricula-tbody"');
            return;
        }
        
        tbody.innerHTML = '';
        
        // Usar grupos de edad globales del backend
        console.log('Grupos de edad desde backend para tabla vacía:', gruposEdad);
        
        // Si no hay grupos de edad del backend, usar valores por defecto
        let edadesParaUsar = [];
        if (gruposEdad && gruposEdad.length > 0) {
            const gruposOrdenados = [...gruposEdad].sort((a, b) => {
                const aId = parseInt(a.Id_Grupo_Edad, 10);
                const bId = parseInt(b.Id_Grupo_Edad, 10);
                if (isNaN(aId) || isNaN(bId)) {
                    return String(a.Grupo_Edad).localeCompare(String(b.Grupo_Edad));
                }
                return aId - bId;
            });
            edadesParaUsar = gruposOrdenados.map(g => ({
                id: g.Id_Grupo_Edad,
                label: g.Grupo_Edad
            }));
        } else {
            // Fallback: edades por defecto
            const edadesDefault = [
                '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', 'Más de 25'
            ];
            edadesParaUsar = edadesDefault.map((edad, idx) => ({
                id: idx + 1,
                label: edad
            }));
        }
        
        let semestreActual = parseInt(document.getElementById('semestre')?.value || '1');
        const tiposIngresoVisibles = obtenerTiposIngresoPorSemestre(semestreActual);
        let turnosOrdenados = [];
        if (Array.isArray(turnosVisibles) && turnosVisibles.length > 0) {
            turnosOrdenados = turnosVisibles
                .map(t => ({ id: parseInt(t.id), nombre: t.nombre }))
                .filter(t => !isNaN(t.id));
        } else if (Array.isArray(turnosDisponibles) && turnosDisponibles.length > 0) {
            turnosOrdenados = turnosDisponibles
                .map(t => ({ id: parseInt(t.Id_Turno), nombre: t.Turno }))
                .filter(t => !isNaN(t.id));
        }
        if (turnosOrdenados.length === 0) {
            turnosOrdenados = [{ id: 0, nombre: 'Turno' }];
        }
        turnosVisibles = turnosOrdenados;
        renderizarEncabezadoTabla(semestreActual, turnosOrdenados);
        
        edadesParaUsar.forEach((edadObj, idxEdad) => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #e0e0e0';
            tr.style.transition = 'all 0.2s ease';
            tr.onmouseover = () => tr.style.backgroundColor = '#f5f5f5';
            tr.onmouseout = () => tr.style.backgroundColor = '';
            
            // Columna de Edad
            const tdEdad = document.createElement('td');
            tdEdad.textContent = edadObj.label;
            tdEdad.style.padding = '8px 5px';
            tdEdad.style.textAlign = 'center';
            tdEdad.style.fontWeight = '600';
            tdEdad.style.fontSize = '13px';
            tdEdad.style.color = '#424242';
            tdEdad.style.background = '#f8f9fa';
            tdEdad.style.verticalAlign = 'middle';
            // Ancho controlado por CSS, no inline
            tr.appendChild(tdEdad);
            
            // Columnas para cada turno y tipo de ingreso visible
            turnosOrdenados.forEach((turno, indexTurno) => {
                tiposIngresoVisibles.forEach((tipo, indexTipo) => {
                    const tdTipo = document.createElement('td');
                    tdTipo.style.padding = '8px 5px';
                    tdTipo.style.verticalAlign = 'middle';
                    // Ancho controlado por CSS
                    // Línea divisoria más gruesa al final de cada turno
                    if (indexTipo === tiposIngresoVisibles.length - 1) {
                        tdTipo.style.borderRight = '3px solid #b71c1c';
                    }
                    
                    tdTipo.innerHTML = `
                    <div style="display:inline-flex; gap:4px; justify-content:center; align-items:center; width:100%; max-width:100%; /* Contenedor general */">
                        
                        <div style="display:inline-flex; align-items:center; gap:2px; padding:1px 3px; background:#e3f2fd; border-radius:4px; border:1px solid #90caf9; line-height:1;">
                            <div style="font-weight:700;color:#1976d2;font-size:10px;min-width:12px;text-align:center;">H</div>
                            <input type="number" 
                                id="input_${tipo.id}_${edadObj.id}_${turno.id}_M" 
                                value="" 
                                min="0" 
                                class="input-matricula-nueva" 
                                data-tipo-ingreso="${tipo.id}" 
                                data-grupo-edad="${edadObj.id}" 
                                data-turno="${turno.id}"
                                data-sexo="M" 
                                oninput="this.value = this.value.replace(/[^0-9]/g, '')"
                                style="width:34px;padding:1px 2px;border:2px solid #2196f3;border-radius:3px;background:#fff;color:#1976d2;font-weight:600;text-align:center;font-size:10px;line-height:1.1;" 
                                placeholder="">
                        </div>

                        <div style="display:inline-flex; align-items:center; gap:2px; padding:1px 3px; background:#fce4ec; border-radius:4px; border:1px solid #f48fb1; line-height:1;">
                            <div style="font-weight:700;color:#c2185b;font-size:10px;min-width:12px;text-align:center;">M</div>
                            <input type="number" 
                                id="input_${tipo.id}_${edadObj.id}_${turno.id}_F" 
                                value="" 
                                min="0" 
                                class="input-matricula-nueva" 
                                data-tipo-ingreso="${tipo.id}" 
                                data-grupo-edad="${edadObj.id}" 
                                data-turno="${turno.id}"
                                data-sexo="F" 
                                oninput="this.value = this.value.replace(/[^0-9]/g, '')"
                                style="width:34px;padding:1px 2px;border:2px solid #e91e63;border-radius:3px;background:#fff;color:#c2185b;font-weight:600;text-align:center;font-size:10px;line-height:1.1;" 
                                placeholder="">
                        </div>
                    </div>`;
                
                tr.appendChild(tdTipo);
            });
        });
        
        tbody.appendChild(tr);
    });
        
        // La fila de totales se muestra ahora en un bloque fijo
        // debajo de la tabla (totales-matricula-fixed), por lo que
        // ya no se agrega una fila especial dentro del tbody.
        
        // Re-bind events for inputs
        const inputs = document.querySelectorAll('input.input-matricula-nueva');
        console.log(`🔗 [generarTablaVacia] Vinculando eventos a ${inputs.length} inputs...`);
        inputs.forEach(input => {
            input.addEventListener('input', calcularTotales);
            input.addEventListener('change', calcularTotales);
            input.addEventListener('focus', scrollToVisibleInput);
            // Guardar datos automáticamente cuando cambie el valor
            input.addEventListener('input', guardarDatosSemestreActual);
            input.addEventListener('change', guardarDatosSemestreActual);
        });
        console.log(`✅ [generarTablaVacia] Eventos vinculados a ${inputs.length} inputs`);

        // Restaurar datos guardados del semestre actual después de renderizar
        // NOTA: Solo restaurar si hay datos guardados localmente
        semestreActual = parseInt(document.getElementById('semestre').value);
        setTimeout(() => {
            const datosContexto = obtenerDatosContexto(false);
            const hayDatos = Object.keys(datosContexto || {}).some(turnoId => {
                const datosTurno = (datosContexto[turnoId] || {})[semestreActual] || {};
                return Object.keys(datosTurno).length > 0;
            });
            if (hayDatos) {
                console.log('📦 Hay datos guardados localmente (tabla vacía), restaurando...');
                restaurarDatosSemestre(semestreActual);
            } else {
                console.log('📊 No hay datos guardados (tabla vacía), tabla queda vacía');
                // Solo aplicar reglas de validación por semestre
                updateInputsBySemestre(semestreActual);
            }
        }, 100); // Pequeño delay para asegurar que los inputs estén renderizados
        
        calcularTotales();
        // Alinear ancho de la celda TOTALES con la columna de Edad
        setTimeout(sincronizarAnchoCeldaTotales, 0);
    }

    // Control de acceso: por defecto, acceso no restringido a menos que el backend defina lo contrario
    var accesoRestringido = typeof accesoRestringido !== 'undefined' ? accesoRestringido : false;

    // Variables globales para manejo de turnos
    let turnosVisibles = [];
    let turnoActualIndex = 0;

    // Variables globales para semáforo de semestres
    console.log('🚦 Estados del semáforo cargados:', semaforoEstados);

    // Almacén global de datos por semestre y turno, separado por contexto
    // Estructura: { [contextKey]: { [turnoId]: { [semestreId]: { "tipo_grupo_sexo": valor } } } }
    let datosMatriculaPorSemestre = {};
    // Bandera para saber si hay cambios locales (captura en UI) pendientes
    // de aplicar sobre los datos que vienen del SP.
    let hayCambiosLocalesPendientes = false;
    // Bandera para saber si ya se realizó el primer render completo
    let primerRenderCompleto = false;

    function obtenerClaveContextoDatos() {
        const periodo = document.getElementById('periodo')?.value || '';
        const programa = document.getElementById('programa')?.value || '';
        const modalidad = document.getElementById('modalidad')?.value || '';
        return `${periodo}_${programa}_${modalidad}`;
    }

    function obtenerDatosContexto(crear = false) {
        const key = obtenerClaveContextoDatos();
        if (!key) return {};
        if (crear && !datosMatriculaPorSemestre[key]) {
            datosMatriculaPorSemestre[key] = {};
        }
        return datosMatriculaPorSemestre[key] || {};
    }

    function limpiarDatosContexto() {
        const key = obtenerClaveContextoDatos();
        if (!key) return;
        datosMatriculaPorSemestre[key] = {};
        // Al limpiar el contexto, asumimos que no hay cambios locales pendientes
        hayCambiosLocalesPendientes = false;
    }

    // Almacén de estados de semáforo por semestre (viene del SP)
    let estadosSemaforoPorSemestre = {};
    
    // Almacén de semestres disponibles extraídos del SP (dinámico por nivel educativo)
    let semestresDisponiblesSP = [];
    
    // ✨ BANDERA DE OPTIMIZACIÓN: Indica si los datos completos ya se cargaron del backend
    let datosCompletosYaCargados = false;
    let ultimoContextoCarga = '';

    // ============================================
    // FUNCIONES PARA PERSISTENCIA DE SEMÁFOROS
    // ============================================
    
    /**
     * Genera una clave única para localStorage basada en los filtros actuales
     * Formato: "semaforo_periodoId_programaId_modalidadId_turnoId"
     */
    function generarClaveLocalStorage() {
        const periodo = document.getElementById('periodo').value;
        const programa = document.getElementById('programa').value;
        const modalidad = document.getElementById('modalidad').value;
        const turno = document.getElementById('turno').value;
        
        return `semaforo_${periodo}_${programa}_${modalidad}_${turno}`;
    }
    
    /**
     * Guarda los estados validados (estado 3) en localStorage
     */
    function guardarEstadosValidadosEnLocalStorage() {
        const clave = generarClaveLocalStorage();
        
        // Filtrar solo los semestres con estado 3 (validados)
        const estadosValidados = {};
        for (let semestre in estadosSemaforoPorSemestre) {
            if (estadosSemaforoPorSemestre[semestre] === 3) {
                estadosValidados[semestre] = 3;
            }
        }
        
        try {
            localStorage.setItem(clave, JSON.stringify(estadosValidados));
            console.log(`💾 Estados validados guardados en localStorage:`, estadosValidados);
        } catch (e) {
            console.error('❌ Error al guardar en localStorage:', e);
        }
    }
    
    /**
     * Carga los estados validados desde localStorage
     */
    function cargarEstadosValidadosDeLocalStorage() {
        const clave = generarClaveLocalStorage();
        
        try {
            const datos = localStorage.getItem(clave);
            if (datos) {
                const estadosValidados = JSON.parse(datos);
                console.log(`📂 Estados validados cargados desde localStorage:`, estadosValidados);
                return estadosValidados;
            }
        } catch (e) {
            console.error('❌ Error al cargar desde localStorage:', e);
        }
        
        return {}; // Retornar objeto vacío si no hay datos
    }
    
    /**
     * Marca un semestre como validado (estado 3) y lo persiste
     */
    function marcarSemestreComoValidado(semestreNum) {
        console.log(`✅ Marcando semestre ${semestreNum} como validado (estado 3)`);
        
        // Actualizar en memoria
        estadosSemaforoPorSemestre[semestreNum] = 3;
        
        // Persistir en localStorage
        guardarEstadosValidadosEnLocalStorage();
        
        // Actualizar UI
        actualizarColoresPestanas();
    }

    // Función para cambiar turno
    function cambiarTurno(direccion) {
        console.log(`🔄 Cambiando turno (dirección: ${direccion > 0 ? 'siguiente' : 'anterior'})...`);
        
        // Guardar datos del contexto actual antes de cambiar turno
        try { guardarDatosSemestreActual(); } catch (e) { console.warn('No se pudo guardar antes de cambiar turno', e); }
        turnoActualIndex += direccion;
        
        // Validar límites
        if (turnoActualIndex < 0) turnoActualIndex = 0;
        if (turnoActualIndex >= turnosDisponibles.length) turnoActualIndex = turnosDisponibles.length - 1;
        
        // Actualizar UI (si existe)
        const turnoActual = turnosDisponibles[turnoActualIndex];
        const turnoNombreEl = document.getElementById('turno-nombre');
        const turnoInputEl = document.getElementById('turno');
        const btnAnterior = document.getElementById('btn-turno-anterior');
        const btnSiguiente = document.getElementById('btn-turno-siguiente');
        if (turnoNombreEl) turnoNombreEl.textContent = turnoActual.Turno;
        if (turnoInputEl) turnoInputEl.value = turnoActual.Id_Turno;
        if (btnAnterior) btnAnterior.disabled = turnoActualIndex === 0;
        if (btnSiguiente) btnSiguiente.disabled = turnoActualIndex === turnosDisponibles.length - 1;
        
        // ✨ OPTIMIZACIÓN MÁXIMA: Renderizar SIEMPRE desde memoria
        // Los datos completos ya se cargaron UNA VEZ al inicio (todos los semestres y turnos)
        let semestreActual = parseInt(document.getElementById('semestre').value);
        const turnoActualId = parseInt(turnoActual.Id_Turno);
        
        if (datosCompletosYaCargados) {
            // ✅ Renderizar desde memoria (datos ya están cargados)
            console.log(`📦 Renderizando turno ${turnoActual.Turno} desde memoria (sin backend)`);
            renderizarSemestreDesdeMemoria(semestreActual);
            
            setTimeout(() => {
                cargarTotalGruposDeLocalStorage();
                aplicarTotalGruposParaSemestreYTurnoActual();
                aplicarModoVista();
            }, 50);
        } else {
            // ⚠️ Primera carga: llamar al SP para traer TODOS los datos
            console.log(`🌐 Primera carga - Ejecutando SP para traer TODOS los datos...`);
            cargarDatosExistentes();
            
            setTimeout(() => {
                cargarTotalGruposDeLocalStorage();
                aplicarTotalGruposParaSemestreYTurnoActual();
                aplicarModoVista();
            }, 100);
        }
    }

    // Escuchar cambios de Programa/Modalidad para refrescar datos y estado de inputs
    document.addEventListener('DOMContentLoaded', () => {
        // Si el acceso está restringido, no ejecutar nada
        if (accesoRestringido) {
            console.log('🔒 Acceso restringido - No se inicializarán event listeners');
            return;
        }
        
        const selPrograma = document.getElementById('programa');
        const selModalidad = document.getElementById('modalidad');
        function onFiltroChange() {
            // Limpiar semáforo previo y deshabilitado visual
            estadosSemaforoPorSemestre = {};
            // Reiniciar cache para el nuevo contexto, pero SIN volver a ejecutar el SP
            datosCompletosYaCargados = false;
            limpiarDatosContexto();
            console.log('🔄 Cambio de filtros: limpiando estados y cache local (sin ejecutar SP)');
            // Forzar semestre a 1 al cambiar filtros para evitar mismatch
            const semEl = document.getElementById('semestre');
            if (semEl) semEl.value = '1';
            // Quitar deshabilitado visual si es capturista
            if (esCapturista) {
                const inputs = document.querySelectorAll('input.input-matricula-nueva');
                inputs.forEach(i => { i.disabled = false; i.classList.remove('input-disabled'); i.title=''; });
                const tgTurnos = document.querySelectorAll('.input-total-grupos-turno');
                tgTurnos.forEach(tg => { tg.disabled = false; tg.classList.remove('input-disabled'); tg.title=''; });
            }
            // Generar tabla vacía para el nuevo contexto
            generarTablaVacia();

            // ♻️ Reutilizar las filas ya obtenidas del SP (lastRowsSp/rowsInicialesSp)
            // para el nuevo programa/modalidad, evitando ejecutar nuevamente el SP
            // en cada cambio de filtro. Solo si no hay cache se recurre al backend.
            if (Array.isArray(lastRowsSp) && lastRowsSp.length > 0) {
                console.log('♻️ Reutilizando lastRowsSp del SP inicial para nuevo programa/modalidad (sin nueva llamada al SP)');

                // Reconstruir en memoria la matrícula (por semestre/turno) para
                // el programa y modalidad actualmente seleccionados, usando las
                // filas ya obtenidas del SP.
                if (typeof procesarYGuardarDatosPorSemestre === 'function') {
                    try {
                        procesarYGuardarDatosPorSemestre(lastRowsSp);
                    } catch (e) {
                        console.warn('⚠️ No se pudo procesar datos por semestre desde lastRowsSp al cambiar filtros', e);
                    }
                }

                // Recalcular mapas de Total Grupos solo para el programa/modalidad actuales
                if (typeof procesarTotalGruposDesdeSP === 'function') {
                    try {
                        procesarTotalGruposDesdeSP(lastRowsSp);
                    } catch (e) {
                        console.warn('⚠️ No se pudo reprocesar Total Grupos desde lastRowsSp al cambiar filtros', e);
                    }
                }

                if (typeof renderMatriculaFromSP === 'function') {
                    (async () => {
                        await renderMatriculaFromSP(lastRowsSp, {});
                        datosCompletosYaCargados = true;
                        autoSeleccionarPrimerSemestreDisponible(); // Llamada directa
                    })();
                } else {
                    console.error('❌ Función renderMatriculaFromSP no disponible al cambiar filtros');
                }
            } else {
                console.log('ℹ️ No hay lastRowsSp en memoria; usando cargarDatosExistentes() como respaldo');
                try {
                    // CargarDatosExistentes ahora maneja su propia auto-selección de forma limpia
                    cargarDatosExistentes(); 
                } catch (e) {
                    console.error('❌ Error al recargar datos desde el backend después de cambiar filtros:', e);
                }
            }

            setTimeout(() => {
                aplicarTotalGruposParaSemestreYTurnoActual();
                aplicarBloqueoPorSemaforo();
                aplicarModoVista();
                calcularTotales();
            }, 150);
        }
        if (selPrograma) {
            selPrograma.addEventListener('change', () => {
                // Actualizar primero las modalidades válidas para el programa
                filtrarModalidadesPorPrograma();
                actualizarVisibilidadCapturaSegunFiltros();

                // Sólo refrescar datos cuando también haya modalidad seleccionada
                if (selModalidad && selPrograma.value && selModalidad.value) {
                    onFiltroChange();
                } else {
                    // Si falta modalidad, limpiar vista para evitar información errónea
                    generarTablaVacia();
                    calcularTotales();
                }
            });
        }
        if (selModalidad) {
            selModalidad.addEventListener('change', () => {
                actualizarVisibilidadCapturaSegunFiltros();
                if (selPrograma && selPrograma.value && selModalidad.value) {
                    onFiltroChange();
                }
            });
        }

        // Estado inicial del combo de modalidad y visibilidad de captura
        if (selPrograma && !selPrograma.value) {
            if (selModalidad) {
                selModalidad.innerHTML = '<option value="">-- Primero seleccione un Programa --</option>';
                selModalidad.disabled = true;
            }
        } else if (selPrograma) {
            // Si ya hay un programa seleccionado al cargar, filtrar modalidades de inmediato
            filtrarModalidadesPorPrograma();
        }

        actualizarVisibilidadCapturaSegunFiltros();
    });

    // Función para determinar el estado de progreso de un semestre
    function determinarEstadoSemestre(semestreNum) {
        // Buscar el estado del semáforo que viene del SP para este semestre
        const estadoDelSP = estadosSemaforoPorSemestre[semestreNum];
        
        if (estadoDelSP) {
            console.log(`🚦 Semestre ${semestreNum}: Estado del SP = ${estadoDelSP}`);
            return estadoDelSP;
        }
        
        // Si no hay estado del SP, usar estado por defecto (sin datos)
        console.warn(`⚠️ Semestre ${semestreNum}: Sin estado del SP, usando estado por defecto (1 - ROJO)`);
        console.log(`📊 Estados disponibles en estadosSemaforoPorSemestre:`, Object.keys(estadosSemaforoPorSemestre));
        return 1; // Estado por defecto - Sin datos
    }

    function obtenerSemestresDisponibles() {
        const tabs = Array.from(document.querySelectorAll('.semestre-tab'));
        if (tabs.length > 0) {
            return tabs
                .map(tab => parseInt(tab.getAttribute('data-semestre')))
                .filter(n => !isNaN(n))
                .sort((a, b) => a - b);
        }
        if (Array.isArray(semestresDisponiblesSP) && semestresDisponiblesSP.length > 0) {
            return [...semestresDisponiblesSP].sort((a, b) => a - b);
        }
        if (Array.isArray(semestresData) && semestresData.length > 0) {
            return semestresData
                .map(s => parseInt(s.Id_Semestre ?? s.Semestre ?? s))
                .filter(n => !isNaN(n))
                .sort((a, b) => a - b);
        }
        return [1];
    }


    // ✅ Auto-selección robusta del primer semestre REAL (solo 1 vez por contexto Programa+Modalidad+Periodo)
    // Evita el bug donde la tabla queda vacía hasta que el usuario hace clic manual en una pestaña.
    let __autoSemestreKeyApplied = null;

    function autoSeleccionarPrimerSemestreDisponible() {
        try {
            const periodo = document.getElementById('periodo')?.value || '';
            const programa = document.getElementById('programa')?.value || '';
            const modalidad = document.getElementById('modalidad')?.value || '';
            const key = `${periodo}||${programa}||${modalidad}`;

            // Solo auto-seleccionar cuando ya hay filtros completos
            if (!periodo || !programa || !modalidad) return;

            // Evitar loops: solo una vez por este contexto
            if (__autoSemestreKeyApplied === key) return;

            // Debe existir el cache de filas para poder renderizar
            if (!Array.isArray(lastRowsSp) || lastRowsSp.length === 0) {
                console.warn('⚠️ Auto-selección: lastRowsSp vacío; no se puede forzar render del primer semestre');
                return;
            }

            // Tomar el primer semestre existente en las pestañas (fuente de verdad del frontend)
            const semestres = (typeof obtenerSemestresDisponibles === 'function')
                ? obtenerSemestresDisponibles()
                : Array.from(document.querySelectorAll('.semestre-tab'))
                    .map(t => parseInt(t.getAttribute('data-semestre')))
                    .filter(n => !isNaN(n));

            if (!Array.isArray(semestres) || semestres.length === 0) {
                console.warn('⚠️ Auto-selección: no se detectaron semestres disponibles');
                return;
            }

            // Orden académico numérico
            const ordenados = [...semestres].sort((a, b) => a - b);
            const primerSemestre = ordenados[0];

            console.log(`✨ Auto-selección: forzando render del primer semestre disponible: ${primerSemestre}`);

            // Marcar aplicado ANTES para evitar recursión si renderMatriculaFromSP vuelve a disparar hooks
            __autoSemestreKeyApplied = key;

            // Forzar selección (más confiable que .click() si hay preventDefault/capas)
            if (typeof seleccionarSemestre === 'function') {
                seleccionarSemestre(primerSemestre);
            } else {
                // fallback a click
                const tab = document.querySelector(`.semestre-tab[data-semestre="${primerSemestre}"]`);
                if (tab) tab.click();
            }
        } catch (e) {
            console.error('❌ Error en autoSeleccionarPrimerSemestreDisponible:', e);
        }
    }


    function actualizarEstadoBotonesSemestre() {
        const semestres = obtenerSemestresDisponibles();
        const actual = parseInt(document.getElementById('semestre')?.value || '1');
        const idx = semestres.indexOf(actual);
        const btnAnterior = document.getElementById('btn-turno-anterior');
        const btnSiguiente = document.getElementById('btn-turno-siguiente');
        const totalTurnos = Array.isArray(turnosDisponibles) ? turnosDisponibles.length : 0;
        const turnoIdx = typeof turnoActualIndex === 'number' ? turnoActualIndex : 0;

        const enPrimerSemestre = idx <= 0;
        const enUltimoSemestre = idx === -1 || idx >= semestres.length - 1;
        const enPrimerTurno = turnoIdx <= 0;
        const enUltimoTurno = totalTurnos === 0 ? true : turnoIdx >= totalTurnos - 1;

        if (btnAnterior) btnAnterior.disabled = enPrimerSemestre && enPrimerTurno;
        if (btnSiguiente) btnSiguiente.disabled = enUltimoSemestre && enUltimoTurno;
    }

    function cambiarSemestre(direccion) {
        const semestres = obtenerSemestresDisponibles();
        const actual = parseInt(document.getElementById('semestre')?.value || '1');
        const idx = semestres.indexOf(actual);
        if (idx === -1) return;

        const nextIdx = idx + direccion;
        if (nextIdx < 0 || nextIdx >= semestres.length) return;

        seleccionarSemestre(semestres[nextIdx]);
        actualizarEstadoBotonesSemestre();
    }

    function cambiarNavegacionSemestre(direccion) {
        const totalTurnos = Array.isArray(turnosDisponibles) ? turnosDisponibles.length : 0;
        const turnoIdx = typeof turnoActualIndex === 'number' ? turnoActualIndex : 0;

        if (direccion > 0) {
            if (totalTurnos > 0 && turnoIdx < totalTurnos - 1) {
                cambiarTurno(1);
                actualizarEstadoBotonesSemestre();
                return;
            }
            cambiarSemestre(1);
            return;
        }

        if (totalTurnos > 0 && turnoIdx > 0) {
            cambiarTurno(-1);
            actualizarEstadoBotonesSemestre();
            return;
        }

        const semestres = obtenerSemestresDisponibles();
        const actual = parseInt(document.getElementById('semestre')?.value || '1');
        const idx = semestres.indexOf(actual);
        if (idx <= 0) return;

        seleccionarSemestre(semestres[idx - 1]);
        if (totalTurnos > 0) {
            setTimeout(() => {
                turnoActualIndex = totalTurnos - 1;
                cambiarTurno(0);
                actualizarEstadoBotonesSemestre();
            }, 50);
        } else {
            actualizarEstadoBotonesSemestre();
        }
    }

    // Función para generar pestañas de semestres con semáforo
    // Ahora acepta un array de semestres o un número máximo (para compatibilidad)
    function generarPestanasSemestres(semestresParam) {
        const tabsContainer = document.getElementById('semestres-tabs');
        tabsContainer.innerHTML = '';
        
        let semestresAGenerar = [];
        
        // Si es un número, generar del 1 al número (modo antiguo)
        if (typeof semestresParam === 'number') {
            for (let i = 1; i <= semestresParam; i++) {
                semestresAGenerar.push(i);
            }
        } 
        // Si es un array, usar el array directamente (modo nuevo - del SP)
        else if (Array.isArray(semestresParam) && semestresParam.length > 0) {
            semestresAGenerar = [...semestresParam].sort((a, b) => a - b);
        }
        // Si no hay parámetro válido, usar semestresDisponiblesSP o generar 6 por defecto
        else {
            if (semestresDisponiblesSP && semestresDisponiblesSP.length > 0) {
                semestresAGenerar = [...semestresDisponiblesSP];
            } else {
                // Fallback: generar 6 semestres por defecto
                for (let i = 1; i <= 6; i++) {
                    semestresAGenerar.push(i);
                }
            }
        }
        
        console.log('🎯 Generando pestañas para semestres:', semestresAGenerar);
        
        // Obtener el semestre actualmente seleccionado
        const semestreActualElement = document.getElementById('semestre');
        const semestreActualSeleccionado = semestreActualElement ? parseInt(semestreActualElement.value) : null;
        
        // Si el semestre actualmente seleccionado no está en la lista disponible, usar el primero real
        let semestreEfectivo = semestreActualSeleccionado;
        if (!semestreEfectivo || !semestresAGenerar.includes(semestreEfectivo)) {
            semestreEfectivo = semestresAGenerar[0];
            if (semestreActualElement) {
                semestreActualElement.value = semestreEfectivo;
            }
            console.log(`⚠️ Semestre ${semestreActualSeleccionado} no disponible en la lista. Usando primer semestre real: ${semestreEfectivo}`);
        } else {
            console.log(`📌 Semestre actualmente seleccionado: ${semestreEfectivo}`);
        }
        
        // ✨ OPTIMIZACIÓN: Usar DocumentFragment para inserciones masivas (mucho más rápido)
        const fragment = document.createDocumentFragment();
        
        semestresAGenerar.forEach((semestreNum, index) => {
            const tab = document.createElement('button');
            tab.className = 'semestre-tab';
            tab.textContent = `Semestre ${semestreNum}`;
            tab.setAttribute('data-semestre', semestreNum);
            // ✨ NOTA: onclick se maneja con event delegation en el contenedor
            
            // Aplicar color del semáforo
            actualizarColorPestana(tab, semestreNum);
            
            // Marcar como activo el primer semestre real del SP
            if (semestreNum === semestreEfectivo) {
                tab.classList.add('active');
                console.log(`✅ Pestaña Semestre ${semestreNum} marcada como activa`);
            }
            
            fragment.appendChild(tab);
        });
        
        // Una sola inserción al DOM (mucho más eficiente)
        tabsContainer.appendChild(fragment);
        actualizarEstadoBotonesSemestre();

        // Inicializar barra de semestre actual al generar las pestañas
        actualizarBarraSemestreActual(semestreEfectivo);
    }

    // Función para actualizar el color de una pestaña según su estado
    function actualizarColorPestana(tab, semestreNum) {
        const estadoId = determinarEstadoSemestre(semestreNum);
        const estado = semaforoEstados.find(s => s.id === estadoId);
        
        if (estado) {
            // Remover clases de color anteriores
            tab.classList.remove('semaforo-estado-1', 'semaforo-estado-2', 'semaforo-estado-3');
            
            // Agregar clase y estilo para el estado actual
            tab.classList.add(`semaforo-estado-${estadoId}`);
            tab.style.setProperty('--semaforo-color', estado.color);
            
            // Agregar tooltip con la descripción
            tab.title = `${estado.descripcion}`;
            
            console.log(`🚦 Semestre ${semestreNum}: Estado ${estadoId} (${estado.descripcion}) - Color: ${estado.color}`);
        }
    }

    // Función para actualizar todos los colores de las pestañas
    function actualizarColoresPestanas() {
        const tabs = document.querySelectorAll('.semestre-tab');
        tabs.forEach(tab => {
            const semestreNum = parseInt(tab.getAttribute('data-semestre'));
            actualizarColorPestana(tab, semestreNum);
        });
    }

    // Función para guardar datos del semestre actual
    // ✨ OPTIMIZADO: Con cache DOM y acceso más eficiente
    function guardarDatosSemestreActual() {
        // No ejecutar si aún no se ha completado el primer render
        if (!primerRenderCompleto) {
            console.log('🚫 guardarDatosSemestreActual: ignorado hasta completar primer render');
            return;
        }

        let semestreActual = parseInt(domCache.semestre?.value || document.getElementById('semestre')?.value);
        const tbody = domCache.tbody || document.getElementById('matricula-tbody');
        
        if (isNaN(semestreActual) || !tbody) return;
        
        const inputs = tbody.querySelectorAll('input.input-matricula-nueva');
        
        // Inicializar almacén por turno/semestre si no existe
        const datosContexto = obtenerDatosContexto(true);
        let seGuardoAlgúnValor = false;
        
        // ✨ Usar for loop (más rápido) y dataset (más eficiente que getAttribute)
        for (let i = 0; i < inputs.length; i++) {
            const input = inputs[i];
            const tipoIngreso = input.dataset.tipoIngreso;
            const grupoEdad = input.dataset.grupoEdad;
            const sexo = input.dataset.sexo;
            const turnoId = parseInt(input.dataset.turno);
            const valor = input.value || '';
            // Si no hay valor numérico, no sobreescribir lo que venga del SP
            if (valor === '' || isNaN(parseInt(valor))) {
                continue;
            }
            const key = `${tipoIngreso}_${grupoEdad}_${sexo}`;
            if (isNaN(turnoId)) {
                continue;
            }
            if (!datosContexto[turnoId]) {
                datosContexto[turnoId] = {};
            }
            if (!datosContexto[turnoId][semestreActual]) {
                datosContexto[turnoId][semestreActual] = {};
            }
            
            datosContexto[turnoId][semestreActual][key] = valor;
            seGuardoAlgúnValor = true;
        }

        if (seGuardoAlgúnValor) {
            // Marcar que ahora sí existen cambios locales (captura en la UI)
            hayCambiosLocalesPendientes = true;
            console.log(`💾 Datos guardados para semestre ${semestreActual} (todos los turnos)`);
        } else {
            console.log(`ℹ️ guardarDatosSemestreActual: no se encontraron valores numéricos que guardar para semestre ${semestreActual}`);
        }
    }
    
    // ✨ Versión con debouncing para evitar guardados excesivos
    const guardarDatosSemestreActualDebounced = debounce(guardarDatosSemestreActual, 500);

    // Función para restaurar datos del semestre seleccionado
    // ✨ OPTIMIZADO: Restaurar datos con cache DOM y operaciones más eficientes
    function restaurarDatosSemestre(semestreNum) {
        const datosContexto = obtenerDatosContexto(false);
        const tbody = domCache.tbody || document.getElementById('matricula-tbody');
        
        console.log(`🔄 Restaurando semestre ${semestreNum} desde memoria (todos los turnos)`);
        
        if (tbody) {
            const inputs = tbody.querySelectorAll('input.input-matricula-nueva');
            
            // ✨ Usar for loop (más rápido) y dataset (más eficiente)
            for (let i = 0; i < inputs.length; i++) {
                const input = inputs[i];
                const tipoIngreso = input.dataset.tipoIngreso;
                const grupoEdad = input.dataset.grupoEdad;
                const sexo = input.dataset.sexo;
                const turnoId = parseInt(input.dataset.turno);
                const key = `${tipoIngreso}_${grupoEdad}_${sexo}`;
                const datosTurno = (datosContexto[turnoId] || {})[semestreNum] || {};
                
                if (datosTurno[key] !== undefined) {
                    input.value = datosTurno[key];
                }
                // Si NO hay datos guardados, NO hacer nada (conservar valores del SP)
            }
        }
        
        console.log(`✅ Datos restaurados para semestre ${semestreNum}`);
        
        // Recalcular totales después de restaurar
        calcularTotales();
        
        // Ajustar inputs habilitados/inhabilitados según reglas de semestres
        updateInputsBySemestre(semestreNum);
    }

    // Actualizar barra superior con el semestre actual + Programa y Modalidad seleccionados
    function actualizarBarraSemestreActual(semestreNum) {
        const headers = document.querySelectorAll('.tabla-matricula-container .tabla-header');

        // Obtener nombres de Programa y Modalidad desde los selects
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
            let contenido = `<span class="header-semestre">Semestre ${semestreNum}</span>`;
            if (nombrePrograma) {
                contenido += `<span class="header-separador"> ◉ </span><span class="header-programa">${nombrePrograma}</span>`;
            }
            if (nombreModalidad) {
                contenido += `<span class="header-separador"> ◉ </span><span class="header-modalidad">${nombreModalidad}</span>`;
            }

            header.innerHTML = `<h3>${contenido}</h3>`;

            // Auto-ajustar tamaño de fuente: máximo 30px, mínimo 11px
            const h3 = header.querySelector('h3');
            if (h3) {
                let fs = 30;
                h3.style.fontSize = fs + 'px';
                // Reducir hasta que el contenido quepa sin desbordarse
                while (h3.scrollWidth > header.clientWidth && fs > 11) {
                    fs -= 0.5;
                    h3.style.fontSize = fs + 'px';
                }
            }
        });
    }

    // Función para seleccionar semestre
    function seleccionarSemestre(semestreNum) {
        console.log(`🔄 Seleccionando semestre ${semestreNum}...`);
        
        // Guardar datos del semestre actual antes de cambiar
        guardarDatosSemestreActual();
        
        // Actualizar tabs activas
        const tabs = document.querySelectorAll('.semestre-tab');
        tabs.forEach(tab => {
            if (parseInt(tab.getAttribute('data-semestre')) === semestreNum) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
        
        // Actualizar campo oculto (usar el ID del semestre correspondiente)
        document.getElementById('semestre').value = semestreNum;

        // Actualizar barra de semestre actual
        actualizarBarraSemestreActual(semestreNum);
        
        // La vista actual consolida todos los turnos en la misma tabla
        
        // DESPLAZAR A LA TABLA DE MATRÍCULA (dejando visibles las pestañas de semestres)
        setTimeout(() => {
            const tablaContainer = document.querySelector('.tabla-matricula-container');
            if (tablaContainer) {
                const rect = tablaContainer.getBoundingClientRect();
                const offset = 150; // Espacio para mantener las pestañas visibles
                const scrollPosition = window.pageYOffset + rect.top - offset;
                
                window.scrollTo({
                    top: scrollPosition,
                    behavior: 'smooth'
                });
                console.log('📍 Desplazamiento a la tabla de matrícula (con offset para pestañas)');
            }
        }, 200);
        
        // A partir de la vista consolidada por turnos, es necesario
        // REGENERAR la estructura de la tabla en cada cambio de semestre
        // para respetar la regla de tipos de ingreso, pero reutilizando
        // SIEMPRE las filas ya obtenidas del SP (lastRowsSp) sin volver
        // a ejecutar el SP. renderMatriculaFromSP filtrará por el
        // semestre actualmente seleccionado.
        console.log(`📦 Regenerando tabla para semestre ${semestreNum} usando lastRowsSp (sin backend)`);

        if (Array.isArray(lastRowsSp) && lastRowsSp.length > 0 && typeof renderMatriculaFromSP === 'function') {
            // Esta llamada volverá a construir la tabla completa usando
            // el semestre actual (valor de #semestre) y los filtros de
            // programa/modalidad ya seleccionados.
            (async () => {
                await renderMatriculaFromSP(lastRowsSp, {});
            })();
        } else {
            console.warn('⚠️ No hay lastRowsSp disponible al cambiar de semestre; se genera tabla vacía');
            generarTablaVacia(false);
        }

        setTimeout(() => {
            // Cargar nuevamente datos locales auxiliares y aplicar reglas
            cargarTotalGruposDeLocalStorage();
            aplicarTotalGruposParaSemestreYTurnoActual();
            aplicarBloqueoPorSemaforo();
            aplicarModoVista();
            sincronizarAnchoCeldaTotales();
        }, 150);
    }

    // Función que habilita/inhabilita inputs según el semestre seleccionado
    // Regla: Si Semestre 1 -> bloquear 'Reingreso' (tipo id = 2)
    //       Si Semestre != 1 -> bloquear 'Nuevo Ingreso' (tipo id = 1)
// Función que habilita/inhabilita inputs según el semestre seleccionado
function updateInputsBySemestre(semestreNum) {
    // 🚀 FIX: Prevenir race conditions obteniendo siempre el valor actual real del DOM.
    // Esto evita que un setTimeout con un valor atrasado (ej. 1) borre los datos de un semestre distinto (ej. 2).
    const semestreReal = parseInt(document.getElementById('semestre')?.value || semestreNum);
    
    const inputs = document.querySelectorAll('input.input-matricula-nueva');
    inputs.forEach(input => {
        const tipo = input.getAttribute('data-tipo-ingreso');
        if (!tipo) return;

        let shouldDisable = false;
        let tooltipMessage = '';
        
        const estadoSemaforo = estadosSemaforoPorSemestre[parseInt(semestreReal)];
        if (parseInt(estadoSemaforo) === 3) {
            shouldDisable = true;
            tooltipMessage = 'Semestre finalizado';
        } else {
            // Usamos semestreReal en lugar de semestreNum para la validación
            if (parseInt(semestreReal) === 1) {
                // Bloquear Reingreso (tipo 2) en semestre 1
                if (tipo === '2') {
                    shouldDisable = true;
                    tooltipMessage = 'Reingreso no aplica en Semestre 1';
                }
            } else {
                // En cualquier otro semestre, bloquear Nuevo Ingreso (tipo 1)
                if (tipo === '1') {
                    shouldDisable = true;
                    tooltipMessage = `Nuevo Ingreso no aplica en Semestre ${semestreReal}`;
                }
            }
        }

        if (shouldDisable) {
            input.disabled = true;
            input.classList.add('input-disabled');
            input.title = tooltipMessage;
            
            // No limpiar el valor si es por semáforo finalizado, conservar lo traído del SP
            if (tooltipMessage !== 'Semestre finalizado') {
                input.value = ''; // Sólo limpiar si es por regla de tipo ingreso
            }
            
            // Agregar indicador visual al contenedor padre
            const container = input.closest('.matricula-box');
            if (container) {
                container.classList.add('input-container-disabled');
                container.setAttribute('data-tooltip', tooltipMessage);
            }
        } else {
            // Solo habilitar inputs si el usuario ES CAPTURISTA
            if (typeof esCapturista !== 'undefined' && esCapturista) {
                input.disabled = false;
                input.classList.remove('input-disabled');
                input.title = '';
                
                // Remover indicador visual del contenedor padre
                const container = input.closest('.matricula-box');
                if (container) {
                    container.classList.remove('input-container-disabled');
                    container.removeAttribute('data-tooltip');
                }
            } else {
                // Roles de validación: mantener deshabilitado siempre
                input.disabled = true;
                input.classList.add('input-disabled');
                input.style.backgroundColor = '#f0f0f0';
                input.style.cursor = 'not-allowed';
            }
        }
    });
    
    console.log(`🚫 Inputs actualizados para Semestre ${semestreReal}: ${document.querySelectorAll('.input-disabled').length} deshabilitados`);
}

    // Deshabilita todos los inputs de la vista (incluye Total Grupos)
    function deshabilitarTodaLaVista() {
        const inputs = document.querySelectorAll('input.input-matricula-nueva');
        inputs.forEach(input => {
            input.disabled = true;
            input.classList.add('input-disabled');
            const container = input.closest('.matricula-box');
            if (container) {
                container.classList.add('input-container-disabled');
                if (!container.getAttribute('data-tooltip')) {
                    container.setAttribute('data-tooltip', 'Semestre finalizado (bloqueado)');
                }
            }
        });
        const tgTurnos = document.querySelectorAll('.input-total-grupos-turno');
        tgTurnos.forEach(tg => {
            tg.disabled = true;
            tg.classList.add('input-disabled');
        });
        console.log('🔒 Vista de captura bloqueada: todos los inputs deshabilitados');
    }

    // Si el semáforo del semestre actual está en 3 (completado), bloquear edición
    function aplicarBloqueoPorSemaforo() {
        let semestreActual = parseInt(document.getElementById('semestre').value);
        const estado = estadosSemaforoPorSemestre[semestreActual];
        const btnGuardar = document.getElementById('btn-guardar-matricula');
        const btnLimpiar = document.getElementById('btn-limpiar-formulario');
        const btnValidar = document.getElementById('btn-validar-matricula');
        const btnFinalizar = document.getElementById('btn-finalizar-captura');
        
        if (parseInt(estado) === 3) {
            // Bloquear todos los inputs de matrícula (incluye ambos turnos conceptualmente porque se recrean por turno)
            deshabilitarTodaLaVista();
            // Bloquear también el Total Grupos de este semestre-turno
            aplicarTotalGruposParaSemestreYTurnoActual();
            // Deshabilitar botones de acción (incluye Finalizar Semestre)
            [btnGuardar, btnLimpiar, btnValidar, btnFinalizar].forEach(b => { if (b) { b.disabled = true; b.classList.add('input-disabled'); }});
            console.log('🛑 Semestre finalizado (semáforo 3): botones Guardar/Limpiar/Validar/Finalizar deshabilitados.');
        } else {
            // Rehabilitar botones si el semestre NO está finalizado
            [btnGuardar, btnLimpiar, btnValidar, btnFinalizar].forEach(b => { if (b) { b.disabled = false; b.classList.remove('input-disabled'); }});
            console.log('✅ Semestre activo: todos los botones habilitados.');
        }
    }

    async function guardarMatricula() {
        // Validar que al menos un campo tenga datos (ahora aceptando 0)
        const inputs = document.querySelectorAll('input.input-matricula-nueva');
        let hasData = false;
        
        for (let input of inputs) {
            const valor = parseInt(input.value);
            if (!isNaN(valor) && valor >= 0) {
                hasData = true;
                break;
            }
        }
        
        if (!hasData) {
            await Swal.fire({
                icon: 'warning',
                title: 'Sin datos',
                text: 'Por favor, ingrese datos antes de guardar.',
                confirmButtonText: 'Entendido'
            });
            return;
        }

        // Validar que los filtros estén seleccionados
        const periodo = document.getElementById('periodo').value;
        let programa = document.getElementById('programa').value;
        const semestre = document.getElementById('semestre').value;
        const modalidad = document.getElementById('modalidad').value;
        
        // **LÓGICA ESPECIAL PARA TRONCO COMÚN**
        const programaSelect = document.getElementById('programa');
        const programaNombre = programaSelect?.selectedOptions[0]?.text || '';
        if (programaNombre.toLowerCase().includes('tronco común')) {
            console.log(`🎓 TRONCO COMÚN detectado en guardar (ID original: ${programa}) → Forzando ID = 1`);
            programa = '1';
        }
        
        if (!periodo || !programa || !semestre || !modalidad) {
            await Swal.fire({
                icon: 'warning',
                title: 'Filtros incompletos',
                text: 'Por favor, complete todos los filtros antes de guardar.',
                confirmButtonText: 'Entendido'
            });
            return;
        }

        const datosPorTurno = {};
        inputs.forEach(input => {
            if (!input.disabled) {
                const tipoIngreso = input.getAttribute('data-tipo-ingreso');
                const grupoEdad = input.getAttribute('data-grupo-edad');
                const sexo = input.getAttribute('data-sexo');
                const turnoId = parseInt(input.getAttribute('data-turno'));
                const inputValue = input.value ? input.value.trim() : '';
                const isAutoFilled = input.hasAttribute('data-auto-filled');
                const hasUserValue = inputValue !== '';
                
                if (isNaN(turnoId)) return;
                if (hasUserValue || isAutoFilled) {
                    const valor = parseInt(inputValue) || 0;
                    if (valor >= 0) {
                        const key = `${tipoIngreso}_${grupoEdad}_${sexo}`;
                        if (!datosPorTurno[turnoId]) datosPorTurno[turnoId] = {};
                        const claveTurno = `${parseInt(semestre)}_${turnoId}`;
                        const totalGruposTurno = totalGruposPorSemestreYTurno[claveTurno] || 0;
                        datosPorTurno[turnoId][key] = {
                            tipo_ingreso: tipoIngreso,
                            grupo_edad: grupoEdad,
                            sexo: sexo,
                            matricula: valor,
                            salones: totalGruposTurno
                        };
                    }
                }
            }
        });

        const turnosIds = Object.keys(datosPorTurno);
        if (turnosIds.length === 0) {
            await Swal.fire({
                icon: 'warning',
                title: 'Sin datos',
                text: 'No se encontraron datos válidos para guardar.',
                confirmButtonText: 'Entendido'
            });
            return;
        }

        // Mostrar indicador de carga
        const saveBtn = document.querySelector('.btn-primary');
        const originalText = saveBtn ? saveBtn.textContent : '';
        if (saveBtn) {
            saveBtn.textContent = '⏳ Guardando...';
            saveBtn.disabled = true;
        }

        try {
            for (const turnoId of turnosIds) {
                const claveTurno = `${parseInt(semestre)}_${turnoId}`;
                const totalGruposTurno = totalGruposPorSemestreYTurno[claveTurno] || 0;
                const payload = {
                    periodo: periodo,
                    programa: programa,
                    semestre: semestre,
                    modalidad: modalidad,
                    turno: turnoId,
                    total_grupos: totalGruposTurno,
                    datos_matricula: datosPorTurno[turnoId]
                };
                const response = await fetch('/matricula/guardar_captura_completa', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (result.error) {
                    throw new Error(result.error);
                }
            }
            await Swal.fire({
                icon: 'success',
                title: '✅ Guardado exitoso',
                text: 'Matrícula guardada correctamente.',
                timer: 2000,
                timerProgressBar: true,
                showConfirmButton: false
            });
            limpiarFormulario();
        } catch (error) {
            console.error('Error:', error);
            await Swal.fire({
                icon: 'error',
                title: 'Error al guardar',
                text: error.message,
                confirmButtonText: 'Entendido'
            });
        } finally {
            if (saveBtn) {
                saveBtn.textContent = originalText;
                saveBtn.disabled = false;
            }
        }
    }

    // Nuevo flujo unificado: guarda en Temp_Matricula y, si todo va bien, ejecuta el SP de actualización
    async function guardarYActualizarMatricula() {
        // Verificar si hay un SP en ejecución
        if (!verificarSiPuedeContinuar()) {
            return;
        }
        
        // Validar que al menos un campo tenga datos (incluye 0)
        const inputs = document.querySelectorAll('input.input-matricula-nueva');
        let hasData = false;
        for (let input of inputs) {
            const valor = parseInt(input.value);
            if (!isNaN(valor) && valor >= 0) { hasData = true; break; }
        }
        if (!hasData) { 
            await Swal.fire({
                icon: 'warning',
                title: 'Sin datos',
                text: 'Por favor, ingrese datos antes de guardar.',
                confirmButtonText: 'Entendido'
            });
            return; 
        }

        // Filtros requeridos
        const periodo = document.getElementById('periodo').value;
        let programa = document.getElementById('programa').value;
        const semestre = document.getElementById('semestre').value;
        const modalidad = document.getElementById('modalidad').value;
        // **LÓGICA ESPECIAL PARA TRONCO COMÚN**
        const programaSelect = document.getElementById('programa');
        const programaNombre = programaSelect?.selectedOptions[0]?.text || '';
        if (programaNombre.toLowerCase().includes('tronco común')) {
            programa = '1';
        }
        if (!periodo || !programa || !semestre || !modalidad) {
            await Swal.fire({
                icon: 'warning',
                title: 'Filtros incompletos',
                text: 'Por favor, complete todos los filtros antes de guardar.',
                confirmButtonText: 'Entendido'
            });
            return;
        }
        
        // Mostrar overlay
        mostrarOverlayCarga('Guardando Matrícula...', 'Por favor espere mientras se actualizan los datos');

        // Total de grupos del semestre (suma de todos los turnos)
        const totalGrupos = totalGruposPorSemestre[semestre] || 0;

        // Construir payloads por turno
        const datosPorTurno = {};
        inputs.forEach(input => {
            if (!input.disabled) {
                const tipoIngreso = input.getAttribute('data-tipo-ingreso');
                const grupoEdad = input.getAttribute('data-grupo-edad');
                const sexo = input.getAttribute('data-sexo');
                const turnoId = parseInt(input.getAttribute('data-turno'));
                const inputValue = input.value ? input.value.trim() : '';
                const isAutoFilled = input.hasAttribute('data-auto-filled');
                const hasUserValue = inputValue !== '';
                if (isNaN(turnoId)) return;
                if (hasUserValue || isAutoFilled) {
                    const valor = parseInt(inputValue) || 0;
                    if (valor >= 0) {
                        const key = `${tipoIngreso}_${grupoEdad}_${sexo}`;
                        if (!datosPorTurno[turnoId]) datosPorTurno[turnoId] = {};
                        const claveTurno = `${parseInt(semestre)}_${turnoId}`;
                        const totalGruposTurno = totalGruposPorSemestreYTurno[claveTurno] || 0;
                        datosPorTurno[turnoId][key] = {
                            tipo_ingreso: tipoIngreso,
                            grupo_edad: grupoEdad,
                            sexo: sexo,
                            matricula: valor,
                            salones: totalGruposTurno
                        };
                    }
                }
            }
        });

        const btn = document.getElementById('btn-guardar-matricula');
        const original = btn ? btn.textContent : '';
        if (btn) {
            btn.textContent = '⏳ Guardando…';
            btn.disabled = true;
        }

        try {
            // 1) Guardar en Temp_Matricula por turno
            const turnosIds = Object.keys(datosPorTurno);
            if (turnosIds.length === 0) {
                throw new Error('No se encontraron datos válidos para guardar.');
            }
            console.log(`📊 Guardando datos en Temp_Matricula para ${turnosIds.length} turnos...`);
            for (const turnoId of turnosIds) {
                const claveTurno = `${parseInt(semestre)}_${turnoId}`;
                const totalGruposTurno = totalGruposPorSemestreYTurno[claveTurno] || 0;
                const payload = {
                    periodo, programa, semestre, modalidad, turno: turnoId,
                    total_grupos: totalGruposTurno,
                    datos_matricula: datosPorTurno[turnoId]
                };
                console.log(`💾 Guardando turno ${turnoId}:`, {
                    periodo, programa, semestre, modalidad, turno: turnoId,
                    total_grupos: totalGruposTurno,
                    cantidad_registros: Object.keys(datosPorTurno[turnoId]).length
                });
                const r1 = await fetch('/matricula/guardar_captura_completa', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const d1 = await r1.json();
                console.log(`✅ Respuesta guardar turno ${turnoId}:`, d1);
                if (d1.error) throw new Error(d1.error);
                // d1.mensaje puede ser truthy o falsy según el backend (0 registros es válido);
                // solo se corta si viene error explícito.
            }

            // Ejecutar el SP de actualización definitiva
            const semActual = parseInt(document.getElementById('semestre')?.value || '1');
            const totalGruposActual = totalGruposPorSemestre[semActual] || 0;
            console.log(`🚀 Ejecutando SP actualizar_matricula con:`, {
                periodo, 
                total_grupos: totalGruposActual
            });
            const r2 = await fetch('/matricula/actualizar_matricula', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ periodo, total_grupos: totalGruposActual })
            });
            const d2 = await r2.json();
            console.log(`📥 Respuesta del SP:`, d2);
            if (d2.error) throw new Error(d2.error);
            
            // **NUEVO: Mostrar información de diagnóstico**
            let mensajeResultado = 'Matrícula guardada y actualizada correctamente.';
            let detalles = '';
            if (d2.diagnostico) {
                const diag = d2.diagnostico;
                detalles = `📊 Diagnóstico:<br>` +
                    `• Registros antes: ${diag.registros_antes}<br>` +
                    `• Registros después: ${diag.registros_despues}<br>` +
                    `• Diferencia: ${diag.diferencia > 0 ? '+' : ''}${diag.diferencia}`;
                
                if (!diag.sp_hizo_cambios) {
                    detalles += `<br><br>⚠️ ADVERTENCIA: El SP no hizo cambios en Matricula`;
                } else if (diag.diferencia > 0) {
                    detalles += `<br><br>✅ Se insertaron ${diag.diferencia} registros nuevos`;
                } else {
                    detalles += `<br><br>✅ Se actualizaron registros existentes`;
                }
            }
            
            await Swal.fire({
                title: '¡Guardado!',
                html: mensajeResultado + (detalles ? '<br><br>' + detalles : ''),
                icon: 'success',
                timer: 2000,
                showConfirmButton: true
            });

            // Refrescar estado del semáforo desde el SP tras el guardado
            try {
                const reqSem = { periodo, programa, modalidad };
                if (typeof esRolSuperior !== 'undefined' && esRolSuperior && window.contextoRolSuperior) {
                    reqSem.id_unidad_academica = window.contextoRolSuperior.id_unidad_academica;
                    reqSem.id_nivel = window.contextoRolSuperior.id_nivel;
                }
                const rSem = await fetch('/matricula/obtener_datos_existentes_sp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reqSem)
                });
                const dSem = await rSem.json();
                if (dSem.rows && dSem.rows.length > 0) {
                    estadosSemaforoPorSemestre = {};
                    procesarEstadosSemaforoDelSP(dSem.rows);
                    actualizarColoresPestanas();
                    aplicarBloqueoPorSemaforo();

                    // ✅ Actualizar datos base SP con los valores recién guardados:
                    // - lastRowsSp: usados en cada cambio de pestaña (renderMatriculaFromSP)
                    // - procesarYGuardar: refresca datosContexto → hayCambiosLocalesPendientes=false
                    // - renderMatriculaFromSP: re-dibuja la tabla actual con el estado correcto del SP
                    lastRowsSp = dSem.rows;
                    window.lastRowsSp = lastRowsSp;
                    if (typeof procesarYGuardarDatosPorSemestre === 'function') {
                        procesarYGuardarDatosPorSemestre(dSem.rows);
                    }
                    if (typeof renderMatriculaFromSP === 'function') {
                        await renderMatriculaFromSP(dSem.rows, {});
                    }
                }
            } catch (eSem) {
                console.warn('⚠️ No se pudo refrescar el semáforo:', eSem);
            }
        } catch (e) {
            console.error('Error en Guardar Matrícula unificado:', e);
            await Swal.fire({
                title: 'Error',
                text: `Error al guardar la matrícula: ${e.message}`,
                icon: 'error'
            });
        } finally {
            ocultarOverlayCarga();
            if (btn) {
                btn.textContent = original;
                btn.disabled = false;
            }
        }
    }

    function scrollToVisibleInput(event) {
        const input = event.target;
        const container = document.querySelector('.tabla-matricula-completa tbody');
        
        if (!container || !input) return;
        
        // Agregar un pequeño retraso para que el foco se establezca completamente
        setTimeout(() => {
            // Obtener la fila que contiene el input
            const row = input.closest('tr');
            if (!row) return;
            
            // Calcular la posición de la fila dentro del contenedor
            const rowRect = row.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            
            // Posición relativa de la fila dentro del contenedor scrolleable
            const rowTop = rowRect.top - containerRect.top + container.scrollTop;
            const rowHeight = rowRect.height;
            
            // Altura útil del contenedor (descontando espacio para totales)
            const containerHeight = container.clientHeight;
            const reservedSpace = 80; // Espacio para totales y margen
            const usableHeight = containerHeight - reservedSpace;
            
            // Centrar la fila en el área visible
            const targetScrollTop = rowTop - (usableHeight / 2) + (rowHeight / 2);
            
            // Aplicar scroll suave hacia la posición calculada
            container.scrollTo({
                top: Math.max(0, targetScrollTop), // No permitir scroll negativo
                behavior: 'smooth'
            });
            
            // Resaltar temporalmente el input para que sea más visible
            input.style.boxShadow = '0 0 10px 3px rgba(110, 3, 67, 0.5)';
            input.style.transform = 'scale(1.05)';
            
            // Quitar el resaltado después de 1 segundo
            setTimeout(() => {
                input.style.boxShadow = '';
                input.style.transform = '';
            }, 1000);
            
        }, 10); // Pequeño retraso para asegurar que el foco esté establecido
    }

    // ✨ OPTIMIZADO: Usar cache DOM
    function limpiarFormulario() {
        console.log('🧹 Ejecutando limpiarFormulario()...');
        
        // Limpiar todos los inputs de matrícula del semestre/turno actual
        const tbody = domCache.tbody || document.getElementById('matricula-tbody');
        if (tbody) {
            const inputs = tbody.querySelectorAll('input.input-matricula-nueva');
            // Usar for loop: más rápido que forEach
            for (let i = 0; i < inputs.length; i++) {
                inputs[i].value = '';
                inputs[i].removeAttribute('data-auto-filled');
            }
            console.log('🗑️ Valores de inputs de matrícula limpiados (estructura preservada)');
        }

        // NO tocar la estructura de la tabla ni los totales de grupos; 
        // solo recalcular totales de H/M/TOTAL con los nuevos valores vacíos.
        calcularTotales();
    }

    // Agregar eventos a los inputs para cálculos automáticos
    document.addEventListener('DOMContentLoaded', function() {
        // ✨ INICIALIZAR CACHE DOM PRIMERO (CRÍTICO PARA OPTIMIZACIONES)
        inicializarCacheDOM();
        
        // Inicializar pestañas de semestres según programa seleccionado
        const programaEl = document.getElementById('programa');
        if (programaEl) {
            const opt = programaEl.selectedOptions[0];
            const maxSem = parseInt(opt?.getAttribute('data-max-semestre')) || 5;
            generarPestanasSemestres(maxSem);
            
            // Actualizar pestañas cuando cambie el programa
            // NOTA: Las pestañas se regenerarán dinámicamente cuando lleguen los datos del SP
            programaEl.addEventListener('change', function() {
                console.log('🔄 Programa cambiado, los datos del SP determinarán los semestres disponibles');
                // NO regenerar pestañas aquí - se hará en renderMatriculaFromSP con datos del SP
            });
        }
        
        // Inicializar turno oculto (si aplica)
        if (turnosDisponibles && turnosDisponibles.length > 0) {
            const turnoInput = document.getElementById('turno');
            if (turnoInput) turnoInput.value = turnosDisponibles[0].Id_Turno;
        }
        
        // Agregar eventos a los filtros para cargar datos existentes
        const filtros = ['periodo', 'programa', 'modalidad'];
        filtros.forEach(filtroId => {
            const elemento = document.getElementById(filtroId);
            if (elemento) {
                elemento.addEventListener('change', function() {
                    // Limpiar datos guardados cuando cambie programa o modalidad
                    console.log(`🔄 Cambió ${filtroId}, limpiando datos guardados`);
                    
                    // 🗑️ LIMPIAR DATOS DE MATRÍCULA POR SEMESTRE (CRÍTICO)
                    limpiarDatosContexto();
                    console.log('🗑️ datosMatriculaPorSemestre limpiado para el contexto actual');
                    
                    // ✨ RESETEAR bandera de datos cargados (forzar nueva carga del SP)
                    datosCompletosYaCargados = false;
                    
                    // NUEVO: Limpiar turnos validados
                    turnosValidadosPorSemestre = {};
                    try {
                        const key = `turnos_validados_${document.getElementById('periodo').value}_${document.getElementById('programa').value}_${document.getElementById('modalidad').value}`;
                        localStorage.removeItem(key);
                        console.log('🗑️ Turnos validados limpiados de localStorage');
                    } catch (e) {
                        console.warn('No se pudo limpiar turnos validados de localStorage', e);
                    }
                    
                    // 🧹 LIMPIAR TOTAL GRUPOS POR SEMESTRE
                    console.log('🗑️ Limpiando totalGruposPorSemestre...');
                    totalGruposPorSemestre = {};
                    guardarTotalGruposEnLocalStorage();
                    
                    // 🧹 LIMPIAR FORMULARIO COMPLETO INMEDIATAMENTE
                    console.log('🧹 Limpiando formulario completo...');
                    limpiarFormulario();
                    
                    // Limpiar atributos data-auto-filled de todos los inputs
                    const inputs = document.querySelectorAll('input.input-matricula-nueva');
                    inputs.forEach(input => {
                        input.removeAttribute('data-auto-filled');
                    });
                    
                    console.log('🗑️ Datos de matrícula, Total Grupos, marcadores auto-filled y turnos validados limpiados por cambio de contexto');
                    
                    // Reinicializar botón de validar
                    reinicializarBotonValidar();
                    
                    // Para cambio de contexto, solo limpiar; el SP NO se vuelve a ejecutar aquí
                });
            }
        });

        // ✨ EVENT DELEGATION para pestañas de semestres (optimizado)
        const semestreTabsContainer = document.getElementById('semestres-tabs');
        if (semestreTabsContainer) {
            semestreTabsContainer.addEventListener('click', function(e) {
                const tab = e.target.closest('.semestre-tab');
                if (tab) {
                    const semestreNum = parseInt(tab.getAttribute('data-semestre'));
                    if (!isNaN(semestreNum)) {
                        seleccionarSemestre(semestreNum);
                    }
                }
            });
            console.log('✅ Event delegation configurado para pestañas de semestres');
        }
        
        // Generar tabla vacía inicial (aunque la sección esté oculta)
        generarTablaVacia();

        // Si el backend ya ejecutó el SP y envió filas iniciales,
        // guárdalas en cache pero SOLO renderiza cuando haya filtros completos.
        if (Array.isArray(rowsInicialesSp) && rowsInicialesSp.length > 0) {
            console.log('✅ Usando rowsInicialesSp enviados por el backend (sin segunda llamada al SP)');

            // Guardar en la cache global como si vinieran de cargarDatosExistentes
            lastRowsSp = rowsInicialesSp;
            if (typeof window !== 'undefined') {
                window.lastRowsSp = lastRowsSp;
            }

            const selPrograma = document.getElementById('programa');
            const selModalidad = document.getElementById('modalidad');
            const filtrosCompletos = selPrograma && selPrograma.value && selModalidad && selModalidad.value;

            if (filtrosCompletos) {
                // Procesar estados de semáforo y datos por semestre/turno
                procesarEstadosSemaforoDelSP(rowsInicialesSp);
                procesarYGuardarDatosPorSemestre(rowsInicialesSp);
                procesarTotalGruposDesdeSP(rowsInicialesSp);

            // Derivar turnos visibles desde las filas iniciales
            try {
                const turnoCandidates = ['Turno', 'Nombre_Turno', 'Id_Turno', 'IdTurno'];
                const first = rowsInicialesSp[0] || {};
                const keys = Object.keys(first);
                const findKey = (cands) => {
                    for (let c of cands) if (keys.includes(c)) return c;
                    const low = keys.reduce((acc, k) => { acc[k.toLowerCase()] = k; return acc; }, {});
                    for (let c of cands) if (low[c.toLowerCase()]) return low[c.toLowerCase()];
                    return null;
                };
                const turnoKey = findKey(turnoCandidates);
                const turnosMap = new Map();
                if (turnoKey) {
                    rowsInicialesSp.forEach(r => {
                        const turnoRaw = r[turnoKey];
                        const turnoId = mapTurnoToId(turnoRaw);
                        if (isNaN(turnoId)) return;
                        let turnoNombre = '';
                        const rawStr = String(turnoRaw || '').trim();
                        if (rawStr && isNaN(parseInt(rawStr))) {
                            turnoNombre = rawStr;
                        }
                        if (!turnoNombre && Array.isArray(turnosDisponibles)) {
                            const match = turnosDisponibles.find(t => parseInt(t.Id_Turno) === turnoId);
                            if (match) turnoNombre = match.Turno;
                        }
                        turnosMap.set(turnoId, { id: turnoId, nombre: turnoNombre || `Turno ${turnoId}` });
                    });
                }
                if (turnosMap.size === 0 && Array.isArray(turnosDisponibles)) {
                    turnosDisponibles.forEach(t => {
                        const turnoId = parseInt(t.Id_Turno);
                        if (!isNaN(turnoId)) {
                            turnosMap.set(turnoId, { id: turnoId, nombre: t.Turno });
                        }
                    });
                }
                turnosVisibles = Array.from(turnosMap.values()).sort((a, b) => a.id - b.id);
            } catch (e) {
                console.warn('⚠️ No se pudieron derivar turnos visibles desde rowsInicialesSp', e);
                turnosVisibles = [];
            }

                // Renderizar tabla completa usando la misma lógica que en recargas,
                // lo que incluye reglas especiales de semestres para Tronco Común
                // y programas Técnicos de nivel Medio Superior.
                if (typeof renderMatriculaFromSP === 'function') {
                    (async () => {
                        await renderMatriculaFromSP(rowsInicialesSp, {});
                        datosCompletosYaCargados = true;
                        primerRenderCompleto = true;
                        console.log('✅ Primer render completo - eventos de guardado activos');

                        // Aplicar restricciones después de renderizar pestañas
                        aplicarTotalGruposParaSemestreYTurnoActual();
                        aplicarBloqueoPorSemaforo();
                        aplicarModoVista();
                        calcularTotales();
                        
                        // Auto-seleccionar directamente
                        autoSeleccionarPrimerSemestreDisponible();
                    })();
                } else {
                    console.error('❌ Función renderMatriculaFromSP no disponible');
                    generarTablaVacia(false);
                }
            } else {
                console.log('⏸ Filtros incompletos al cargar: se pospone render de tabla hasta que se seleccione programa y modalidad');
            }
        } else {
            // Sin filas iniciales: solo usar flujo normal cuando haya filtros completos
            const selPrograma = document.getElementById('programa');
            const selModalidad = document.getElementById('modalidad');
            const filtrosCompletos = selPrograma && selPrograma.value && selModalidad && selModalidad.value;
            if (filtrosCompletos) {
                console.log('ℹ️ Sin rowsInicialesSp, llamando a cargarDatosExistentes() con filtros completos');
                cargarDatosExistentes();
                calcularTotales();
            } else {
                console.log('⏸ Sin rowsInicialesSp y filtros incompletos: no se llama a cargarDatosExistentes aún');
            }
        }
    });

    // Función para validar campos vacíos
    async function validarCamposVacios() {
        const inputs = document.querySelectorAll('.input-matricula-nueva');
        let camposVacios = 0;
        
        inputs.forEach(input => {
            if (!input.value || input.value.trim() === '') {
                camposVacios++;
            }
        });
        
        if (camposVacios > 0) {
            const confirmacion = await Swal.fire({
                title: 'Campos vacíos detectados',
                text: `Se detectaron ${camposVacios} campos vacíos. ¿Desea llenarlos con ceros?`,
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'Sí, llenar',
                cancelButtonText: 'No',
                confirmButtonColor: '#28a745',
                cancelButtonColor: '#dc3545'
            });
            
            if (confirmacion.isConfirmed) {
                inputs.forEach(input => {
                    if (!input.value || input.value.trim() === '') {
                        input.value = '0';
                        // Marcar como auto-rellenado
                        input.setAttribute('data-auto-filled', 'true');
                    }
                });
                calcularTotales();
                await Swal.fire({
                    icon: 'success',
                    title: 'Campos completados',
                    text: 'Los campos vacíos se han llenado con ceros.',
                    timer: 2000,
                    timerProgressBar: true,
                    showConfirmButton: false
                });
            }
        } else {
            await Swal.fire({
                icon: 'info',
                title: 'Todo completo',
                text: 'Todos los campos están completos.',
                timer: 2000,
                timerProgressBar: true,
                showConfirmButton: false
            });
        }
    }

    // ===== NUEVO SISTEMA: VALIDACIÓN POR TURNOS CON EJECUCIÓN CONSOLIDADA =====
    
    // Estructura para rastrear turnos validados por semestre
    let turnosValidadosPorSemestre = {};
    
    // Cargar turnos validados desde localStorage
    function cargarTurnosValidadosDeLocalStorage() {
        try {
            const key = `turnos_validados_${document.getElementById('periodo').value}_${document.getElementById('programa').value}_${document.getElementById('modalidad').value}`;
            const raw = localStorage.getItem(key);
            turnosValidadosPorSemestre = raw ? JSON.parse(raw) : {};
            console.log('📂 Turnos validados cargados:', turnosValidadosPorSemestre);
        } catch (e) {
            console.warn('No se pudo cargar turnos validados de localStorage', e);
            turnosValidadosPorSemestre = {};
        }
    }
    
    // Inicializar el sistema de validación por turnos
    function inicializarSistemaValidacionTurnos() {
        cargarTurnosValidadosDeLocalStorage();
        aplicarEstadoValidacionTurnos();
    }
    
    // Aplicar el estado de validación a los turnos (bloquear los ya validados)
    function aplicarEstadoValidacionTurnos() {
        let semestreActual = parseInt(document.getElementById('semestre').value);
        const semestreValidado = todosTurnosValidados(semestreActual);
        
        if (semestreValidado) {
            console.log(`🔒 Semestre ${semestreActual} ya está validado - aplicando bloqueo PERMANENTE`);
            
            // Bloquear todos los inputs del semestre
            const inputs = document.querySelectorAll('input.input-matricula-nueva');
            inputs.forEach(input => {
                input.disabled = true;
                input.classList.add('input-disabled');
            });
            
            // Bloquear también los inputs de Total Grupos por turno
            const tgTurnos = document.querySelectorAll('.input-total-grupos-turno');
            tgTurnos.forEach(tg => {
                tg.disabled = true;
                tg.classList.add('input-disabled');
            });
            
            // Bloquear botón de validar
            const btnValidar = document.getElementById('btn-validar-matricula');
            if (btnValidar) {
                btnValidar.disabled = true;
                btnValidar.classList.add('input-disabled');
                btnValidar.textContent = '✅ Semestre Validado';
            }
            
            // Bloquear botón de guardar avance
            const btnGuardar = document.getElementById('btn-guardar-matricula');
            if (btnGuardar) {
                btnGuardar.disabled = true;
                btnGuardar.classList.add('input-disabled');
            }
            
            console.log('🎉 Todos los turnos del semestre están validados');
        }
    }
    
    // Reinicializar botón de finalizar captura
    function reinicializarBotonValidar() {
        const btnFinalizar = document.getElementById('btn-finalizar-captura');
        if (btnFinalizar) {
            btnFinalizar.disabled = false;
            btnFinalizar.classList.remove('input-disabled');
            btnFinalizar.textContent = '🎯 Finalizar Semestre';
        }
    }
    
    // Guardar turnos validados en localStorage
    function guardarTurnosValidadosEnLocalStorage() {
        try {
            const key = `turnos_validados_${document.getElementById('periodo').value}_${document.getElementById('programa').value}_${document.getElementById('modalidad').value}`;
            localStorage.setItem(key, JSON.stringify(turnosValidadosPorSemestre));
        } catch (e) {
            console.warn('No se pudo guardar turnos validados en localStorage', e);
        }
    }
    
    // Marcar turno como validado (sin ejecutar SP)
    function marcarTurnoComoValidado(semestre, turno) {
        if (!turnosValidadosPorSemestre[semestre]) {
            turnosValidadosPorSemestre[semestre] = [];
        }
        if (!turnosValidadosPorSemestre[semestre].includes(turno)) {
            turnosValidadosPorSemestre[semestre].push(turno);
            guardarTurnosValidadosEnLocalStorage();
        }
    }
    
    // Verificar si todos los turnos de un semestre están validados
    function todosTurnosValidados(semestre) {
        const turnosDelSemestre = turnosValidadosPorSemestre[semestre] || [];
        const turnosIds = (turnosVisibles && turnosVisibles.length > 0)
            ? turnosVisibles.map(t => parseInt(t.id))
            : (turnosDisponibles || []).map(t => parseInt(t.Id_Turno));
        return turnosIds.every(turnoId => turnosDelSemestre.includes(turnoId));
    }
    
    // Función para ejecutar el SP final cuando todos los turnos están listos
    async function ejecutarSPFinalSemestre(semestreActual, periodo, programa, modalidad, semestre) {
        console.log('🚀 === EJECUTANDO SP FINAL DEL SEMESTRE ===');
        
        // **LÓGICA ESPECIAL PARA TRONCO COMÚN**
        const programaSelect = document.getElementById('programa');
        const programaNombre = programaSelect?.selectedOptions[0]?.text || '';
        if (programaNombre.toLowerCase().includes('tronco común')) {
            console.log(`🎓 TRONCO COMÚN detectado en SP final (ID original: ${programa}) → Forzando ID = 1`);
            programa = '1';
        }
        
        try {
            // Obtener Total Grupos del semestre
            const totalGrupos = totalGruposPorSemestre[semestreActual] || 0;
            
            console.log(`📊 Ejecutando SP final con Total Grupos: ${totalGrupos}`);
            
            // Ejecutar el SP de validación final (el que actualiza el semáforo)
            // NOTA: NO se envía 'turno' porque el SP procesa TODO el semestre
            const response = await fetch('/matricula/validar_captura_semestre', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    periodo: periodo,
                    programa: programa,
                    modalidad: modalidad,
                    semestre: semestre,
                    total_grupos: totalGrupos
                })
            });
            
            const resultado = await response.json();
            console.log('📥 Respuesta del SP final:', resultado);
            
            if (resultado.error) {
                console.error('❌ Error en el SP final:', resultado.error);
                await Swal.fire({
                    icon: 'error',
                    title: 'Error en SP final',
                    text: resultado.error,
                    confirmButtonText: 'Entendido'
                });
                return;
            }
            
            if (resultado.success) {
                console.log('✅ SP final ejecutado exitosamente!');
                
                // Actualizar estado del semáforo
                const estadoVerificado = (typeof resultado.estado_semaforo === 'number') ? resultado.estado_semaforo : null;
                
                // Bloquear siempre la vista cuando el SP finaliza correctamente,
                // aunque por algún motivo no se pueda leer el estado del semáforo.
                if (estadoVerificado === 3 || resultado.success) {
                    // Marcar semestre como completado
                    marcarSemestreComoValidado(semestreActual);
                    console.log(`🚦 Semestre ${semestreActual} marcado como COMPLETADO (estado: ${estadoVerificado})`);
                    
                    // Bloquear toda la vista del semestre
                    deshabilitarTodaLaVista();
                    
                    // Deshabilitar botones de acción
                    const btnGuardar = document.getElementById('btn-guardar-matricula');
                    const btnLimpiar = document.getElementById('btn-limpiar-formulario');
                    const btnValidar = document.getElementById('btn-validar-matricula');
                    
                    [btnGuardar, btnLimpiar, btnValidar].forEach(b => {
                        if (b) {
                            b.disabled = true;
                            b.classList.add('input-disabled');
                        }
                    });
                    
                    console.log('🔒 Vista bloqueada - semestre completado');
                }
                
                // Actualizar colores de pestañas
                actualizarColoresPestanas();
                
                // Procesar datos actualizados del SP si están disponibles
                if (resultado.rows && resultado.rows.length > 0) {
                    console.log('🔄 Procesando datos actualizados del SP final...');
                    procesarEstadosSemaforoDelSP(resultado.rows);
                    procesarYGuardarDatosPorSemestre(resultado.rows);
                    actualizarColoresPestanas();
                }
                
                // Mensaje de éxito
                const semestreNombre = semestresMap[semestreActual] || `Semestre ${semestreActual}`;
                let mensajeEstado = '';
                
                if (estadoVerificado === 3) {
                    mensajeEstado = '🟢 El semestre ha sido marcado como COMPLETADO';
                } else if (estadoVerificado === 2) {
                    mensajeEstado = '🟡 El semestre tiene datos parciales';
                } else if (estadoVerificado === 1) {
                    mensajeEstado = '🔴 El semestre sigue sin datos';
                } else {
                    mensajeEstado = 'No se pudo confirmar el estado del semáforo';
                }
                
                // Mostrar mensaje de éxito sin botón OK
                Swal.fire({
                    icon: 'success',
                    title: '¡Semestre Finalizado!',
                    html: `<strong>${semestreNombre}</strong> consolidado completamente<br><br>` +
                          `${mensajeEstado}<br><br>` +
                          `📊 Todos los turnos han sido procesados<br>` +
                          `🔒 El semestre está ahora bloqueado para edición`,
                    timer: 3000,
                    timerProgressBar: true,
                    showConfirmButton: false
                });
                
                console.log('✅ SP final completado exitosamente');
                
                // AUTO-AVANCE: Pasar al siguiente semestre automáticamente
                console.log('🔄 Auto-avance: Verificando si hay más semestres disponibles...');
                const semestreActualIdx = semestresDisponiblesSP.indexOf(semestreActual);
                console.log(`📍 Índice del semestre actual: ${semestreActualIdx}, Total semestres: ${semestresDisponiblesSP.length}`);
                
                if (semestreActualIdx !== -1 && semestreActualIdx < semestresDisponiblesSP.length - 1) {
                    const siguienteSemestre = semestresDisponiblesSP[semestreActualIdx + 1];
                    const siguienteSemestreNombre = semestresMap[siguienteSemestre] || `Semestre ${siguienteSemestre}`;
                    console.log(`✨ Avanzando al ${siguienteSemestreNombre}...`);
                    
                    setTimeout(() => {
                        seleccionarSemestre(siguienteSemestre);
                        console.log(`✅ Auto-avance completado al ${siguienteSemestreNombre}`);
                    }, 1000); // Delay más largo para que el usuario vea el mensaje de éxito del semestre
                } else if (semestreActualIdx === semestresDisponiblesSP.length - 1) {
                    console.log('🏁 Ya completaste el último semestre disponible');
                    
                    // Obtener información del programa y modalidad actuales
                    const programaSelect = document.getElementById('programa');
                    const modalidadSelect = document.getElementById('modalidad');
                    const programaNombre = programaSelect?.selectedOptions[0]?.text || 'Programa actual';
                    const modalidadNombre = modalidadSelect?.selectedOptions[0]?.text || 'Modalidad actual';
                    
                    setTimeout(() => {
                        Swal.fire({
                            icon: 'success',
                            title: '🎉 ¡FELICITACIONES!',
                            html: '<div style="text-align: center;">' +
                                  '<p style="font-size: 18px; font-weight: bold; margin: 20px 0;">¡Has completado TODOS los semestres!</p>' +
                                  '<hr style="margin: 15px 0; border-color: #28a745;">' +
                                  `<p><strong>📚 Programa:</strong> ${programaNombre}</p>` +
                                  `<p><strong>🎓 Modalidad:</strong> ${modalidadNombre}</p>` +
                                  `<p><strong>✅ Semestres completados:</strong> ${semestresDisponiblesSP.length}</p>` +
                                  '<hr style="margin: 15px 0; border-color: #28a745;">' +
                                  '<p style="color: #28a745; font-weight: bold;">🔒 Proceso de captura finalizado completamente</p>' +
                                  '</div>',
                            confirmButtonText: 'Entendido',
                            confirmButtonColor: '#28a745',
                            width: '600px',
                            showClass: {
                                popup: 'animate__animated animate__fadeInDown'
                            }
                        });
                    }, 2500);
                } else {
                    console.log('⚠️ No se pudo determinar el siguiente semestre');
                }
                
            } else {
                console.warn('⚠️ Respuesta inesperada del SP final');
                await Swal.fire({
                    icon: 'warning',
                    title: 'Respuesta inesperada',
                    text: 'No se pudo confirmar la ejecución del SP final.',
                    confirmButtonText: 'Entendido'
                });
            }
            
        } catch (error) {
            console.error('❌ Error al ejecutar SP final:', error);
            await Swal.fire({
                icon: 'error',
                title: 'Error en SP final',
                text: error.message,
                confirmButtonText: 'Entendido'
            });
        }
    }
    
    // ===== VALIDACIÓN MASIVA DE TODOS LOS SEMESTRES (solo cuando hay rechazo) =====
    async function validarTodosLosSemestres() {
        console.log('🚀 === VALIDACIÓN MASIVA: TODOS LOS SEMESTRES ===');
        
        // Confirmación del usuario
        const confirmacion = await Swal.fire({
            title: '🔄 VALIDACIÓN MASIVA',
            html: '<p><strong>Esta función validará TODOS los semestres y turnos de forma automática.</strong></p>' +
                  '<br><p style="text-align: left; margin-left: 20px;">' +
                  '⚠️ <strong>ADVERTENCIA:</strong><br>' +
                  '• Se procesarán TODOS los semestres disponibles<br>' +
                  '• Se validarán TODOS los turnos de cada semestre<br>' +
                  '• Los datos se guardarán y consolidarán automáticamente<br>' +
                  '• Esta acción NO se puede deshacer' +
                  '</p>',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, continuar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#dc3545',
            width: '600px'
        });
        
        if (!confirmacion.isConfirmed) {
            console.log('❌ Usuario canceló la validación masiva');
            return;
        }
        
        // Obtener filtros actuales
        const periodo = document.getElementById('periodo').value;
        let programa = document.getElementById('programa').value;
        const modalidad = document.getElementById('modalidad').value;
        
        // **LÓGICA ESPECIAL PARA TRONCO COMÚN**
        const programaSelect = document.getElementById('programa');
        const programaNombre = programaSelect?.selectedOptions[0]?.text || '';
        if (programaNombre.toLowerCase().includes('tronco común')) {
            console.log(`🎓 TRONCO COMÚN detectado → Forzando ID = 1`);
            programa = '1';
        }
        
        if (!periodo || !programa || !modalidad) {
            await Swal.fire({
                icon: 'warning',
                title: 'Filtros incompletos',
                text: 'Por favor, complete todos los filtros antes de continuar.',
                confirmButtonText: 'Entendido'
            });
            return;
        }
        
        // Deshabilitar botón durante el proceso
        const btnValidarTodos = document.getElementById('btn-validar-todos-semestres');
        const textoOriginal = btnValidarTodos.textContent;
        btnValidarTodos.disabled = true;
        
        try {
            console.log(`📋 Semestres a procesar: ${semestresDisponiblesSP.length}`);
            console.log(`📋 Semestres: ${semestresDisponiblesSP.join(', ')}`);
            
            let semestresExitosos = 0;
            let semestresConError = 0;
            const detallesProcesamiento = [];
            
            // Iterar por cada semestre
            for (let i = 0; i < semestresDisponiblesSP.length; i++) {
                const semestreId = semestresDisponiblesSP[i];
                const semestreNombre = semestresMap[semestreId] || `Semestre ${semestreId}`;
                
                console.log(`\n🔄 Procesando ${semestreNombre} (${i + 1}/${semestresDisponiblesSP.length})...`);
                btnValidarTodos.textContent = `⏳ Procesando ${semestreNombre}... (${i + 1}/${semestresDisponiblesSP.length})`;
                
                // Seleccionar el semestre
                document.getElementById('semestre').value = semestreId;
                await cargarDatosExistentes(); // Cargar datos del semestre
                
                // Obtener turnos del semestre
                const turnosDelSemestre = turnosDisponibles || [];
                console.log(`   📊 Turnos encontrados: ${turnosDelSemestre.length}`);
                
                if (turnosDelSemestre.length === 0) {
                    console.warn(`   ⚠️ No hay turnos para ${semestreNombre}, saltando...`);
                    detallesProcesamiento.push(`⚠️ ${semestreNombre}: Sin turnos disponibles`);
                    continue;
                }
                
                let turnosExitosos = 0;
                let turnosConError = 0;
                
                // Iterar por cada turno del semestre
                for (let j = 0; j < turnosDelSemestre.length; j++) {
                    const turno = turnosDelSemestre[j];
                    const turnoId = parseInt(turno.Id_Turno);
                    const turnoNombre = turno.Turno;
                    
                    console.log(`      🔹 Validando turno: ${turnoNombre}...`);
                    
                    // Seleccionar el turno
                    document.getElementById('turno').value = turnoId;
                    turnoActualIndex = j;
                    await cargarDatosExistentes(); // Recargar datos con el nuevo turno
                    
                    try {
                        // Obtener Total Grupos (suma de todos los turnos del semestre)
                        const totalGrupos = totalGruposPorSemestre[semestreId] || 0;
                        
                        // Rellenar campos vacíos con '0'
                        const inputs = document.querySelectorAll('input.input-matricula-nueva');
                        inputs.forEach(input => {
                            if (!input.disabled && (!input.value || input.value.trim() === '')) {
                                input.value = '0';
                            }
                        });
                        
                        // Guardar datos del turno
                        const data = {
                            periodo: periodo,
                            programa: programa,
                            semestre: semestreId,
                            modalidad: modalidad,
                            turno: turnoId,
                            total_grupos: totalGrupos,
                            datos_matricula: {}
                        };
                        
                        // Recopilar datos de los inputs
                        inputs.forEach(input => {
                            if (input.dataset.grupoEdad && input.dataset.tipoIngreso && input.dataset.semestre) {
                                const key = `${input.dataset.grupoEdad}_${input.dataset.tipoIngreso}_${input.dataset.semestre}`;
                                data.datos_matricula[key] = parseInt(input.value) || 0;
                            }
                        });
                        
                        // Guardar en Temp_Matricula
                        const saveResponse = await fetch('/matricula/guardar', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });
                        
                        const saveResult = await saveResponse.json();
                        if (saveResult.error) {
                            throw new Error(`Error al guardar: ${saveResult.error}`);
                        }
                        
                        // Actualizar tabla Matricula
                        const updateResponse = await fetch('/matricula/actualizar', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                periodo: periodo,
                                total_grupos: totalGrupos
                            })
                        });
                        
                        const updateResult = await updateResponse.json();
                        if (updateResult.error) {
                            throw new Error(`Error al actualizar: ${updateResult.error}`);
                        }
                        
                        // Preparar turno (ejecutar SP de Unidad Académica)
                        const prepararResponse = await fetch('/matricula/preparar_turno', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                periodo: periodo,
                                programa: programa,
                                modalidad: modalidad,
                                semestre: semestreId,
                                turno: turnoId,
                                total_grupos: totalGrupos
                            })
                        });
                        
                        const prepararResult = await prepararResponse.json();
                        if (prepararResult.error) {
                            throw new Error(`Error al preparar turno: ${prepararResult.error}`);
                        }
                        
                        // Marcar turno como validado
                        marcarTurnoComoValidado(semestreId, turnoId);
                        
                        console.log(`      ✅ Turno ${turnoNombre} validado exitosamente`);
                        turnosExitosos++;
                        
                    } catch (error) {
                        console.error(`      ❌ Error en turno ${turnoNombre}:`, error);
                        turnosConError++;
                    }
                }
                
                // Ejecutar SP final del semestre si todos los turnos están validados
                if (todosTurnosValidados(semestreId)) {
                    console.log(`   🚀 Ejecutando SP final para ${semestreNombre}...`);
                    
                    try {
                        await ejecutarSPFinalSemestre(semestreId, periodo, programa, modalidad, semestreId);
                        console.log(`   ✅ ${semestreNombre} consolidado exitosamente`);
                        detallesProcesamiento.push(`✅ ${semestreNombre}: ${turnosExitosos} turnos validados y consolidado`);
                        semestresExitosos++;
                    } catch (error) {
                        console.error(`   ❌ Error al consolidar ${semestreNombre}:`, error);
                        detallesProcesamiento.push(`⚠️ ${semestreNombre}: Turnos validados pero error en consolidación`);
                        semestresConError++;
                    }
                } else {
                    console.log(`   ⚠️ ${semestreNombre}: No todos los turnos pudieron validarse`);
                    detallesProcesamiento.push(`⚠️ ${semestreNombre}: ${turnosExitosos} de ${turnosDelSemestre.length} turnos validados`);
                    semestresConError++;
                }
            }
            
            // Mensaje final con resumen
            const mensajeResumen = 
                `🎉 VALIDACIÓN MASIVA COMPLETADA\n\n` +
                `✅ Semestres exitosos: ${semestresExitosos}\n` +
                `⚠️ Semestres con errores: ${semestresConError}\n\n` +
                `📋 DETALLES:\n` +
                detallesProcesamiento.join('\n') +
                `\n\n✅ Proceso de validación masiva finalizado.`;
            
            await Swal.fire({
                icon: 'success',
                title: '✅ Validación Masiva Completada',
                html: mensajeResumen.replace(/\n/g, '<br>'),
                confirmButtonText: 'Entendido',
                width: '600px'
            });
            console.log('✅ VALIDACIÓN MASIVA COMPLETADA');
            
            // ===== EJECUTAR SP DE FINALIZAR CAPTURA MATRÍCULA =====
            // Si todos los semestres fueron exitosos, ejecutar SP_Finaliza_Captura_Matricula
            if (semestresExitosos > 0 && semestresConError === 0) {
                console.log('\n🚀 === EJECUTANDO SP_Finaliza_Captura_Matricula ===');
                btnValidarTodos.textContent = '⏳ Finalizando captura completa...';
                
                try {
                    console.log('📋 Llamando a endpoint /matricula/ejecutar_sp_finalizar_captura...');
                    console.log(`   Periodo: ${periodo}, Programa: ${programa}, Modalidad: ${modalidad}`);
                    
                    const responseFinalizacion = await fetch('/matricula/ejecutar_sp_finalizar_captura', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            periodo: periodo,
                            programa: programa,
                            modalidad: modalidad
                        })
                    });
                    
                    const resultadoFinalizacion = await responseFinalizacion.json();
                    console.log('📥 Respuesta del endpoint:', resultadoFinalizacion);
                    
                    if (resultadoFinalizacion.success) {
                        console.log('✅ SP_Finaliza_Captura_Matricula ejecutado exitosamente!');
                        await Swal.fire({
                            icon: 'success',
                            title: '🎉 ¡CAPTURA COMPLETA FINALIZADA!',
                            html: '<strong>✅ Todos los semestres validados</strong><br>' +
                                `✅ ${resultadoFinalizacion.semestres_validados} semestres verificados<br>` +
                                '✅ SP_Finaliza_Captura_Matricula ejecutado<br>' +
                                '🚦 Semáforo actualizado a COMPLETADO<br><br>' +
                                '¡Proceso de captura de matrícula COMPLETADO!',
                            confirmButtonText: 'Entendido',
                            timer: 6000,
                            timerProgressBar: true
                        });
                    } else {
                        console.warn('⚠️ No se pudo ejecutar SP_Finaliza_Captura_Matricula:', resultadoFinalizacion.error);
                        await Swal.fire({
                            icon: 'warning',
                            title: 'Validación completada con observaciones',
                            html: `Semestres validados correctamente, pero:<br><br>${resultadoFinalizacion.error}<br><br>` +
                                  'Puede que el SP ya haya sido ejecutado previamente o falten semestres por validar.',
                            confirmButtonText: 'Entendido'
                        });
                    }
                } catch (error) {
                    console.error('❌ Error al ejecutar SP_Finaliza_Captura_Matricula:', error);
                    await Swal.fire({
                        icon: 'warning',
                        title: 'Error en SP final',
                        html: `Semestres validados correctamente.<br><br>Error al ejecutar SP final:<br>${error.message}<br><br>Verifique el estado manualmente.`,
                        confirmButtonText: 'Entendido'
                    });
                }
            }
            
            // Actualizar colores de pestañas
            actualizarColoresPestanas();
            
            // Recargar la vista al primer semestre
            if (semestresDisponiblesSP.length > 0) {
                seleccionarSemestre(semestresDisponiblesSP[0]);
            }
            
        } catch (error) {
            console.error('❌ Error en validación masiva:', error);
            await Swal.fire({
                icon: 'error',
                title: 'Error en validación masiva',
                text: error.message,
                confirmButtonText: 'Entendido'
            });
        } finally {
            btnValidarTodos.textContent = textoOriginal;
            btnValidarTodos.disabled = false;
        }
    }
    
    // Función para validar y finalizar la captura del semestre actual - NUEVO SISTEMA DE DOS FASES
    async function validarCapturaSemestre() {
        // Cargar turnos validados desde localStorage
        cargarTurnosValidadosDeLocalStorage();
        
        // Obtener el semestre actual
        let semestreActual = parseInt(document.getElementById('semestre').value);
        const semestreNombre = semestresMap[semestreActual] || `Semestre ${semestreActual}`;
        
        const inputs = document.querySelectorAll('input.input-matricula-nueva');
        
        // Aplicar reglas de habilitación/deshabilitación al semestre actual
        updateInputsBySemestre(semestreActual);
        
        // Rellenar campos vacíos con '0'
        let camposRellenados = 0;
        inputs.forEach((input) => {
            if (input.disabled) return;
            const currentValue = input.value;
            const isEmpty = !currentValue || currentValue.trim() === '';
            if (isEmpty) {
                input.value = '0';
                input.setAttribute('data-auto-filled', 'true');
                camposRellenados++;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
        
        if (camposRellenados > 0) {
            calcularTotales();
        }
        
        const confirmacion = await Swal.fire({
            title: '⚠️ Confirmación requerida',
            html: 'Se llenarán con <strong>ceros</strong> los campos vacíos y los cambios serán <strong>irreversibles</strong>.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, continuar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#dc3545'
        });
        
        if (!confirmacion.isConfirmed) {
            return;
        }
        
        const periodo = document.getElementById('periodo').value;
        let programa = document.getElementById('programa').value;
        const modalidad = document.getElementById('modalidad').value;
        const semestre = document.getElementById('semestre').value;
        const totalGruposSemestre = totalGruposPorSemestre[semestreActual] || 0;
        
        const programaSelect = document.getElementById('programa');
        const programaNombre = programaSelect?.selectedOptions[0]?.text || '';
        if (programaNombre.toLowerCase().includes('tronco común')) {
            programa = '1';
        }
        
        if (!periodo || !programa || !modalidad || !semestre) {
            await Swal.fire({
                icon: 'warning',
                title: 'Filtros incompletos',
                text: 'Por favor, complete todos los filtros antes de validar.',
                confirmButtonText: 'Entendido'
            });
            return;
        }
        
        const btnValidar = document.getElementById('btn-finalizar-captura');
        const textoOriginal = btnValidar ? btnValidar.textContent : '🎯 Finalizar Semestre';
        if (btnValidar) {
            btnValidar.textContent = '⏳ Finalizando semestre...';
            btnValidar.disabled = true;
        }
        mostrarOverlayCarga('Finalizando semestre...', 'Guardando y procesando todos los turnos');
        
        try {
            totalGruposPorSemestre[semestreActual] = totalGruposSemestre;
            guardarTotalGruposEnLocalStorage();
            
            const datosPorTurno = {};
            inputs.forEach(input => {
                if (!input.disabled) {
                    const tipoIngreso = input.getAttribute('data-tipo-ingreso');
                    const grupoEdad = input.getAttribute('data-grupo-edad');
                    const sexo = input.getAttribute('data-sexo');
                    const turnoId = parseInt(input.getAttribute('data-turno'));
                    if (isNaN(turnoId)) return;
                    // Siempre incluir todos los inputs habilitados:
                    // inputs vacíos se tratan como 0 para garantizar que queden
                    // registrados en Temp_Matricula aunque no hayan sido llenados.
                    const inputValue = (input.value ?? '').trim();
                    const valor = inputValue !== '' ? (parseInt(inputValue) || 0) : 0;
                    if (valor >= 0) {
                        const key = `${tipoIngreso}_${grupoEdad}_${sexo}`;
                        if (!datosPorTurno[turnoId]) datosPorTurno[turnoId] = {};
                        const claveTurno = `${parseInt(semestreActual)}_${turnoId}`;
                        const totalGruposTurno = totalGruposPorSemestreYTurno[claveTurno] || 0;
                        datosPorTurno[turnoId][key] = {
                            tipo_ingreso: tipoIngreso,
                            grupo_edad: grupoEdad,
                            sexo: sexo,
                            matricula: valor,
                            salones: totalGruposTurno
                        };
                    }
                }
            });
            
            const turnosIds = Object.keys(datosPorTurno);
            if (turnosIds.length === 0) {
                await Swal.fire({
                    icon: 'warning',
                    title: 'Sin datos',
                    text: 'No se encontraron datos válidos para validar.',
                    confirmButtonText: 'Entendido'
                });
                return;
            }
            
            // Guardar datos en Temp_Matricula por turno
            for (const turnoId of turnosIds) {
                const claveTurno = `${parseInt(semestreActual)}_${turnoId}`;
                const totalGruposTurno = totalGruposPorSemestreYTurno[claveTurno] || 0;
                const data = {
                    periodo: periodo,
                    programa: programa,
                    semestre: semestre,
                    modalidad: modalidad,
                    turno: turnoId,
                    total_grupos: totalGruposTurno,
                    datos_matricula: datosPorTurno[turnoId]
                };
                const saveResponse = await fetch('/matricula/guardar_captura_completa', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const saveResult = await saveResponse.json();
                if (saveResult.error) {
                    throw new Error(saveResult.error);
                }
            }
            
            // Preparar turnos
            Swal.update({ title: 'Finalizando semestre...', text: 'Organizando datos por turno' });
            if (btnValidar) btnValidar.textContent = '⏳ Finalizando semestre...';
            for (const turnoId of turnosIds) {
                const claveTurnoPrep = `${parseInt(semestreActual)}_${turnoId}`;
                const totalGruposTurnoPrep = totalGruposPorSemestreYTurno[claveTurnoPrep] || 0;
                const prepararResponse = await fetch('/matricula/preparar_turno', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        periodo: periodo,
                        programa: programa,
                        modalidad: modalidad,
                        semestre: semestre,
                        turno: turnoId,
                        total_grupos: totalGruposTurnoPrep
                    })
                });
                const prepararResult = await prepararResponse.json();
                if (prepararResult.error) {
                    throw new Error(prepararResult.error);
                }
                marcarTurnoComoValidado(semestreActual, parseInt(turnoId));
            }
            
            // Bloquear inputs del semestre
            inputs.forEach(input => {
                input.disabled = true;
                input.classList.add('input-disabled');
            });
            
            const btnGuardar = document.getElementById('btn-guardar-matricula');
            if (btnGuardar) {
                btnGuardar.disabled = true;
                btnGuardar.classList.add('input-disabled');
            }
            
            // Ejecutar el SP de actualización definitiva si todos los turnos están validados
            if (todosTurnosValidados(semestreActual)) {
                await ejecutarSPFinalSemestre(semestreActual, periodo, programa, modalidad, semestre);
            }
            
            if (btnValidar) {
                btnValidar.disabled = true;
                btnValidar.classList.add('input-disabled');
                btnValidar.textContent = '✅ Semestre Finalizado';
            }
            
        } catch (error) {
            console.error('❌ Error en la validación del semestre:', error);
            await Swal.fire({
                icon: 'error',
                title: 'Error al finalizar',
                text: error.message,
                confirmButtonText: 'Entendido'
            });
        } finally {
            ocultarOverlayCarga();
            if (!todosTurnosValidados(semestreActual)) {
                if (btnValidar) {
                    btnValidar.textContent = textoOriginal;
                    btnValidar.disabled = false;
                }
            }
        }
    }

    // Agregar validación solo números en inputs
    document.addEventListener('DOMContentLoaded', function() {
        document.addEventListener('input', function(e) {
            if (e.target.classList.contains('input-matricula-nueva')) {
                // Solo permitir números
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
            }
        });
    });
    
    // ===== FUNCIONES PARA MODO DE VISTA SEGÚN ROL =====
    
    // Aplicar modo de vista (solo lectura para roles de validación)
    function aplicarModoVista() {
        console.log(`🔐 Aplicando modo de vista: ${modoVista}`);
        
        if (!esCapturista) {
            console.log('👁️ Modo validación activado - Deshabilitando edición de matrícula');
            
            // Deshabilitar TODOS los inputs de matrícula
            const inputs = document.querySelectorAll('input.input-matricula-nueva');
            inputs.forEach(input => {
                input.disabled = true;
                input.classList.add('input-disabled');
                input.style.backgroundColor = '#f0f0f0';
                input.style.cursor = 'not-allowed';
                // Eliminar cualquier evento que pudiera habilitar el input
                input.readOnly = true;
            });
            
            // Deshabilitar inputs de Total Grupos por turno
            const totalGruposTurnos = document.querySelectorAll('.input-total-grupos-turno');
            totalGruposTurnos.forEach(tg => {
                tg.disabled = true;
                tg.classList.add('input-disabled');
                tg.style.backgroundColor = '#f0f0f0';
                tg.style.cursor = 'not-allowed';
                tg.readOnly = true;
            });
            
            // Deshabilitar botones de acción del capturista si existen
            const btnGuardar = document.getElementById('btn-guardar-matricula');
            const btnLimpiar = document.getElementById('btn-limpiar-formulario');
            const btnValidarCaptura = document.getElementById('btn-validar-matricula');
            
            if (btnGuardar) {
                btnGuardar.style.display = 'none';
            }
            if (btnLimpiar) {
                btnLimpiar.style.display = 'none';
            }
            if (btnValidarCaptura) {
                btnValidarCaptura.style.display = 'none';
            }
            
            // ⚠️ IMPORTANTE: Los filtros (programa, modalidad y turnos) PERMANECEN HABILITADOS
            // para que roles 4, 5, 6, 7, 8 puedan filtrar diferentes programas/modalidades/turnos
            console.log('✅ Filtros de programa, modalidad y turnos habilitados para validación');
            
            // Los botones de navegación de turno PERMANECEN habilitados para roles de validación
            // para que puedan revisar diferentes turnos
            
            console.log('✅ Vista configurada en modo solo lectura (filtros y turnos activos)');
            console.log('🔒 TODOS los inputs están permanentemente deshabilitados para roles de validación');
        }
    }
    
    // Función para validar el semestre (roles de validación)
    async function validarSemestre() {
        // Verificar si el botón está deshabilitado
        const btnValidar = document.getElementById('btn-validar-semestre');
        if (btnValidar.disabled) {
            await Swal.fire({
                icon: 'warning',
                title: 'Acción no permitida',
                text: 'Ya has validado o rechazado esta matrícula. No puedes realizar esta acción nuevamente.',
                confirmButtonText: 'Entendido'
            });
            return;
        }
        
        // Verificar si hay un SP en ejecución
        if (!verificarSiPuedeContinuar()) {
            return;
        }
        
        const periodo = document.getElementById('periodo').value;
        const programa = document.getElementById('programa').value;
        const modalidad = document.getElementById('modalidad').value;
        const semestre = document.getElementById('semestre').value;
        
        const semestreNombre = semestresMap[parseInt(semestre)] || `Semestre ${semestre}`;
        
        const confirmacion = await Swal.fire({
            title: '¿Está seguro que desea VALIDAR?',
            html: 'Esta acción marcará el semestre como <strong>aprobado</strong> y bloqueará cualquier modificación futura.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, validar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#dc3545'
        });
        
        if (!confirmacion.isConfirmed) {
            console.log('❌ Usuario canceló la validación');
            return;
        }
        
        // Mostrar overlay
        mostrarOverlayCarga('Validando Matrícula...', 'Procesando y finalizando el semestre');
        
        try {
            console.log('🔄 Enviando validación al servidor...');
            
            const response = await fetch('/matricula/validar_semestre_rol', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    periodo: periodo
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Matrícula validada exitosamente:', data);
                await Swal.fire({
                    title: '¡Validado!',
                    html: `${data.mensaje}<br><br>` +
                        `<b>Validado por:</b> ${data.data.validado_por}<br>` +
                        `<b>Unidad Académica:</b> ${data.data.unidad_academica}<br>` +
                        `<b>Periodo:</b> ${data.data.periodo}<br>` +
                        `<b>Fecha:</b> ${new Date(data.data.fecha_validacion).toLocaleString()}<br><br>` +
                        `La matrícula ha sido aprobada completamente.`,
                    icon: 'success',
                    timer: 2500,
                    showConfirmButton: true
                });
                
                location.reload();
            } else {
                await Swal.fire({
                    title: 'Error',
                    text: data.error || 'No se pudo completar la validación',
                    icon: 'error'
                });
            }
        } catch (error) {
            console.error('❌ Error en validarSemestre:', error);
            await Swal.fire({
                title: 'Error',
                text: `Error al validar: ${error.message}`,
                icon: 'error'
            });
        } finally {
            ocultarOverlayCarga();
        }
    }
    
    // Función para rechazar el semestre (roles de validación) - Abre panel desplegable
    async function rechazarSemestre() {
        // Verificar si el botón está deshabilitado
        const btnRechazar = document.getElementById('btn-rechazar-semestre');
        if (btnRechazar.disabled) {
            await Swal.fire({
                icon: 'warning',
                title: 'Acción no permitida',
                text: 'Ya has validado o rechazado esta matrícula. No puedes realizar esta acción nuevamente.',
                confirmButtonText: 'Entendido'
            });
            return;
        }
        
        const panel = document.getElementById('panel-rechazo');
        const textarea = document.getElementById('motivo-rechazo-panel');
        const contador = document.getElementById('contador-caracteres-panel');
        
        // Toggle: si ya está abierto, cerrarlo
        if (panel.style.display === 'block') {
            cerrarPanelRechazo();
            return;
        }
        
        // Limpiar textarea y reiniciar contador
        textarea.value = '';
        contador.textContent = '0';
        
        // Mostrar panel con animación
        panel.style.display = 'block';
        
        // Pequeño delay para que la animación se vea
        setTimeout(() => {
            panel.classList.add('panel-abierto');
        }, 10);
        
        // Focus en el textarea
        setTimeout(() => textarea.focus(), 300);
        
        // Actualizar contador de caracteres
        textarea.oninput = function() {
            contador.textContent = this.value.length;
            
            // Cambiar color si se acerca al límite
            if (this.value.length > 230) {
                contador.style.color = '#dc3545';
                contador.style.fontWeight = 'bold';
            } else {
                contador.style.color = '#666';
                contador.style.fontWeight = 'normal';
            }
        };
        
        // Scroll suave hacia el panel
        setTimeout(() => {
            panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 350);
    }
    
    // Función para actualizar el contador de caracteres del panel
    function actualizarContadorPanel() {
        const textarea = document.getElementById('motivo-rechazo-panel');
        const contador = document.getElementById('contador-caracteres-panel');
        contador.textContent = textarea.value.length;
    }
    
    // Función para cerrar el panel de rechazo
    function cerrarPanelRechazo() {
        const panel = document.getElementById('panel-rechazo');
        const textarea = document.getElementById('motivo-rechazo-panel');
        
        // Quitar clase de animación
        panel.classList.remove('panel-abierto');
        
        // Limpiar textarea y contador
        textarea.value = '';
        document.getElementById('contador-caracteres-panel').textContent = '0';
        
        // Esperar a que termine la animación antes de ocultar
        setTimeout(() => {
            panel.style.display = 'none';
        }, 300);
    }
    
    // Función para confirmar el rechazo desde el panel
    async function confirmarRechazoPanel() {
        const periodo = document.getElementById('periodo').value;
        const textarea = document.getElementById('motivo-rechazo-panel');
        const motivo = textarea.value.trim();
        
        // Validar que hay motivo
        if (!motivo) {
            await Swal.fire({
                icon: 'warning',
                title: 'Motivo requerido',
                text: 'Debe ingresar un motivo para el rechazo',
                confirmButtonText: 'Entendido'
            });
            textarea.focus();
            return;
        }
        
        if (motivo.length < 10) {
            await Swal.fire({
                icon: 'warning',
                title: 'Motivo muy corto',
                text: 'El motivo debe tener al menos 10 caracteres para ser descriptivo',
                confirmButtonText: 'Entendido'
            });
            textarea.focus();
            return;
        }
        
        // Deshabilitar botón para evitar doble click
        const btnConfirmar = document.querySelector('.btn-confirmar-rechazo');
        btnConfirmar.disabled = true;
        btnConfirmar.textContent = '⏳ Procesando...';
        
        try {
            const response = await fetch('/matricula/rechazar_semestre_rol', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    periodo: periodo,
                    motivo: motivo
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Cerrar panel
                cerrarPanelRechazo();
                await Swal.fire({
                    icon: 'success',
                    title: '✅ Matrícula Rechazada Exitosamente',
                    html: `<strong>Rechazado por:</strong> ${data.data.rechazado_por}<br>` +
                          `<strong>Unidad Académica:</strong> ${data.data.unidad_academica}<br>` +
                          `<strong>Periodo:</strong> ${data.data.periodo}<br>` +
                          `<strong>Motivo:</strong> ${data.data.motivo}<br>` +
                          `<strong>Fecha:</strong> ${new Date(data.data.fecha_rechazo).toLocaleString()}<br><br>` +
                          `El capturista será notificado para realizar las correcciones necesarias.`,
                    confirmButtonText: 'Entendido',
                    timer: 5000,
                    timerProgressBar: true
                });
                
                // Recargar la página para reflejar los cambios
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                throw new Error(data.error || 'Error desconocido al rechazar');
            }
            
        } catch (error) {
            console.error('❌ Error al rechazar la matrícula:', error);
            await Swal.fire({
                icon: 'error',
                title: 'Error al rechazar',
                text: error.message,
                confirmButtonText: 'Entendido'
            });
            
            // Rehabilitar botón en caso de error
            btnConfirmar.disabled = false;
            btnConfirmar.textContent = '✅ Confirmar Rechazo';
        }
    }

// ---- Script extra (antes inline) ----

    // Función para actualizar la matrícula definitiva usando el SP
    async function actualizarMatricula() {
        // Confirmar la acción
        const confirmacion = await Swal.fire({
            title: '🔄 ¿Actualizar matrícula definitiva?',
            html: '<p><strong>⚠️ Esta acción:</strong></p>' +
                  '<ul style="text-align: left; margin-left: 20px;">' +
                  '<li>Transferirá todos los datos de la tabla temporal a la matrícula oficial</li>' +
                  '<li>Limpiará la tabla temporal</li>' +
                  '<li>No se puede deshacer</li>' +
                  '</ul>',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, actualizar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#dc3545'
        });
        
        if (!confirmacion.isConfirmed) {
            return;
        }

        const updateBtn = document.querySelector('.btn-success');
        const originalText = updateBtn.textContent;
        updateBtn.textContent = '⏳ Actualizando...';
        updateBtn.disabled = true;

        // Obtener período desde el campo hidden
        const periodo = document.getElementById('periodo').value;

        fetch('/matricula/actualizar_matricula', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                periodo: periodo
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            if (data.warning) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Advertencia',
                    text: data.warning,
                    confirmButtonText: 'Entendido'
                });
                return;
            }
            
            // Mostrar mensaje de éxito detallado
            Swal.fire({
                icon: 'success',
                title: '✅ ' + data.mensaje,
                html: `<strong>📊 Registros procesados:</strong> ${data.registros_procesados}<br>` +
                      `<strong>🧹 Tabla temporal limpiada:</strong> ${data.temp_matricula_limpiada ? 'Sí' : 'No'}<br>` +
                      `<strong>👤 Usuario:</strong> ${data.usuario}<br>` +
                      `<strong>📅 Período:</strong> ${data.periodo}<br>` +
                      `<strong>⏰ Fecha:</strong> ${new Date(data.timestamp).toLocaleString()}`,
                confirmButtonText: 'Entendido',
                timer: 5000,
                timerProgressBar: true
            }).then(() => {
                location.reload();
            });
        })
        .catch(error => {
            console.error('Error al actualizar matrícula:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error al actualizar',
                text: error.message,
                confirmButtonText: 'Entendido'
            });
        })
        .finally(() => {
            // Restaurar botón
            updateBtn.textContent = originalText;
            updateBtn.disabled = false;
        });
    }
    
    // ¡Nombre corregido a actualizarInforme!
    function actualizarInforme() {
        const inputs = document.querySelectorAll('input.input-matricula-nueva');

        // 1. Estructura de totales (usando IDs como clave para que coincida con data-tipo-ingreso)
        const totalesTipoIngreso = {
            '1': { M: 0, F: 0, label: 'Nuevo Ingreso' },
            '2': { M: 0, F: 0, label: 'Reingreso' },
            '3': { M: 0, F: 0, label: 'Repetidores' }
        };
        
        // Almacenará { 'id_grupo_edad': { M: 0, F: 0, label: '18', sortKey: 18 } }
        const totalesGrupoEdad = {};

        // PASO 1: Recolectar y sumar los datos
        inputs.forEach(input => {
            const valor = parseInt(input.value) || 0;
            const tipoIngresoId = input.getAttribute('data-tipo-ingreso');
            const grupoEdadId = input.getAttribute('data-grupo-edad');
            const sexo = input.getAttribute('data-sexo'); // 'M' o 'F'

            // 2. Sumar por tipo de ingreso (ahora funciona)
            if (totalesTipoIngreso[tipoIngresoId]) {
                totalesTipoIngreso[tipoIngresoId][sexo] += valor;
            }

            // 3. Sumar por grupo de edad (corregido)
            if (!totalesGrupoEdad[grupoEdadId]) {
                // Si el grupo de edad no existe, lo inicializamos
                // Obtenemos la etiqueta de la primera celda (Edad) en la fila del input
                const label = input.closest('tr').querySelector('td:first-child').textContent;
                
                // Extraemos una clave numérica para ordenar (ej. '18' de '18', '<18' es 0)
                let sortKey = 99;
                if (label.startsWith('<')) {
                    sortKey = 0;
                } else if (label.startsWith('>')) {
                    sortKey = 999;
                } else {
                    sortKey = parseInt(label.match(/\d+/)) || 99;
                }

                totalesGrupoEdad[grupoEdadId] = { M: 0, F: 0, label: label, sortKey: sortKey };
            }
            
            // Sumamos el valor
            totalesGrupoEdad[grupoEdadId][sexo] += valor;
        });

        // PASO 2: Renderizar las tablas (FUERA del bucle forEach)

        // 4. Renderizar tabla TIPO DE INGRESO
        const tablaTipoBody = document.querySelector('#informe-tipo-ingreso-table tbody');
        if (tablaTipoBody) {
            let htmlTipo = '';
            for (const key in totalesTipoIngreso) {
                const data = totalesTipoIngreso[key];
                const totalFila = data.M + data.F;
                
                // Opcional: solo mostrar filas que tengan datos
                if (totalFila > 0) {
                    htmlTipo += `<tr>
                        <td>${data.label}</td>
                        <td>${data.M}</td>
                        <td>${data.F}</td>
                        <td>${totalFila}</td>
                    </tr>`;
                }
            }
            tablaTipoBody.innerHTML = htmlTipo || '<tr><td colspan="4">Sin datos</td></tr>';
        } else {
            console.error("No se encontró el tbody de informe-tipo-ingreso-table");
        }

        // 5. Renderizar tabla GRUPO DE EDAD
        const tablaEdadBody = document.querySelector('#informe-grupo-edad-table tbody');
        if (tablaEdadBody) {
            let htmlEdad = '';

            // 6. Ordenar los grupos de edad usando la 'sortKey' que creamos
            const edadesOrdenadas = Object.values(totalesGrupoEdad).sort((a, b) => {
                return a.sortKey - b.sortKey;
            });

            // 7. Generar el HTML
            edadesOrdenadas.forEach(data => {
                const totalFila = data.M + data.F;
                // Opcional: solo mostrar filas que tengan datos
                if (totalFila > 0) {
                    htmlEdad += `<tr>
                        <td>${data.label}</td>
                        <td>${data.M}</td>
                        <td>${data.F}</td>
                        <td>${totalFila}</td>
                    </tr>`;
                }
            });
            
            tablaEdadBody.innerHTML = htmlEdad || '<tr><td colspan="4">Sin datos</td></tr>';
        } else {
            console.error("No se encontró el tbody de informe-grupo-edad-table");
        }
    }

    /* ========================================
       FUNCIONES DEL BANNER DE RECHAZO Y NOTIFICACIONES
       ======================================== */
    
    /**
     * Cerrar el banner de rechazo (ocultarlo temporalmente)
     * El banner se puede volver a ver desde la campanita de notificaciones
     */
    function cerrarBannerRechazo() {
        const banner = document.getElementById('banner-rechazo');
        if (banner) {
            banner.style.animation = 'slideDownBanner 0.3s ease-out reverse';
            setTimeout(() => {
                banner.style.display = 'none';
            }, 300);
        }
    }
    
    /**
     * Mostrar el banner de rechazo (desde la campanita de notificaciones)
     */
    function mostrarBannerRechazo() {
        const banner = document.getElementById('banner-rechazo');
        if (banner) {
            banner.style.display = 'flex';
            banner.style.animation = 'slideDownBanner 0.5s ease-out';
            
            // Cerrar el panel de notificaciones
            const panel = document.getElementById('panel-notificaciones');
            if (panel) {
                panel.style.display = 'none';
            }
            
            // Hacer scroll suave hasta el banner
            setTimeout(() => {
                banner.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }
    
    /**
     * Toggle (abrir/cerrar) el panel de notificaciones
     */
    function togglePanelNotificaciones() {
        const panel = document.getElementById('panel-notificaciones');
        if (panel) {
            if (panel.style.display === 'none' || panel.style.display === '') {
                // Abrir panel
                panel.style.display = 'block';
            } else {
                // Cerrar panel
                panel.style.display = 'none';
            }
        }
    }
    
    // Cerrar panel de notificaciones al hacer clic fuera
    document.addEventListener('click', function(event) {
        const panel = document.getElementById('panel-notificaciones');
        const btnNotificaciones = document.querySelector('.btn-notificaciones');
        
        // Si el panel está abierto y el clic NO fue en el panel ni en el botón
        if (panel && panel.style.display === 'block') {
            if (!panel.contains(event.target) && !btnNotificaciones.contains(event.target)) {
                panel.style.display = 'none';
            }
        }
    });