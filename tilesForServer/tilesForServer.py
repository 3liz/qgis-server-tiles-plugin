__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.server import QgsServerInterface

from tilesForServer.tmsapi import init_tms_api


class TilesForServer:

    def __init__(self, server_iface: QgsServerInterface) -> None:
        init_tms_api(server_iface)
