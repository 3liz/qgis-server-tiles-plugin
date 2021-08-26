__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.server import QgsServerInterface


def serverClassFactory(server_iface: QgsServerInterface):
    """ Plugin entry point
    """
    from tilesForServer.tilesForServer import TilesForServer
    return TilesForServer(server_iface)
