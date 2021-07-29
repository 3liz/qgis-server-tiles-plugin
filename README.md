# Tiles API

Add tiles API to QGIS Server
* Tiles Map Service API
* OGC Tiles API

## Tile Map Service API - TMS

The TMS API provides these URLs:
* `/tms/?`
  * to get information on the Tile Map Service based on WMTS Server project configuration
* `/tms/tilemaps/(?<tileMapId>[^/]+)/?`
  * to get information on a tile map based on WMTS Server project configuration
* `/tms/tilemaps/(?<tileMapId>[^/]+)/(?P<tilematrixid>\d+)/(?P<tilecolid>\d+)/(?P<tilerowid>\d+)\.(?P<extension>[^/?]+)/?`
  * to get tile map content based on extension
