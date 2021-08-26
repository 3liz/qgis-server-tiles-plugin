import json
import logging
import os

from shutil import rmtree

import lxml.etree

from qgis.core import Qgis, QgsProject

LOGGER = logging.getLogger('server')


def test_tmsapi_no_project(client):
    """ Test Project file error
    """
    plugin = client.getplugin('tilesForServer')
    assert plugin is not None

    # TMS API request
    qs = "/tms?"
    rv = client.get(qs)
    assert rv.status_code == 500
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'httpcode' in json_content
    assert json_content['httpcode'] == 500
    assert 'status' in json_content
    assert json_content['status'] == 'error'
    assert 'error' in json_content
    assert 'message' in json_content['error']

    # Get undefined project
    project = QgsProject()
    project.setFileName(client.getprojectpath("undefined.qgs").strpath)

    # TMS API request
    qs = "/tms?MAP=%s" % project.fileName()
    rv = client.get(qs)
    assert rv.status_code == 500
    assert rv.headers.get('Content-Type',"").startswith('application/json')

def test_tmsapi_landingpage(client):
    """ Test the TMS API -Landing page
        /tms?
    """
    plugin = client.getplugin('tilesForServer')
    assert plugin is not None

    # Get project
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # TMS API requests
    qs = "/tms?MAP=%s" % project.fileName()
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'title' in json_content

    assert 'abstract' in json_content

    assert 'tileMaps' in json_content
    assert len(json_content['tileMaps']) == 1
    tile_map = json_content['tileMaps'][0]
    assert 'id' in tile_map
    assert tile_map['id'] == 'france_parts'
    assert 'title' in tile_map
    assert tile_map['title'] == 'france_parts'
    assert 'abstract' in tile_map
    assert 'formats' in tile_map
    if Qgis.QGIS_VERSION_INT >= 31400:
        assert len(tile_map['formats']) == 2
    else:
        assert len(tile_map['formats']) == 1
    assert 'png' in tile_map['formats']
    if Qgis.QGIS_VERSION_INT >= 31400:
        assert 'pbf' in tile_map['formats']
    assert 'links' in tile_map
    assert len(tile_map['links']) == 1
    assert 'title' in tile_map['links'][0]
    assert 'type' in tile_map['links'][0]
    assert 'rel' in tile_map['links'][0]
    assert 'href' in tile_map['links'][0]
    assert '/tms/france_parts' in tile_map['links'][0]['href']

    assert 'source_id' not in tile_map
    assert 'source_type' not in tile_map

    assert 'links' in json_content
    assert len(json_content['links']) == 0


    # Project with WMTS but not in EPSG:3857
    project.setFileName(client.getprojectpath("france_parts_grid_4326.qgs").strpath)
    qs = "/tms?MAP=%s" % project.fileName()
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'tileMaps' in json_content
    assert len(json_content['tileMaps']) == 0

    # Project without WMTS
    project.setFileName(client.getprojectpath("france_parts_no_wmts.qgs").strpath)
    qs = "/tms?MAP=%s" % project.fileName()
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'tileMaps' in json_content
    assert len(json_content['tileMaps']) == 0

def test_tmsapi_tilemapinfo(client):
    """ Test the TMS API -Landing page
        /tms/{tilemapid}?
    """
    plugin = client.getplugin('tilesForServer')
    assert plugin is not None

    # Get project
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # TMS API requests
    qs = "/tms/france_parts?MAP=%s" % project.fileName()
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'id' in json_content
    assert json_content['id'] == 'france_parts'
    assert 'title' in json_content
    assert json_content['title'] == 'france_parts'
    assert 'abstract' in json_content
    assert 'bbox' in json_content
    assert 'formats' in json_content
    if Qgis.QGIS_VERSION_INT >= 31400:
        assert len(json_content['formats']) == 2
    else:
        assert len(json_content['formats']) == 1
    assert 'extension' in json_content['formats'][0]
    assert json_content['formats'][0]['extension'] == 'png'
    assert 'mimetype' in json_content['formats'][0]
    assert json_content['formats'][0]['mimetype'] == 'image/png'
    if Qgis.QGIS_VERSION_INT >= 31400:
        assert 'extension' in json_content['formats'][1]
        assert json_content['formats'][1]['extension'] == 'pbf'
        assert 'mimetype' in json_content['formats'][1]
        assert json_content['formats'][1]['mimetype'] == 'application/x-protobuf'

    # TMS API request - tilemapid unknwon
    qs = "/tms/unknwon?MAP=%s" % project.fileName()
    rv = client.get(qs)
    assert rv.status_code == 404
    assert rv.headers.get('Content-Type',"").startswith('application/json')

    json_content = json.loads(rv.content)
    assert 'httpcode' in json_content
    assert json_content['httpcode'] == 404
    assert 'status' in json_content
    assert json_content['status'] == 'error'
    assert 'error' in json_content
    assert 'message' in json_content['error']

def test_tmsapi_tilemapcontent(client):
    """ Test the TMS API -Landing page
        /tms/{tilemapid}/{tilematrixid}/{tilecolid}/{tilerowid}?
    """
    plugin = client.getplugin('tilesForServer')
    assert plugin is not None

    # Get project
    project = QgsProject()
    project.setFileName(client.getprojectpath("france_parts.qgs").strpath)

    # TMS API requests
    qs = "/tms/france_parts/0/0/0.png?MAP=%s" % project.fileName()
    rv = client.get(qs)
    assert rv.status_code == 200
    assert rv.headers.get('Content-Type',"").startswith('image/png')
    assert len(rv.content) > 0

    if Qgis.QGIS_VERSION_INT >= 31400:
        qs = "/tms/france_parts/0/0/0.pbf?MAP=%s" % project.fileName()
        rv = client.get(qs)
        assert rv.status_code == 200
        assert rv.headers.get('Content-Type',"").startswith('application/x-protobuf')
        assert len(rv.content) > 0

    # TMS API request - No project
    qs = "/tms/france_parts/0/0/0.png"
    rv = client.get(qs)
    assert rv.status_code == 500
    assert rv.headers.get('Content-Type',"").startswith('application/json')
