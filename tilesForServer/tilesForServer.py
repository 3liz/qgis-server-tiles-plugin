""" QGIS server plugin - Tile Map Service and OGC Tiles API for QGIS Server

    author: René-Luc DHONT (3liz)
    Copyright: (C) 2021 3Liz
"""

from qgis.server import QgsServerInterface

from .tmsapi import init_tms_api


class tilesForServer:
    """ Plugin for QGIS server
    """

    def __init__(self, serverIface: 'QgsServerInterface') -> None:
        # save reference to the QGIS interface
        self.serverIface = serverIface

        # Cache Manager API
        init_tms_api(serverIface)
