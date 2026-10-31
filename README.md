# aws-url-shortener

Acortador de enlaces que desarrollé y desplegué en AWS como proyecto del midterm. Integra tres servicios: **Amazon S3** (interfaz web), **Amazon EC2** (API con FastAPI) y **Amazon DynamoDB** (base de datos).

## Arquitectura

```
Navegador ──> S3 (HTML/CSS/JS) ──fetch()──> EC2 (FastAPI + Uvicorn) ──Rol IAM──> DynamoDB
```

1. El usuario abre la página alojada en S3 e ingresa una URL.
2. El frontend envía la URL al backend con `fetch()`.
3. FastAPI genera un UUID, lo guarda en DynamoDB junto con la URL y la fecha, y devuelve el enlace corto.
4. Al abrir el enlace corto, FastAPI consulta DynamoDB y responde con una redirección **HTTP 307** hacia la URL original.

El UUID se genera únicamente en el backend. El frontend no genera identificadores ni consulta DynamoDB.

## Estructura del proyecto

```
backend/      main.py (endpoints), database.py (conexión a DynamoDB), schemas.py (validación), requirements.txt
frontend/     index.html, styles.css, app.js
deployment/   shortener.service (systemd), iam-policy.json (política de permisos)
.env.example  plantilla de variables de entorno
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/shorten` | Genera un UUID, guarda el registro en DynamoDB y devuelve el enlace corto |
| GET | `/{short_code}` | Consulta DynamoDB y redirige con 307. Devuelve 404 si el UUID no existe |
| GET | `/urls/{short_code}` | Devuelve en JSON el UUID, la URL original y la fecha de creación. 404 si no existe |

## Configuración en AWS

**DynamoDB.** Creé la tabla `url-shortener` con `short_code` (String) como clave de partición. Cada enlace es un ítem independiente con los atributos `original_url` y `created_at`. Usé capacidad on-demand.

**IAM.** Creé el rol `UrlShortenerEC2Role` y lo asocié a la instancia EC2. Su política solo permite `dynamodb:PutItem` y `dynamodb:GetItem` sobre la tabla `url-shortener`. Boto3 usa las credenciales temporales del rol, por lo que **no hay Access Keys en el código ni en el repositorio**.

**EC2.** Lancé una instancia Amazon Linux 2023, instalé Python 3.11 y Git, cloné este repositorio y creé un entorno virtual con las dependencias. El Security Group permite:
- SSH (puerto 22) restringido a mi IP.
- TCP 8000 para acceder a la API.

La configuración se maneja con variables de entorno en un archivo `.env` (excluido del repositorio):

| Variable | Uso |
|---|---|
| `AWS_REGION` | Región de DynamoDB (`us-east-1`) |
| `TABLE_NAME` | Nombre de la tabla |
| `PUBLIC_BASE_URL` | Base del enlace corto (IP pública de EC2) |
| `ALLOWED_ORIGINS` | Origen del frontend permitido por CORS |

Para que la API siga activa al cerrar la sesión SSH o reiniciar la instancia, la ejecuto como servicio con **systemd** (`deployment/shortener.service`), con reinicio automático.

**S3.** Creé un bucket con alojamiento de sitios web estáticos y subí `index.html`, `styles.css` y `app.js`. Una política de bucket permite la lectura pública de los objetos. El endpoint de sitio web de S3 no ofrece HTTPS por sí solo, por lo que tanto la interfaz como la API funcionan sobre HTTP.

**CORS.** El backend usa `CORSMiddleware` y solo acepta solicitudes del origen del bucket de S3.

## Pruebas realizadas

- Abrir la interfaz desde S3, ingresar una URL válida y obtener el enlace corto.
- Ingresar una URL inválida y ver el mensaje de error en la interfaz.
- Comprobar en DynamoDB que el registro se guardó con su UUID, URL y fecha.
- Abrir el enlace corto y verificar la redirección 307 hacia la URL original.
- Consultar un UUID inexistente y recibir 404.
- Consultar un enlace con `/urls/{short_code}`.
- Reiniciar el servicio (`systemctl restart shortener`) y comprobar que los enlaces siguen funcionando, ya que los datos viven en DynamoDB.

## Ejecución local (opcional)

```bash
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env        # completar valores
set -a; source .env; set +a
cd backend && uvicorn main:app --reload
```

Para probar localmente se necesitan credenciales de AWS configuradas en mi equipo (`aws configure`). Nunca se guardan en el repositorio.

## Seguridad

- Sin Access Keys en el código: se usa el rol IAM de la instancia.
- Permisos mínimos sobre una única tabla.
- `.env` incluido en `.gitignore`.
- SSH limitado a una IP concreta.
