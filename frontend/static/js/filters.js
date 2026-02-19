// JavaScript para filtros - Lógica de filtrado en tablas

document.addEventListener('DOMContentLoaded', function() {
    // Elementos de filtros
    const filtro = document.getElementById('filtro-usuarios');
    const filtroUA = document.getElementById('filtro-ua');
    
    // Función principal para aplicar todos los filtros
    function aplicarFiltros() {
        const textoFiltro = filtro ? filtro.value.trim().toLowerCase() : '';
        const uaFiltro = filtroUA ? filtroUA.value : '';
        
        document.querySelectorAll('#tabla-usuarios tbody tr').forEach(tr => {
            const textoFila = tr.innerText.toLowerCase();
            // Acceder correctamente al atributo data-id_unidad
            const idUnidad = tr.getAttribute('data-id_unidad');
            
            const coincideTexto = !textoFiltro || textoFila.includes(textoFiltro);
            // Convertir ambos valores a string para comparación correcta
            const coincideUA = !uaFiltro || String(idUnidad) === String(uaFiltro);
            
            tr.style.display = (coincideTexto && coincideUA) ? '' : 'none';
        });
    }
    
    // Event listeners para filtros
    if (filtro) {
        filtro.addEventListener('input', aplicarFiltros);
    }
    
    if (filtroUA) {
        filtroUA.addEventListener('change', aplicarFiltros);
    }
});