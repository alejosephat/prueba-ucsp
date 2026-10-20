"""Descarga los datasets de TUNI.PE a data/bronze/.

Cadena de 5 pasos (la pagina tuni.pe/datos es un SPA que delega en SharePoint):
  1. catalogo        POST  /api/serviciotuni/listar
  2. link de descarga POST /api/serviciotuni  {"archivos":[id]}  -> webUrl SharePoint
  3. sesion anonima  GET   <webUrl>?download=1   -> cookie FedAuth + rootFolder
  4. nombre del zip  GET   /_api/web/GetFolderByServerRelativeUrl(...)/Files
  5. descarga        GET   /_api/web/GetFileByServerRelativeUrl(...)/$value

El paso 4 es obligatorio: sin el, el paso 5 devuelve 403.
Idempotente: si el zip local sigue coincidiendo con el sha256 del manifiesto, no
se vuelve a bajar NI a resolver -- y saltarse la resolucion es lo que hace que una
reejecucion cueste segundos y no minutos (ver el comentario en main()).
Con --revalidar se fuerza la resolucion completa contra la fuente.
"""
import csv
import hashlib
import re
import sys

import requests

from config import API, ARCHIVOS, BRONZE, SHAREPOINT

NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MANIFIESTO = BRONZE / "manifiesto.csv"


def catalogo(s):
    """Paso 1: {(categoria, periodo): id_csv} de todo lo publicado en TUNI."""
    r = s.post(f"{API}/serviciotuni/listar",
               json={"page": 0, "pageSize": 1000, "orderBy": "asc"},
               headers={"Origin": "https://tuni.pe"})
    r.raise_for_status()
    return {(d["categoria"], d["periodo"]): f["id"]
            for d in r.json()["data"] for f in d["formatos"] if f["formato"] == "csv"}


def resolver(s, id_archivo):
    """Pasos 2-4: del id del catalogo a la ruta del zip dentro de SharePoint."""
    web_url = s.post(f"{API}/serviciotuni", json={"archivos": [id_archivo]},
                     headers={"Origin": "https://tuni.pe"}).json()["webUrl"]

    # Ojo: a SharePoint NO se le manda el header Origin (lo rechaza con 403).
    html = s.get(f"{web_url}?download=1", headers=NAVEGADOR).text
    carpeta = re.search(r'"rootFolder":"([^"]+)"', html).group(1).replace("\u002f", "/")

    r = s.get(f"{SHAREPOINT}/_api/web/GetFolderByServerRelativeUrl('{carpeta}')/Files",
              headers={**NAVEGADOR, "Accept": "application/json;odata=nometadata"},
              params={"$select": "Name,Length,ServerRelativeUrl"})
    r.raise_for_status()
    archivo = r.json()["value"][0]
    return archivo["ServerRelativeUrl"], int(archivo["Length"])


def descargar(s, ruta, destino):
    """Paso 5: baja el zip en streaming y devuelve su sha256."""
    r = s.get(f"{SHAREPOINT}/_api/web/GetFileByServerRelativeUrl('{ruta}')/$value",
              headers=NAVEGADOR, stream=True)
    r.raise_for_status()
    sha = hashlib.sha256()
    with open(destino, "wb") as f:
        for trozo in r.iter_content(1 << 20):
            f.write(trozo)
            sha.update(trozo)
    return sha.hexdigest()


def sha256_de(ruta):
    sha = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            sha.update(trozo)
    return sha.hexdigest()


def main():
    # --revalidar ignora el atajo de idempotencia y vuelve a resolver cada
    # archivo contra la fuente. Util si se sospecha que SUNEDU republico un
    # periodo con el contenido corregido.
    revalidar = "--revalidar" in sys.argv
    BRONZE.mkdir(parents=True, exist_ok=True)
    # El manifiesto previo se indexa por (categoria, periodo) y no por nombre de
    # archivo, porque la clave con la que se busca es la del catalogo: el nombre
    # del zip lleva un hash que solo se conoce DESPUES de resolverlo.
    previo = {}
    if MANIFIESTO.exists():
        with open(MANIFIESTO, encoding="utf-8") as f:
            previo = {(r["categoria"], r["periodo"]): r for r in csv.DictReader(f)}

    s = requests.Session()
    cat = catalogo(s)
    filas = []

    for categoria, periodo in ARCHIVOS:
        # ATAJO DE IDEMPOTENCIA. Si el manifiesto ya trae este (categoria,
        # periodo) y el zip local sigue intacto, se salta TAMBIEN la resolucion.
        #
        # Por que importa: resolver un archivo cuesta tres llamadas HTTP (pasos
        # 2, 3 y 4), o sea 168 llamadas para el catalogo completo, y eso era el
        # 68 % del tiempo de esta etapa -- 154 s de 225 s medidos. Resolver no
        # aportaba nada cuando el hash ya coincide: el paso 5 compara el hash
        # LOCAL contra el del manifiesto, no contra el del servidor, asi que la
        # ruta resuelta se descartaba.
        #
        # LO QUE ESTO NO DETECTA, y hay que decirlo: si SUNEDU republica un
        # periodo con el contenido corregido, el zip local sigue intacto y el
        # atajo lo da por bueno. Tampoco lo detectaba la version anterior, por
        # el motivo de arriba. Para forzar la revalidacion completa contra la
        # fuente esta --revalidar.
        guardado = previo.get((categoria, periodo))
        if not revalidar and guardado:
            local = BRONZE / guardado["archivo"]
            if local.exists() and sha256_de(local) == guardado["sha256"]:
                print(f"  = {guardado['archivo']} (intacto, no se resuelve)")
                # bytes se re-tipa: csv.DictReader devuelve todo como texto, y
                # el total del final suma esta columna.
                filas.append({**guardado, "bytes": int(guardado["bytes"])})
                continue

        id_archivo = cat.get((categoria, periodo))
        if id_archivo is None:
            print(f"  !! no esta en el catalogo: {categoria} {periodo}", file=sys.stderr)
            continue

        ruta, tam = resolver(s, id_archivo)
        nombre = ruta.rsplit("/", 1)[-1]
        destino = BRONZE / nombre

        if destino.exists() and guardado and guardado["sha256"] == sha256_de(destino):
            print(f"  = {nombre} (ya descargado)")
            sha = guardado["sha256"]
        else:
            print(f"  v {nombre} ({tam / 1048576:.0f} MB)...", end="", flush=True)
            sha = descargar(s, ruta, destino)
            print(" ok")

        filas.append({"categoria": categoria, "periodo": periodo, "id": id_archivo,
                      "archivo": nombre, "bytes": destino.stat().st_size, "sha256": sha})

    # Sin esta guarda, un cambio en la API dejaria filas vacio, el open("w")
    # truncaria el manifiesto antes de fallar, y la siguiente corrida perderia
    # la idempotencia: volveria a descargar los 1 270 MB.
    if not filas:
        raise SystemExit("No se resolvio ningun archivo: se conserva el manifiesto previo.")

    with open(MANIFIESTO, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    total = sum(r["bytes"] for r in filas) / 1048576
    print(f"\n{len(filas)} archivos | {total:.0f} MB | manifiesto en {MANIFIESTO}")


if __name__ == "__main__":
    main()
