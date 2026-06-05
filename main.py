import feedparser
import json
import os
import smtplib
from email.mime.text import MIMEText

KEYWORDS = [
    "México"
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


def guardar_enviadas(datos):
    with open(ARCHIVO_ENVIADAS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def contiene_keyword(texto):
    texto = texto.lower()
    return any(k in texto for k in KEYWORDS)


def obtener_noticias():
    resultados = []

    for feed_url in RSS_FEEDS:
        print(f"Revisando RSS: {feed_url}")

        try:
            feed = feedparser.parse(feed_url)

            print(f"Noticias recibidas: {len(feed.entries)}")

            for i, entry in enumerate(feed.entries[:10], start=1):
                titulo = entry.get("title", "SIN TITULO")
                enlace = entry.get("link", "SIN LINK")

                print(f"{i}. {titulo}")
                print(f"   {enlace}")

            for entry in feed.entries:
                titulo = entry.get("title", "")
                resumen = entry.get("summary", "")
                enlace = entry.get("link", "")

                texto = f"{titulo} {resumen}"

                if contiene_keyword(texto):
                    resultados.append({
                        "titulo": titulo,
                        "link": enlace
                    })

        except Exception as e:
            print(f"Error revisando {feed_url}: {e}")

    print(f"Noticias que coinciden con palabras clave: {len(resultados)}")

    return resultados


def enviar_correo(noticias):
    email_user = os.environ["EMAIL_USER"]
    email_pass = os.environ["EMAIL_PASS"]
    email_to = os.environ["EMAIL_TO"]

    cuerpo = "Noticias encontradas:\n\n"

    for n in noticias:
        cuerpo += f"Título: {n['titulo']}\n"
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

        enviadas.extend(nuevas)

        guardar_enviadas(enviadas)

        print(f"Enviadas {len(nuevas)} noticias.")
    else:
        print("Sin noticias nuevas.")


if __name__ == "__main__":
    main()
