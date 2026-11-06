"""Projection des mesures dans une carte OpenCV en couleurs BGR."""

import math
from typing import Iterable, Tuple

import cv2
import numpy as np


VERT = (0, 255, 0)
ROUGE = (0, 0, 255)
BLANC = (255, 255, 255)


class Projecteur:

    def __init__(self, largeur: int = 800, hauteur: int = 800,
                 echelle: float = 100.0, afficher: bool = True):
        if (not isinstance(largeur, int) or not isinstance(hauteur, int)
                or largeur <= 0 or hauteur <= 0):
            raise ValueError("Les dimensions doivent etre des entiers strictement positifs.")
        if not math.isfinite(echelle) or echelle <= 0:
            raise ValueError("L'echelle doit etre finie et strictement positive.")
        self.largeur = largeur
        self.hauteur = hauteur
        self.echelle = echelle
        self.afficher = afficher
        self.centre = (largeur // 2, hauteur // 2)
        self.nom_fenetre = "Labo 6 - Carte lidar"
        self._fenetre_ouverte = False

    def coordonnees_image(self, distance: float, angle: float) -> Tuple[int, int]:
        x = -distance * math.sin(angle)
        y = distance * math.cos(angle)
        return (round(self.centre[0] + x * self.echelle),
                round(self.centre[1] + y * self.echelle))

    @staticmethod
    def est_dangereux(distance: float, angle: float) -> bool:
        """Zone rouge : 0,10 < d < 0,50 m et ecart a l'avant <= 10 degres."""
        if not (math.isfinite(distance) and math.isfinite(angle)
                and 0.10 < distance < 0.50):
            return False
        ecart_avant = abs(math.remainder(angle - math.pi, math.tau))
        return ecart_avant <= math.radians(10) + 1e-12

    def projeter(self, vecteurs: Iterable[Tuple[float, float]]) -> np.ndarray:
        image = np.zeros((self.hauteur, self.largeur, 3), dtype=np.uint8)
        self._dessiner_reperes(image)
        points_rouges = []
        for distance, angle in vecteurs:
            if not (math.isfinite(distance) and math.isfinite(angle)) or distance <= 0:
                continue
            x, y = self.coordonnees_image(distance, angle)
            if not (0 <= x < self.largeur and 0 <= y < self.hauteur):
                continue
            if self.est_dangereux(distance, angle):
                points_rouges.append((x, y))
            else:
                cv2.circle(image, (x, y), 2, VERT, -1)

        for point in points_rouges:
            cv2.circle(image, point, 2, ROUGE, -1)
        cv2.circle(image, self.centre, 3, BLANC, -1)

        if self.afficher:
            cv2.imshow(self.nom_fenetre, image)
            self._fenetre_ouverte = True
        return image

    def _dessiner_reperes(self, image: np.ndarray) -> None:
        cx, cy = self.centre
        gris = (28, 28, 28)
        cv2.line(image, (cx, 0), (cx, self.hauteur - 1), gris, 1)
        cv2.line(image, (0, cy), (self.largeur - 1, cy), gris, 1)
        rayon_max = min(cx, cy)
        for metres in range(1, math.ceil(rayon_max / self.echelle)):
            rayon = round(metres * self.echelle)
            if rayon > 0:
                cv2.circle(image, self.centre, rayon, gris, 1)
        texte = "AVANT"
        largeur_texte = cv2.getTextSize(texte, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0][0]
        cv2.putText(image, texte, (max(0, cx - largeur_texte // 2), 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)
        cv2.putText(image, f"1 m = {self.echelle:g} px", (10, self.hauteur - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)

    def quitter_demande(self) -> bool:
        if not self._fenetre_ouverte:
            return False
        touche = cv2.waitKey(1) & 0xFF
        if touche in (ord("q"), ord("Q"), 27):
            return True
        try:
            return cv2.getWindowProperty(self.nom_fenetre, cv2.WND_PROP_VISIBLE) < 1
        except cv2.error:
            return True

    def fermer(self) -> None:
        if self._fenetre_ouverte:
            try:
                cv2.destroyWindow(self.nom_fenetre)
            except cv2.error:
                pass
            self._fenetre_ouverte = False
