"""Acquisition de mesures avec le SDK officiel YDLIDAR."""

from importlib import import_module


class Lidar:
    MODELES = {
        "x2": {"baud": 115200, "echantillonnage": 3, "frequence": 6.0,
               "canal_unique": True, "distance_min": 0.10, "distance_max": 8.0},
        "x4": {"baud": 128000, "echantillonnage": 5, "frequence": 7.0,
               "canal_unique": False, "distance_min": 0.12, "distance_max": 10.0},
    }

    def __init__(self, port: str, modele: str):
        if not isinstance(port, str) or not port.strip():
            raise ValueError("Le port serie doit etre une chaine non vide.")
        if not isinstance(modele, str) or modele.lower() not in self.MODELES:
            raise ValueError("Le modele doit etre x2 ou x4.")
        self.port = port
        self.modele = modele.lower()
        self._sdk = None
        self._lidar = None
        self._scan = None
        self._en_marche = False

    def demarrer(self) -> None:
        if self._en_marche:
            return
        try:
            self._sdk = import_module("ydlidar")
        except ImportError as erreur:
            raise RuntimeError(
                "SDK ydlidar introuvable. Veuillez installer YDLidar-SDK."
            ) from erreur

        configuration = self.MODELES[self.modele]
        try:
            self._sdk.os_init()
            self._lidar = self._sdk.CYdLidar()
            self._scan = self._sdk.LaserScan()
            options = {
                "LidarPropSerialPort": self.port,
                "LidarPropSerialBaudrate": configuration["baud"],
                "LidarPropLidarType": self._sdk.TYPE_TRIANGLE,
                "LidarPropDeviceType": self._sdk.YDLIDAR_TYPE_SERIAL,
                "LidarPropSampleRate": configuration["echantillonnage"],
                "LidarPropScanFrequency": configuration["frequence"],
                "LidarPropSingleChannel": configuration["canal_unique"],
                "LidarPropMinAngle": -180.0,
                "LidarPropMaxAngle": 180.0,
                "LidarPropMinRange": configuration["distance_min"],
                "LidarPropMaxRange": configuration["distance_max"],
                "LidarPropReversion": False,
                "LidarPropInverted": False,
                "LidarPropAutoReconnect": False,
            }
            for nom, valeur in options.items():
                if not self._lidar.setlidaropt(getattr(self._sdk, nom), valeur):
                    raise RuntimeError(f"Configuration refusee : {nom} = {valeur!r}.")
            if not self._lidar.initialize():
                raise RuntimeError(
                    f"Initialisation du {self.modele.upper()} sur {self.port} impossible : "
                    f"{self._lidar.DescribeError()}"
                )
            if not self._lidar.turnOn():
                raise RuntimeError(
                    f"Demarrage du scan impossible : {self._lidar.DescribeError()}"
                )
            self._en_marche = True
        except BaseException:
            try:
                self.arreter()
            except Exception:
                pass
            raise

    def obtenir_donnees(self) -> list:
        if not self._en_marche:
            raise RuntimeError("Le scan doit etre demarre avant de lire les donnees.")
        if not self._lidar.doProcessSimple(self._scan):
            raise RuntimeError(
                f"Lecture du lidar impossible : {self._lidar.DescribeError()}"
            )
        return [(float(point.range), float(point.angle)) for point in self._scan.points]

    def est_actif(self) -> bool:
        return self._en_marche and bool(self._sdk.os_isOk())

    def arreter(self) -> None:
        lidar = self._lidar
        self._lidar = None
        self._scan = None
        self._en_marche = False
        if lidar is not None:
            try:
                lidar.turnOff()
            finally:
                lidar.disconnecting()
