// Cambia esta URL por la IP publica (o DNS) de tu instancia EC2
const API_URL = "http://TU-IP-PUBLICA-EC2:8000";

const form = document.getElementById("form");
const inputUrl = document.getElementById("url");
const btnAcortar = document.getElementById("btn-acortar");
const errorBox = document.getElementById("error");
const resultado = document.getElementById("resultado");
const shortUrl = document.getElementById("short-url");
const btnCopiar = document.getElementById("btn-copiar");

function mostrarError(mensaje) {
  errorBox.textContent = mensaje;
  errorBox.hidden = false;
  resultado.hidden = true;
}

function urlValida(texto) {
  try {
    const u = new URL(texto);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.hidden = true;
  btnCopiar.textContent = "Copiar";

  const original = inputUrl.value.trim();
  if (!urlValida(original)) {
    mostrarError("La URL no es válida. Debe comenzar con http:// o https://");
    return;
  }

  btnAcortar.disabled = true;
  try {
    const resp = await fetch(`${API_URL}/shorten`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ original_url: original }),
    });
    if (!resp.ok) {
      mostrarError(resp.status === 422
        ? "El servidor rechazó la URL. Revisa que sea válida."
        : "El servidor respondió con un error. Intenta de nuevo.");
      return;
    }
    const datos = await resp.json();
    shortUrl.textContent = datos.short_url;
    shortUrl.href = datos.short_url;
    resultado.hidden = false;
  } catch {
    mostrarError("No se pudo conectar con el backend. Verifica que la API en EC2 esté en ejecución.");
  } finally {
    btnAcortar.disabled = false;
  }
});

btnCopiar.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(shortUrl.textContent);
  } catch {
    // Respaldo: el sitio S3 por HTTP no siempre permite clipboard API
    const t = document.createElement("textarea");
    t.value = shortUrl.textContent;
    document.body.appendChild(t);
    t.select();
    document.execCommand("copy");
    t.remove();
  }
  btnCopiar.textContent = "¡Copiado!";
});
