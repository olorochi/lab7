"""Acquisition du lidar et affichage d'une carte."""

import argparse
import math
from pathlib import Path
import sys
import time
import os

import cv2

from camera import Camera
from capteur_lidar import Lidar
from projecteur import Projecteur


PERIODE_SECONDES = 0.050


def executer(camera, nombre_scans=None):
    derniere_image = None
    compteur = 0
    camera.demarrer()
    while compteur != nombre_scans:
        debut = time.monotonic()
        camera.save(f"image_rgb/{compteur}.png")
        compteur += 1

        attente = PERIODE_SECONDES - (time.monotonic() - debut)
        if attente > 0:
            time.sleep(attente)


def entier_positif(texte):
    valeur = int(texte)
    if valeur <= 0:
        raise argparse.ArgumentTypeError("La valeur doit etre positive.")
    return valeur


def echelle_positive(texte):
    valeur = float(texte)
    if not math.isfinite(valeur) or valeur <= 0:
        raise argparse.ArgumentTypeError("L'echelle doit etre finie et positive.")
    return valeur


def main(arguments=None):
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--scans", type=entier_positif, default=200, help="Arreter apres ce nombre d'acquisitions.")
    options = analyseur.parse_args(arguments)

    try:
        camera = Camera(640, 480)

        try: 
            os.mkdir("image_rgb")
        except FileExistsError:
            pass

        image = executer(camera, options.scans)

    except KeyboardInterrupt:
        print("\nAcquisition interrompue.")
    except (RuntimeError, OSError, ValueError, cv2.error) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
