# Tiles API

Add tiles API to QGIS Server
* Tiles Map Service API
* OGC Tiles API (in progress)

## Tile Map Service API - TMS

The TMS API provides these URLs:
* `/tms/?`
  * to get information on the Tile Map Service based on WMTS Server project configuration
* `/tms/(?<tileMapId>[^/]+)/?`
  * to get information on a tile map based on WMTS Server project configuration
* `/tms/(?<tileMapId>[^/]+)/(?P<tilematrixid>\d+)/(?P<tilecolid>\d+)/(?P<tilerowid>\d+)\.(?P<extension>[^/?]+)/?`
  * to get tile map content based on extension
  * the available extension is png, jpg, jpeg and pbf
  * the image formats, png and jpg, is configured in the project
  * the vector tile format is based on QGIS version > 3.14 and only available for vector layers
