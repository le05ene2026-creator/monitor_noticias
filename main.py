import feedparser
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

KEYWORDS = [
    "mundial",
    "copa del mundo",
    "fifa",
    "selección mexicana",
    "seleccion mexicana",
    "tri",
    "estadio azteca",
    "Mundial 2026",
    "fútbol",
    "futbol",
    "japón",
    "arbitro",
    "corner",
    "penalti",
    "fuera de juego",
    "alineación",
    "alineacion",
    "tarjeta amarilla",
    "tarjeta roja",
    "driblear"
]

RSS_FEEDS = [
    {
        "medio": "La Jornada",
        "url": "https://www.jornada.com.mx/rss/deportes.xml"
    },
    {
        "medio": "Reforma / Cancha",
        "url": "https://www.reforma.com/rss/cancha.xml"
    }
]

PAGINAS = [
    {
        "medio": "El Universal",
        "url": "https://www.eluniversal.com.mx/deportes/"
    },
    {
        "medio": "Excélsior",
        "url": "https://www.excelsior.com.mx/adrenalina"
    },
    {
        "medio": "La Crónica de Hoy",
        "url": "https://www.cronica.com.mx/deportes/"
    }
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
    limite = ahora - timedelta(hours=24)

    return dt >= limite


def obtener_fecha_nota(url):
    headers = {
        "User-Agent": "Mozilla/5.0 monitor-mundial-2026",
        "Accept-Language": "es-MX,es;q=0.9"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)

        if r.status_code != 200:
            print(f"No se pudo abrir nota: {url} - Status {r.status_code}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        posibles_metas = [
            {"property": "article:published_time"},
            {"property": "og:published_time"},
            {"name": "article:published_time"},
            {"name": "pubdate"},
            {"name": "date"},
            {"itemprop": "datePublished"},
        ]

        for attrs in posibles_metas:
            meta = soup.find("meta", attrs=attrs)
            if meta and meta.get("content"):
                fecha_raw = meta["content"]
                print(f"Fecha encontrada en {url}: {fecha_raw}")
        
                try:
                    dt = parsedate_to_datetime(fecha_raw)
                    print(f"Fecha interpretada: {dt}")
                    return dt
                except:
                    try:
                        dt = datetime.fromisoformat(fecha_raw.replace("Z", "+00:00"))
                        print(f"Fecha interpretada ISO: {dt}")
                        return dt
                    except Exception as e:
                        print(f"No pude interpretar fecha: {fecha_raw} - {e}")
                        return None

        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            return parsedate_to_datetime(time_tag["datetime"])

        return None

    except Exception as e:
        print(f"Error obteniendo fecha de nota {url}: {e}")
        return None


def fecha_en_ultimas_24_horas(dt):
    if dt is None:
        return False

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(hours=24)

    return dt >= limite

def obtener_noticias():
    resultados = []

    # 1. Revisar RSS
    for feed in RSS_FEEDS:
        medio = feed["medio"]
        feed_url = feed["url"]

        print(f"Revisando RSS: {medio} - {feed_url}")

        parsed = feedparser.parse(feed_url)
        print(f"Noticias recibidas: {len(parsed.entries)}")

        for entry in parsed.entries:
            titulo = entry.get("title", "")
            resumen = entry.get("summary", "")
            enlace = entry.get("link", "")
            fecha = entry.get("published", "") or entry.get("updated", "")

            texto = f"{titulo} {resumen}"

            if es_ultimas_24_horas(entry) and contiene_keyword(texto):
                resultados.append({
                    "medio": medio,
                    "titulo": titulo,
                    "link": enlace,
                    "fecha": fecha
                })

    # 2. Revisar páginas web
    headers = {
        "User-Agent": "Mozilla/5.0 monitor-mundial-2026",
        "Accept-Language": "es-MX,es;q=0.9"
    }

    for pagina in PAGINAS:
        medio = pagina["medio"]
        url = pagina["url"]

        print(f"Revisando página: {medio} - {url}")

        try:
            r = requests.get(url, headers=headers, timeout=25)
            print(f"Status: {r.status_code}")
            print(f"Tamaño HTML: {len(r.text)}")

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            enlaces = soup.find_all("a", href=True)

            vistos = set()

            for a in enlaces:
                titulo = a.get_text(" ", strip=True)
                href = a.get("href", "")

                if not titulo or len(titulo) < 20:
                    continue

                enlace = urljoin(url, href)

                if enlace in vistos:
                    continue

                vistos.add(enlace)

                texto = titulo.lower()

                if contiene_keyword(texto):
                    fecha_dt = obtener_fecha_nota(enlace)

                    if fecha_en_ultimas_24_horas(fecha_dt):
                        resultados.append({
                            "medio": medio,
                            "titulo": titulo,
                            "link": enlace,
                            "fecha": fecha_dt.isoformat()
                        })
                    else:
                        print(f"Descartada por fecha: {titulo}")

        except Exception as e:
            print(f"Error leyendo {medio}: {e}")

    print(f"Noticias encontradas: {len(resultados)}")

    return resultados


def enviar_correo(noticias):
    email_user = os.environ["EMAIL_USER"]
    email_pass = os.environ["EMAIL_PASS"]
    email_to = os.environ["EMAIL_TO"]

    cuerpo = "Noticias encontradas en las últimas 24 horas:\n\n"

    for n in noticias:
        cuerpo += f"Medio: {n.get('medio', 'Sin medio')}\n"
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
