"""Acquisition du lidar et affichage d'une carte toutes les 50 ms."""

import argparse
import math
from pathlib import Path
import sys
import time

import cv2

from capteur_lidar import Lidar
from projecteur import Projecteur


PERIODE_SECONDES = 0.050


def executer(capteur, projecteur, nombre_scans=None):
    derniere_image = None
    compteur = 0
    try:
        capteur.demarrer()
        while capteur.est_actif():
            debut = time.monotonic()
            derniere_image = projecteur.projeter(capteur.obtenir_donnees())
            compteur += 1
            if projecteur.quitter_demande():
                break
            if nombre_scans is not None and compteur >= nombre_scans:
                break
            attente = PERIODE_SECONDES - (time.monotonic() - debut)
            if attente > 0:
                time.sleep(attente)
    finally:
        try:
            capteur.arreter()
        finally:
            projecteur.fermer()
    return derniere_image


def entier_positif(texte):
    valeur = int(texte)
    if valeur <= 0:
        raise argparse.ArgumentTypeError("La valeur doit etre strictement positive.")
    return valeur


def echelle_positive(texte):
    valeur = float(texte)
    if not math.isfinite(valeur) or valeur <= 0:
        raise argparse.ArgumentTypeError("L'echelle doit etre finie et positive.")
    return valeur


def main(arguments=None):
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--port", default="/dev/ttyUSB0", help="Port serie du lidar.")
    analyseur.add_argument("--modele", type=str.lower, choices=("x2", "x4"), default="x4")
    analyseur.add_argument("--taille", type=entier_positif, default=800,
                           help="Largeur et hauteur de l'image en pixels (800).")
    analyseur.add_argument("--echelle", type=echelle_positive, default=100.0,
                           help="Nombre de pixels par metre (100).")
    analyseur.add_argument("--sans-fenetre", action="store_true",
                           help="Calculer la carte sans ouvrir de fenetre OpenCV.")
    analyseur.add_argument("--scans", type=entier_positif,
                           help="Arreter apres ce nombre d'acquisitions.")
    analyseur.add_argument("--capture", type=Path, help="Enregistrer la derniere carte (.png).")
    options = analyseur.parse_args(arguments)
    if options.sans_fenetre and options.scans is None:
        analyseur.error("--sans-fenetre exige --scans pour borner.")

    try:
        capteur = Lidar(options.port, options.modele)
        projecteur = Projecteur(options.taille, options.taille, options.echelle,
                                afficher=not options.sans_fenetre)
        print(f"Lidar {options.modele.upper()} sur {options.port}.")
        if not options.sans_fenetre:
            print("Quitter : Q, ESC.")
        image = executer(capteur, projecteur, options.scans)
        if options.capture is not None:
            if image is None:
                raise RuntimeError("Aucune carte recue a enregistrer.")
            options.capture.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(options.capture), image):
                raise OSError(f"Impossible d'enregistrer {options.capture}.")
            print(f"Carte enregistree : {options.capture}")
    except KeyboardInterrupt:
        print("\nAcquisition interrompue.")
    except (RuntimeError, OSError, ValueError, cv2.error) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
