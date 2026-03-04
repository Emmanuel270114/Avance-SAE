# SAE - Sistema de Administración Escolar

Sistema web desarrollado con FastAPI y Jinja2 para la gestión de usuarios académicos.

## Características
- Gestión de usuarios por roles
- Recuperación de contraseñas vía email
- Filtrado de programas por unidad académica
- Panel de administración

## Instalación
1. Clonar repositorio
2. Crear entorno virtual: `python3 -m venv venv`
3. Activar entorno: 
   - **macOS/Linux**: `source venv/bin/activate`
   - **Windows**: `venv\Scripts\activate`
4. Instalar dependencias: `pip install -r requirements.txt`
5. Configurar variables de entorno (.env)
6. Ejecutar: `python -m uvicorn backend.main:app --reload`

## Variables de entorno requeridas
Ver `.env.example` para la configuración completa.
Sistema web desarrollado con FastAPI y Jinja2 para la gestión de usuarios académicos, unidades académicas y programas educativos.

## 📋 Requisitos del Sistema

### Software Necesario

#### 1. Python 3.8 o superior

- **Descargar:** [python.org](https://www.python.org/downloads/)
- **Verificar instalación:**

  ```bash
  python --version
  ```

#### 2. Microsoft SQL Server ODBC Driver 17

- **Windows:** Descargar desde [Microsoft](https://learn.microsoft.com/es-es/sql/connect/odbc/download-odbc-driver-for-sql-server)
- **Verificar instalación:** Ir a Panel de Control → Herramientas administrativas → Orígenes de datos ODBC (64 bits)

#### 3. Git (opcional, para clonar el repositorio)

- **Descargar:** [git-scm.com](https://git-scm.com/)

### Base de Datos

- **SQL Server 2016** o superior
- **Acceso a la base de datos** con permisos de lectura/escritura
- **Configuración de red** para conexiones remotas (si aplica)

### Servidor SMTP (para recuperación de contraseñas)

- **Gmail:** Requiere contraseña de aplicación con 2FA activado
- **Outlook/Hotmail:** Compatible con SMTP
- **Servidor corporativo:** Verificar configuración SMTP

---

## 🚀 Instalación

### Paso 1: Obtener el Código

#### Opción A: Clonar desde GitHub
```bash
git clone https://github.com/Emmanuel270114/SAE.git
cd SAE
```

#### Opción B: Descargar ZIP
1. Ir al repositorio en GitHub
2. Clic en "Code" → "Download ZIP"
3. Extraer el archivo en la carpeta deseada

### Paso 2: Configurar Entorno Virtual

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate
```

### Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Dependencias principales:**

- FastAPI (Framework web)
- SQLAlchemy (ORM para base de datos)
- Jinja2 (Motor de plantillas)
- bcrypt (Encriptación de contraseñas)
- pydantic-settings (Configuración)
- pyodbc (Conexión a SQL Server)
- uvicorn (Servidor ASGI)

### Paso 4: Configuración de Variables de Entorno

1. **Copiar archivo de ejemplo:**
   ```bash
   copy .env.example .env
   ```

2. **Editar archivo `.env`** con tu configuración:

```env
# Configuración de Base de Datos
DB_USER=tu_usuario_sql
DB_PASSWORD=tu_contraseña_sql
DB_HOST=servidor_sql_o_ip
DB_PORT=1433
DB_NAME=nombre_base_datos
DB_DRIVER=ODBC Driver 17 for SQL Server

# Configuración SMTP para Correos
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=tu_correo@gmail.com
SMTP_PASS=tu_contraseña_de_aplicacion
SMTP_FROM=Sistema SAE <no-reply@tudominio.com>
SMTP_SUBJECT_PREFIX=SAE
```

### Paso 5: Verificar Configuración

**Probar conexión a la base de datos:**
```bash
python -c "from backend.database.connection import get_db; print('Conexión exitosa')"
```

---

## 🎯 Ejecución del Proyecto

### Modo Desarrollo (Recomendado para pruebas)

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Modo Producción

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Acceder al Sistema

- **URL Local:** <http://localhost:8000>
- **Login:** <http://localhost:8000/login>
- **Documentación API:** <http://localhost:8000/docs>
- **Red Local:** <http://[tu-ip-local]:8000>

---

## 🔧 Configuración Adicional

### Configurar Gmail para SMTP

1. **Activar verificación en dos pasos** en tu cuenta Google
2. **Generar contraseña de aplicación:**
   - Ir a Configuración de Google → Seguridad
   - Contraseñas de aplicaciones
   - Crear nueva contraseña para "SAE"
3. **Usar la contraseña generada** en `SMTP_PASS`

### Configurar Firewall (Para acceso desde otras computadoras)

**Windows:**
```bash
# Ejecutar como Administrador
netsh advfirewall firewall add rule name="SAE-FastAPI" dir=in action=allow protocol=TCP localport=8000
```

**O manualmente:**
- Panel de Control → Sistema y seguridad → Firewall de Windows Defender
- Configuración avanzada → Reglas de entrada → Nueva regla
- Puerto → TCP → 8000 → Permitir conexión

---

## 📱 Funcionalidades del Sistema

### Gestión de Usuarios

- ✅ Registro de usuarios con validación
- ✅ Login con autenticación por cookies
- ✅ Roles: Superadministrador y Usuario normal
- ✅ Edición de usuarios (solo superadmin)

### Recuperación de Acceso

- ✅ Recuperar nombre de usuario por email
- ✅ Resetear contraseña con envío por correo
- ✅ Cambio de contraseña autenticado
- ✅ Bitácora de eventos de seguridad

### Programas Académicos

- ✅ Visualización por Unidad Académica
- ✅ Filtrado dinámico para superadministrador
- ✅ Carga optimizada con AJAX

---

## 🔍 Solución de Problemas

### Error: "No module named 'backend'"
```bash
# Verificar que estás en el directorio correcto
pwd
# Debe mostrar la ruta donde está el proyecto

# Verificar que existe la carpeta backend
ls backend
```

### Error: "No module named 'pydantic_settings'"
```bash
pip install pydantic-settings
```

### Error de conexión a base de datos
1. Verificar que SQL Server esté ejecutándose
2. Comprobar credenciales en `.env`
3. Verificar conectividad de red
4. Confirmar que el driver ODBC esté instalado

### Error de SMTP
1. Verificar credenciales de email
2. Comprobar configuración de firewall
3. Para Gmail: usar contraseña de aplicación

---

## 📊 Estructura del Proyecto

```
SAE/
├── backend/
│   ├── api/           # Endpoints de la API
│   ├── core/          # Configuración central
│   ├── crud/          # Operaciones de base de datos
│   ├── database/      # Modelos y conexión DB
│   ├── schemas/       # Esquemas Pydantic
│   ├── services/      # Lógica de negocio
│   ├── tests/         # Pruebas del sistema
│   └── utils/         # Utilidades (email, seguridad)
├── frontend/
│   ├── static/css/    # Archivos CSS
│   └── Templates/     # Plantillas Jinja2
├── .env               # Variables de entorno (NO subir)
├── .env.example       # Plantilla de configuración
├── requirements.txt   # Dependencias Python
└── README.md         # Este archivo
```

---

## 🚨 Notas de Seguridad

- **NUNCA** subas el archivo `.env` al repositorio
- Usa **contraseñas seguras** para la base de datos
- Activa **2FA** en cuentas de correo
- Mantén **actualizadas** las dependencias
- Configura **HTTPS** en producción

---

## 🔄 Actualizaciones Futuras

- [ ] Token de expiración para reset de contraseña
- [ ] Integración con servicios de correo transaccional
- [ ] Autenticación JWT opcional
- [ ] Panel de administración avanzado
- [ ] API REST completa
