#!/usr/bin/env python3

import math

from ev_app import EvApp, EvDesc
from moteur import Moteur
from param import (
    APP_CTRL_ROBOT,
    MOTEUR_DROIT_IN1,
    MOTEUR_DROIT_IN2,
    MOTEUR_DROIT_PWM,
    MOTEUR_GAUCHE_IN1,
    MOTEUR_GAUCHE_IN2,
    MOTEUR_GAUCHE_PWM,
    MSG_ARRETER,
    MSG_AVANCER,
    MSG_OBSTACLE,
    MSG_PIVOTER_D,
    MSG_PIVOTER_G,
    MSG_RECULER,
    MSG_VITESSE,
    VITESSE_MAX,
    VITESSE_MIN,
)
from robot import Robot
from tel_cmd import NOM_FENETRE, TelCmd, afficher_commandes


class CtrlRobot(EvApp):
    def __init__(self, port_no, robot, **app_options):
        super().__init__(port_no, **app_options)
        self.robot = robot
        self.action = MSG_ARRETER
        self.obstacle = False
        self._telecommande = None
        self._cv2 = None
        self._np = None
        self._actions = {
            MSG_ARRETER: self.robot.arreter,
            MSG_AVANCER: self.avancer,
            MSG_RECULER: self.robot.reculer,
            MSG_PIVOTER_G: self.robot.pivoter_gauche,
            MSG_PIVOTER_D: self.robot.pivoter_droite,
        }

    @staticmethod
    def lire_vitesse(evenement):
        vitesse = float(evenement.split()[0])
        if not math.isfinite(vitesse):
            raise ValueError("La vitesse doit etre un nombre fini")
        return max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

    @staticmethod
    def lire_obstacle(evenement):
        valeur = evenement.split()[0].strip().lower()
        if valeur not in ("true", "false"):
            raise ValueError("MSG_OBSTACLE doit contenir True ou False")
        return valeur == "true"

    def avancer(self):
        if self.obstacle:
            self.robot.arreter()
            self.action = MSG_ARRETER
            print("Avance refusee: obstacle detecte.")
            return False
        self.robot.avancer()
        return True

    def _traiter_commande(self, evenement):
        try:
            if evenement.type == MSG_OBSTACLE:
                self.obstacle = self.lire_obstacle(evenement)
                if self.obstacle and self.action == MSG_AVANCER:
                    self.robot.arreter()
                    self.action = MSG_ARRETER
                return
            if evenement.type == MSG_VITESSE:
                self.robot.vitesse = self.lire_vitesse(evenement)
                if self.action != MSG_ARRETER:
                    self._actions[self.action]()
                return
            action = self._actions.get(evenement.type)
            if action is None:
                print(f"Message inconnu ignore: {evenement.type}")
                return
            self.action = evenement.type
            action()
        except (ValueError, IndexError) as erreur:
            self.robot.arreter()
            self.action = MSG_ARRETER
            print(f"Commande invalide, robot arrete: {erreur}")

    def activer_clavier(self, cv2, np):
        self._cv2 = cv2
        self._np = np
        self._telecommande = TelCmd("127.0.0.1", envoyer=self._commande_clavier)
        self.tmo = min(self.tmo, 0.03)

    def _commande_clavier(self, ip_robot, port_no, type_message, *donnees):
        evenement = EvDesc(type_message, ";".join(str(valeur) for valeur in donnees))
        self._traiter_commande(evenement)

    def _actualiser_clavier(self):
        self._telecommande.derniere_commande = self.action
        self._telecommande.vitesse = self.robot.vitesse
        afficher_commandes(self._telecommande, self._cv2, self._np)

        touche = self._cv2.waitKeyEx(1)
        if self._cv2.getWindowProperty(NOM_FENETRE, self._cv2.WND_PROP_VISIBLE) < 1:
            self.quitter_app()
            return
        if touche == 27:
            touche = ord("x")
        if touche != -1 and not self._telecommande.traiter_touche(touche):
            self.quitter_app()

    def dispatch_event(self, evenement):
        if evenement is not None:
            self._traiter_commande(evenement)
        if self._telecommande is not None:
            self._actualiser_clavier()

    def quitter(self):
        try:
            self.robot.fermer()
        finally:
            if self._cv2 is not None:
                self._cv2.destroyAllWindows()
        print("Controleur arrete; moteurs desactives.")


def creer_controleur(port_no=APP_CTRL_ROBOT):
    try:
        from gpiozero import DigitalOutputDevice, PWMOutputDevice
    except ImportError as erreur:
        raise SystemExit("Installez gpiozero") from erreur

    moteur_gauche = Moteur(
        PWMOutputDevice(MOTEUR_GAUCHE_PWM),
        DigitalOutputDevice(MOTEUR_GAUCHE_IN2),
        DigitalOutputDevice(MOTEUR_GAUCHE_IN1),
    )
    moteur_droit = Moteur(
        PWMOutputDevice(MOTEUR_DROIT_PWM),
        DigitalOutputDevice(MOTEUR_DROIT_IN1),
        DigitalOutputDevice(MOTEUR_DROIT_IN2),
    )
    robot = Robot(moteur_gauche, moteur_droit)
    return CtrlRobot(port_no, robot)


def main():
    try:
        import cv2
        import numpy as np
    except ImportError as erreur:
        raise SystemExit("OpenCV et NumPy sont necessaires pour la commande clavier.") from erreur

    controleur = creer_controleur()
    controleur.activer_clavier(cv2, np)
    print(f"Controleur du robot en ecoute sur le port {APP_CTRL_ROBOT}.")
    print("Cliquez dans la fenetre: W avancer, S reculer, Q/E pivoter.")
    print("Espace: arreter. Virgule/point: vitesse. X ou Echap: quitter.")
    controleur.run()


if __name__ == "__main__":
    main()
