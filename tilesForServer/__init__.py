""" QGIS server plugin - Tile Map Service and OGC Tiles API for QGIS Server

    author: René-Luc DHONT (3liz)
    Copyright: (C) 2021 3Liz
"""

from qgis.server import QgsServerInterface


def serverClassFactory(serverIface: 'QgsServerInterface'):
    """ Plugin entry point
    """
    # save reference to the QGIS interface
    from .tilesForServer import tilesForServer
    return tilesForServer(serverIface)
