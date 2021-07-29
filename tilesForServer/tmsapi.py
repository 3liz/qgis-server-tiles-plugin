from pathlib import Path

from qgis.server import (
    QgsServerProjectUtils,
    QgsServerOgcApi,
    QgsBufferServerRequest,
    QgsServerRequest,
)
from qgis.core import Qgis, QgsMessageLog, QgsCoordinateTransform

from .apiutils import HTTPError, RequestHandler, register_api_handlers


#
# WMTS API Handlers
#

class ProjectParser:

    def tile_project_info(self):
        project = self._context.project()

        # The project as tiles source
        if not project.readBoolEntry("WMTSLayers", "Project")[0]:
            return

        # project identifier
        root_name = QgsServerProjectUtils.wmsRootName(project)
        if not root_name:
            root_name = project.title()
        if not root_name:
            return

        # available formats
        formats = []
        if project.readBoolEntry("WMTSPngLayers", "Project")[0]:
            formats.append('png')
        if project.readBoolEntry("WMTSJpegLayers", "Project")[0]:
            formats.append('jpg')

        if not formats:
            return

        # tileMap info
        yield {
                'source_id': root_name,
                'source_type': 'project',
                'id': root_name,
                'title': project.title(),
                'abstract': project.title(),
                'formats': formats
              }

    def tile_groups_info(self):
        project = self._context.project()

        # Groups as tiles source
        g_names = project.readListEntry("WMTSLayers", "Group")[0]
        if not g_names:
            return

        tree_root = project.layerTreeRoot()

        png_g_names = project.readListEntry("WMTSPngLayers", "Group")[0]
        jpg_g_names = project.readListEntry("WMTSJpegLayers", "Group")[0]

        for g_name in g_names:
            tree_group = tree_root.findGroup(g_name)
            if not tree_group:
                continue

            # Group identifier and other infos
            g_id = tree_group.customProperty("wmsShortName")
            if not g_id:
                g_id = g_name
            g_title = tree_group.customProperty("wmsTitle")
            if not g_title:
                g_title = g_name
            g_abstract = tree_group.customProperty("wmsAbstract")

            # available formats
            g_formats = []
            if g_name in png_g_names:
                g_formats.append('png')
            if g_name in jpg_g_names:
                g_formats.append('jpg')
            if not g_formats:
                continue

            # tileMap info
            yield {
                    'source_id': g_name,
                    'source_type': 'group',
                    'id': g_id,
                    'title': g_title,
                    'abstract': g_abstract,
                    'formats': g_formats,
                  }

    def tile_layers_info(self):
        project = self._context.project()

        # Layers as tiles source
        layer_ids = project.readListEntry("WMTSLayers", "Layer")[0]
        if not layer_ids:
            return

        png_layer_ids = project.readListEntry("WMTSPngLayers", "Layer")[0]
        jpg_layer_ids = project.readListEntry("WMTSJpegLayers", "Layer")[0]

        for layer_id in layer_ids:
            layer = project.mapLayer(layer_id)
            if not layer:
                continue

            # Layer identifier and informations
            l_id = layer.shortName()
            if not l_id:
                l_id = layer.name()
            l_title = layer.title()
            if not l_title:
                l_title = layer.name()

            # available formats
            l_formats = []
            if layer_id in png_layer_ids:
                l_formats.append('png')
            if layer_id in jpg_layer_ids:
                l_formats.append('jpg')
            if not l_formats:
                continue

            # tileMap info
            yield {
                    'source_id': layer.id(),
                    'source_type': 'layer',
                    'id': l_id,
                    'title': l_title,
                    'abstract': layer.abstract(),
                    'formats': l_formats,
                  }

    def tile_maps_info(self):
        # The project as tiles source
        for info in self.tile_project_info():
            yield info

        # Groups as tiles source
        for info in self.tile_groups_info():
            yield info

        # Layers as tiles source
        for info in self.tile_layers_info():
            yield info

    def get_complete_tilemap_info(self, tilemapid):
        for info in self.tile_maps_info():
            if tilemapid != info['id']:
                continue

            extra = {**info}
            source_type = extra.pop('source_type')
            source_id = extra.pop('source_id')

            extra['bbox'] = self.get_tilemap_bbox(source_type, source_id)
            extra['formats'] = [{
                'extension': ext,
                'mimetype': self.mimetypeFromExtension(ext)
            } for ext in extra['formats']]
            return extra
        return None

    def get_tilemap_bbox(self, source_type, source_id):
        bbox = None
        if source_type == 'project':
            bbox = self.get_project_bbox()
        elif source_type == 'group':
            bbox = self.get_group_bbox(source_id)
        elif source_type == 'Layer':
            bbox = self.get_layer_bbox(source_id)
        return bbox

    def get_project_bbox(self):
        project = self._context.project()
        crs_dest = QgsCoordinateReferenceSystem("EPSG:3857")
        xform_context = project.transformContext()

        proj_rect = QgsServerProjectUtils.wmsExtent(project)
        xform = QgsCoordinateTransform(project.crs(), crs_dest, xform_context)
        proj_rect = xform.transform(proj_rect)

        return [
            proj_rect.xMinimum(), proj_rect.yMinimum(),
            proj_rect.xMaximum(), proj_rect.yMaximum()
        ]

    def get_group_bbox(self, group_name):
        project = self._context.project()
        crs_dest = QgsCoordinateReferenceSystem("EPSG:3857")
        xform_context = project.transformContext()

        group_rect = None
        tree_group = tree_root.findGroup(group_name)
        for tree_layer in tree_group.findLayers():
            layer = tree_layer.layer
            if not layer:
                continue

            xform = QgsCoordinateTransform(layer.crs(), crs_dest, xform_context)
            if not group_rect:
                group_rect = xform.transform(layer.extent())
            else:
                group_rect.combineExtentWith(xform.transform(layer.extent()))

        if not group_rect:
            return group_rect

        return [
            group_rect.xMinimum(), group_rect.yMinimum(),
            group_rect.xMaximum(), group_rect.yMaximum()
        ]

    def get_layer_bbox(self, layer_id):
        project = self._context.project()
        crs_dest = QgsCoordinateReferenceSystem("EPSG:3857")
        xform_context = project.transformContext()

        layer = project.mapLayer(layer_id)
        if not layer:
            return None

        xform = QgsCoordinateTransform(layer.crs(), crs_dest, xform_context)
        layer_rect = xform.transform(layer.extent())

        if not layer_rect:
            return layer_rect

        return [
            layer_rect.xMinimum(), layer_rect.yMinimum(),
            layer_rect.xMaximum(), layer_rect.yMaximum()
        ]

    def mimetypeFromExtension(self, extension):
        if extension == 'png':
            return 'image/png'
        elif extension == 'jpg':
            return 'image/jpeg'
        return ''


class LandingPage(RequestHandler, ProjectParser):
    """ Project tile map listing handler
    """
    def get(self) -> None:
        project = self._context.project()

        grids = project.readListEntry("WMTSGrids", "CRS")[0]

        # tileMaps generator
        def links():
            # the tms API is available only for EPSG:3857 grid
            if 'EPSG:3857' not in grids:
                return
            # tile maps
            for info in self.tile_maps_info():
                tile_map_id = info['id']
                extra = {**info}
                del extra['source_id']
                del extra['source_type']
                extra['links'] = [{
                        'href': self.href(f"/tilemaps/{tile_map_id})", QgsServerOgcApi.contentTypeToExtension(QgsServerOgcApi.JSON)),
                        "rel": QgsServerOgcApi.relToString(QgsServerOgcApi.item),
                        "type": QgsServerOgcApi.mimeType(QgsServerOgcApi.JSON),
                        "title": "Cache collection",
                    }]
                yield extra

        data = {
            'title': QgsServerProjectUtils.owsServiceTitle(project),
            'abstract': QgsServerProjectUtils.owsServiceAbstract(project),
            'tileMaps': list(links()),
            'links': [],  # self.links(context)
        }
        self.write(data)

class TileMapInfo(RequestHandler, ProjectParser):
    """ Tile map information handler
    """
    def get(self, tilemapid):
        QgsMessageLog.logMessage('Tile map id: %s' % tilemapid, "tilesApi", Qgis.Warning)
        info = self.get_complete_tilemap_info(tilemapid)
        if not info :
            raise HTTPError(404, 'Tile map not found')
        self.write(info)


class TileMapContent(RequestHandler, ProjectParser):
    """ Tile map content handler
    """
    def initialize(self, srv_iface, **kwargs ) -> None:
        """ override
        """
        self._srv_iface = srv_iface
        self._project_needed = True

    def prepare(self, **values):
        """
        """
        QgsMessageLog.logMessage(f"Values %s" % ', '.join(['%s = %s' % (k, v) for k, v in values.items()]) ,"tilesApi",Qgis.Warning)

        if self._project_needed and not self._project:
            raise HTTPError(500, 'Project file error. For Tiles API, please provide a MAP parameter pointing to a valid QGIS project file')


    def get(self, tilemapid, tilematrixid, tilecolid, tilerowid, extension):
        project = self._context.project()

        mimetype = self.mimetypeFromExtension(extension)
        parameters = {
            "MAP": project.fileName(),
            "SERVICE": "WMTS",
            "VERSION": "1.0.0",
            "REQUEST": "GetTile",
            "LAYER": tilemapid,
            "STYLE": "",
            "TILEMATRIXSET": "EPSG:3857",
            "TILEMATRIX": tilematrixid,
            "TILEROW": tilerowid,
            "TILECOL": tilecolid,
            "FORMAT": mimetype,
        }
        qs = "?" + "&".join("%s=%s" % item for item in parameters.items())
        req = QgsBufferServerRequest(qs, QgsServerRequest.GetMethod, {}, None)
        service = self._srv_iface.serviceRegistry().getService('WMTS', '1.0.0')
        service.executeRequest(req, self._response, project );
        self._finished = True


def init_tms_api(serverIface) -> None:
    """ Initialize the Tile Map Server API
    """
    kwargs = dict(srv_iface = serverIface)

    tilemapid = r"tilemaps/(?P<tilemapid>[^/?]+)"

    handlers = [
        (rf"/{tilemapid}/(?P<tilematrixid>\d+)/(?P<tilecolid>\d+)/(?P<tilerowid>\d+)\.(?P<extension>[^/?]+)/?", TileMapContent,  kwargs),
        (rf"/{tilemapid}/?", TileMapInfo,  kwargs),
        (rf"/?", LandingPage, kwargs),
    ]

    register_api_handlers(serverIface, '/tms', 'TileMapService', handlers)
