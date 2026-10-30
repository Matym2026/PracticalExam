# aws-url-shortener

Acortador de enlaces con **Amazon S3** (frontend), **Amazon EC2** (backend FastAPI) y **Amazon DynamoDB** (persistencia).

```
Navegador ──> S3 (HTML/CSS/JS) ──fetch()──> EC2 (FastAPI) ──IAM Role──> DynamoDB
```

## Estructura

```
backend/      main.py, database.py, schemas.py, requirements.txt
frontend/     index.html, styles.css, app.js
deployment/   shortener.service, iam-policy.json
.env.example
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/shorten` | Genera UUID, guarda en DynamoDB y devuelve el enlace corto |
| GET | `/{short_code}` | Consulta DynamoDB y redirige con **307** (404 si no existe) |
| GET | `/urls/{short_code}` | Devuelve el JSON del enlace (404 si no existe) |

---

## Paso a paso del despliegue (región `us-east-1`)

### 1. DynamoDB
Consola → DynamoDB → *Create table*
- Nombre: `url-shortener`
- Partition key: `short_code` (String)
- Capacidad: *On-demand*

(`original_url` y `created_at` se crean automáticamente al insertar.)

### 2. Rol IAM para EC2
1. IAM → *Policies* → *Create policy* → pestaña JSON → pega `deployment/iam-policy.json` (reemplaza `TU_ID_DE_CUENTA`). Nómbrala `UrlShortenerDynamoPolicy`.
2. IAM → *Roles* → *Create role* → *AWS service* → *EC2* → adjunta esa política → nombre `UrlShortenerEC2Role`.

### 3. EC2
- AMI: **Amazon Linux 2023**, tipo `t2.micro` / `t3.micro`.
- *Advanced details* → **IAM instance profile**: `UrlShortenerEC2Role`.
- Security Group:
  - SSH (22): *My IP*
  - TCP personalizado (8000): `0.0.0.0/0`
- Anota la **IP pública**.

### 4. Preparar el backend en EC2
```bash
ssh -i tu-llave.pem ec2-user@<IP_PUBLICA>

sudo dnf install -y python3.11 git
git clone https://github.com/Matym2026/PracticalExam.git
cd PracticalExam

python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
nano .env     # completa IP pública y origen del frontend (paso 5)
```

### 5. Frontend en S3
1. Edita `frontend/app.js` y cambia `API_URL` por `http://<IP_PUBLICA>:8000`.
2. S3 → *Create bucket* (nombre único) → desmarca *Block all public access*.
3. Sube `index.html`, `styles.css` y `app.js`.
4. Pestaña *Properties* → *Static website hosting* → Enable → Index document: `index.html`.
5. Pestaña *Permissions* → *Bucket policy* (cambia el nombre del bucket):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::NOMBRE-DE-TU-BUCKET/*"
  }]
}
```
6. Copia el endpoint del sitio (`http://NOMBRE.s3-website-us-east-1.amazonaws.com`) y ponlo en `ALLOWED_ORIGINS` del `.env` de EC2 (sin `/` al final).

> El endpoint de S3 website no usa HTTPS; por eso la API también usa HTTP (evita el bloqueo de contenido mixto).

### 6. Ejecutar con systemd
```bash
sudo cp deployment/shortener.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now shortener
sudo systemctl status shortener
```
Logs: `journalctl -u shortener -f`

---

## Pruebas

```bash
API=http://<IP_PUBLICA>:8000

# 1. Crear enlace
curl -X POST $API/shorten -H "Content-Type: application/json" \
     -d '{"original_url":"https://www.example.com/articulos/arquitectura-cloud"}'

# 2. Ver la redirección 307 (campo Location)
curl -i $API/<short_code>

# 3. UUID inexistente -> 404
curl -i $API/550e8400-e29b-41d4-a716-446655440000

# 4. Información del enlace
curl $API/urls/<short_code>

# 5. Persistencia tras reinicio
sudo systemctl restart shortener     # o: sudo reboot
curl -i $API/<short_code>            # sigue redirigiendo
```
También prueba desde el navegador: abre la página de S3, acorta una URL, copia el enlace y ábrelo.

## Pruebas locales (opcional)
```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
set -a; source .env; set +a
cd backend && uvicorn main:app --reload
```
(Localmente necesitas credenciales AWS configuradas con `aws configure`; **nunca** las guardes en el repositorio.)

## Seguridad
- Sin Access Keys en el código: boto3 usa las credenciales temporales del IAM Role.
- El rol solo permite `PutItem` y `GetItem` sobre la tabla `url-shortener`.
- `.env` está en `.gitignore`.
