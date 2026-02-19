// Configuración global del frontend
const API_CONFIG = {

    // Protocolo (http o https)
    PROTOCOL: window.location.protocol.replace(':', ''),
    
    // URL completa de la API
    get API_URL() {
        return this.BASE_URL;
    }
};

// Función auxiliar para construir URLs de API
function buildApiUrl(endpoint) {
    // Si el endpoint ya comienza con /, usarlo directamente
    if (endpoint.startsWith('/')) {
        return `${API_CONFIG.API_URL}${endpoint}`;
    }
    return `${API_CONFIG.API_URL}/${endpoint}`;
}

// Exportar para uso global
window.API_CONFIG = API_CONFIG;
window.buildApiUrl = buildApiUrl;
