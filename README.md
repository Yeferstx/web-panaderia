# Sistema de gestión para panadería

Aplicación web para registrar ventas, compras, gastos, inventario y producción de una panadería colombiana.

Tecnologías: Python 3.13, Django 5.2 LTS, PostgreSQL, HTML, CSS y JavaScript sin frameworks.

## Instalación local

Los comandos están para Windows (PowerShell). Si usa Linux o Mac, cambie lo indicado.

### 1. Crear la base de datos en PostgreSQL

Abra **SQL Shell (psql)** o la herramienta de consultas de pgAdmin con el usuario `postgres` y ejecute:

```sql
CREATE USER panaderia_usuario WITH PASSWORD 'clave_local_123' CREATEDB;
CREATE DATABASE panaderia OWNER panaderia_usuario;
```

`CREATEDB` permite que Django cree una base de datos temporal cuando se ejecutan las pruebas.

### 2. Crear el entorno virtual e instalar dependencias

```powershell
cd panaderia
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Linux o Mac: `source .venv/bin/activate`.

### 3. Configurar las variables de entorno

```powershell
copy .env.ejemplo .env
```

Abra `.env` y cambie `SECRET_KEY` por una clave nueva. Para generarla:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Si usó otra contraseña en el paso 1, cámbiela también en `DATABASE_URL`.

### 4. Crear las tablas

```powershell
python manage.py migrate
```

Esto también crea los grupos **Administrador** y **Empleado**.

### 5. Crear el usuario administrador

```powershell
python manage.py createsuperuser
```

### 6. Ejecutar el servidor

```powershell
python manage.py runserver
```

Abra http://127.0.0.1:8000 e ingrese con el usuario creado.

### 7. Ejecutar las pruebas

```powershell
python manage.py test
```

## Roles

| Rol | Puede |
|---|---|
| Administrador | Todo: productos, precios, inventario, compras, gastos, caja, informes y usuarios. |
| Empleado | Registrar ventas y producción. |

Para crear un empleado mientras se construye el módulo de usuarios: entre a http://127.0.0.1:8000/admin/, cree el usuario y agréguelo al grupo **Empleado**.

## Estructura

| Carpeta | Contenido |
|---|---|
| `config/` | Configuración general de Django |
| `core/` | Página de inicio |
| `usuarios/` | Modelo de usuario, ingreso, roles |
| `productos/`, `inventario/`, `ventas/`, `compras/`, `gastos/`, `produccion/`, `reportes/` | Módulos del negocio (se construyen por fases) |
| `templates/` | Plantillas HTML |
| `static/css/`, `static/js/` | Estilos y scripts |
| `docs/` | Decisiones del proyecto |

## Seguridad

- El archivo `.env` tiene las claves y **nunca** se sube a GitHub (está en `.gitignore`).
- Las contraseñas se guardan cifradas por Django.
