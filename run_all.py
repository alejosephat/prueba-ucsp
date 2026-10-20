"""Ejecuta el pipeline completo de principio a fin.

    python run_all.py

Cada etapa es idempotente: 01 no vuelve a descargar lo que ya esta en el
manifiesto con el mismo sha256, y 02 reconstruye silver y gold desde cero.
"""
import runpy
import sys
import time

ETAPAS = ["01_descargar", "02_transformar", "03_calidad", "04_tendencias",
          "05_diccionario"]


def main():
    etapas = sys.argv[1:] or ETAPAS
    for etapa in etapas:
        print(f"\n{'=' * 70}\n  {etapa}\n{'=' * 70}")
        t0 = time.time()
        runpy.run_module(etapa, run_name="__main__")
        print(f"-- {etapa} en {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
