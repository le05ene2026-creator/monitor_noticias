import feedparser
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

KEYWORDS = [
    "mundial",
    "copa del mundo",
    "fifa",
    "selección mexicana",
    "seleccion mexicana",
    "tri",
    "estadio azteca",
    "mundial 2026",
    "fútbol",
    "futbol"
]

RSS_FEEDS = [
    "https://www.eluniversal.com.mx/rss.xml"
]

ARCHIVO_ENVIADAS = "noticias_enviadas.json"


def cargar_enviadas():
    try:
        with open(ARCHIVO_ENVIADAS, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def contiene_keyword(texto):
    texto = texto.lower()
    return any(k in texto for k in KEYWORDS)


def fecha_entry(entry):
    fecha = entry.get("published", "") or entry.get("updated", "")
    if not fecha:
        return None

    try:
        dt = parsedate_to_datetime(fecha)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return None


def es_ultimas_24_horas(entry):
    dt = fecha_entry(entry)
    if dt is None:
        return False

    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(hours=48)

    return dt >= limite


def obtener_noticias():
    resultados = []

    for feed_url in RSS_FEEDS:
        print(f"Revisando RSS: {feed_url}")

        feed = feedparser.parse(feed_url)
        print(f"Noticias recibidas: {len(feed.entries)}")

        for entry in feed.entries:
            titulo = entry.get("title", "")
            resumen = entry.get("summary", "")
            enlace = entry.get("link", "")
            fecha = entry.get("published", "") or entry.get("updated", "")

            texto = f"{titulo} {resumen}"

            if es_ultimas_24_horas(entry) and contiene_keyword(texto):
                resultados.append({
                    "titulo": titulo,
                    "link": enlace,
                    "fecha": fecha
                })

    print(f"Noticias encontradas en últimas 24 horas: {len(resultados)}")

    return resultados


def enviar_correo(noticias):
    email_user = os.environ["EMAIL_USER"]
    email_pass = os.environ["EMAIL_PASS"]
    email_to = os.environ["EMAIL_TO"]

    cuerpo = "Noticias encontradas en las últimas 24 horas:\n\n"

    for n in noticias:
        cuerpo += f"Título: {n['titulo']}\n"
        cuerpo += f"Fecha: {n['fecha']}\n"
        cuerpo += f"Enlace: {n['link']}\n\n"

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = "Alerta diaria Mundial 2026"
    mensaje["From"] = email_user
    mensaje["To"] = email_to

    servidor = smtplib.SMTP("smtp.gmail.com", 587)
    servidor.starttls()
    servidor.login(email_user, email_pass)
    servidor.send_message(mensaje)
    servidor.quit()


def main():
    enviadas = cargar_enviadas()
    urls_enviadas = {n["link"] for n in enviadas}

    noticias = obtener_noticias()

    nuevas = [
        n for n in noticias
        if n["link"] not in urls_enviadas
    ]

    if nuevas:
        enviar_correo(nuevas)
        print(f"Enviadas {len(nuevas)} noticias.")
    else:
        print("Sin noticias nuevas en las últimas 24 horas.")


if __name__ == "__main__":
    main()
