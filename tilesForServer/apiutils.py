""" Qgis API utils utils

    author: David Marteau (3liz)
    Copyright: (C) 2019 3Liz
"""
import json
import sys
import traceback

from http.client import responses as http_responses
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtCore import QRegularExpression, QUrl
from qgis.server import (
    QgsServerOgcApi,
    QgsServerOgcApiHandler,
    QgsServerRequest,
)


class HTTPError(Exception):

    def __init__(self, status_code: int=500, log_message: Optional[str] = None,
                 *args: Any, **kwargs: Any) -> None:
        self.status_code = status_code
        self.log_message = log_message
        self.args = args
        self.reason =  kwargs.get("reason", None)

    def __str__(self) -> str:
        message = "HTTP %d: %s" % (
            self.status_code,
            self.reason or http_responses.get(self.status_code, "Unknown"),
        )
        if self.log_message:
            return message + " (" + (self.log_message % self.args) + ")"
        else:
            return message


class RequestHandler:

    def __init__(self, parent: QgsServerOgcApiHandler,  context) -> None:
        self._parent   = parent
        self._context  = context
        self._response = context.response()
        self._request  = context.request()
        self._project  = context.project()
        self._project_needed = False
        self._finished = False

    def initialize(self, **kwargs: Any ) -> None:
        """ May be overrided
        """
        self._project_needed = True

    def prepare(self, **values):
        """
        """
        if self._project_needed and not self._project:
            raise HTTPError(500, 'Project file error. For Tiles API, please provide a MAP parameter pointing to a valid QGIS project file')

    def href(self, path: str="", extension: str="") -> str:
        """ Returns an URL to self, to be used for links to the current resources
            and as a base for constructing links to sub-resources
        """
        return self._parent.href(self._context,path,extension)

    def finish(self, chunk: Optional[Union[str, bytes, dict]] = None) -> None:
        """ Terminate the request
        """
        if self._finished:
            raise RuntimeError("finish() called twice")

        if chunk is not None:
            self.write(chunk)

        self._finished = True
        self._response.finish()

    def write(self, chunk: Union[str, bytes, dict]) -> None:
        """
        """
        if not isinstance(chunk, (bytes, str, dict)):
            raise TypeError("write() only accepts bytes, unicode, and dict objects")
        if isinstance(chunk, dict):
            chunk = json.dumps(chunk, sort_keys=True)
        self.set_header('Content-Type', 'application/json;charset=utf-8')
        self._response.write(chunk)

    def set_status(self, status_code: int, reason: Optional[str]=None) -> None:
        """
        """
        self._response.setStatusCode(status_code)
        if reason is not None:
            self._reason = reason
        else:
            self._reason = http_responses.get(status_code, "Unknown")

    def send_error(self, status_code: int = 500, **kwargs: Any) -> None:
        """
        """
        self._response.clear()
        reason = kwargs.get("reason")
        if "exc_info" in kwargs:
            exception = kwargs["exc_info"][1]
            if isinstance(exception, HTTPError) and exception.reason:
                reason = exception.reason
        self.set_status(status_code, reason=reason)
        self.write(dict(status="error" if status_code != 200 else "ok",
                        httpcode = status_code,
                        error    = { "message": self._reason }))

        if status_code > 300:
            QgsMessageLog.logMessage(f"Returned HTTP Error {status_code}: {self._reason}" , "tilesApi",Qgis.Critical)

        if not self._finished:
            self.finish()

    def set_header(self, name: str, value: str) -> None:
        """
        """
        self._response.setHeader(name,value)

    def _unimplemented_method(self, *args: str, **kwargs: str) -> None:
        raise HTTPError(405)

    head   = _unimplemented_method
    get    = _unimplemented_method
    post   = _unimplemented_method
    delete = _unimplemented_method
    patch  = _unimplemented_method
    put    = _unimplemented_method

    METHODS = {
        QgsServerRequest.HeadMethod  : 'head',
        QgsServerRequest.PutMethod   : 'put',
        QgsServerRequest.GetMethod   : 'get',
        QgsServerRequest.PostMethod  : 'post',
        QgsServerRequest.PatchMethod : 'patch',
        QgsServerRequest.DeleteMethod: 'delete',
    }

    def execute(self, values):
        """ Execute the request
        """
        try:
            method = self._request.method()
            if method not in self.METHODS:
                raise HTTPError(405)

            self.prepare( **values )
            if self._finished:
                return

            self.set_status(200)

            method = getattr(self, self.METHODS[method])
            method( **values )

            if not self._finished:
                self.finish()
        except Exception as e:
            if self._finished:
                # Nothing to send, but log for debugging purpose
                QgsMessageLog.logMessage(traceback.format_exc(), "tilesApi",Qgis.Critical)
                return
            if isinstance(e, HTTPError):
                QgsMessageLog.logMessage(e.log_message, "tilesApi", Qgis.Critical)
                self.send_error(e.status_code, exc_info=sys.exc_info())
            else:
                QgsMessageLog.logMessage(traceback.format_exc(), "tilesApi", Qgis.Critical)
                self.send_error(500, exc_info=sys.exc_info())



class RequestHandlerDelegate(QgsServerOgcApiHandler):
    """ Delegate request to handler
    """

    # XXX We need to preserve instances from garbage
    # collection
    __instances = []

    def __init__(self, path: str, handler: Type[RequestHandler],
                 content_types=[QgsServerOgcApi.JSON,],
                 kwargs: Dict={}):

        super().__init__()
        if content_types:
            self.setContentTypes(content_types)
        self._path = QRegularExpression(path)
        self._name = handler.__name__
        self._handler = handler
        self._kwargs = kwargs

        self.__instances.append(self)

    def path(self):
        return self._path

    def linkType(self):
        return QgsServerOgcApi.items

    def operationId(self):
        return f"tiles{self._name}"

    def summary(self):
        return f"Tiles {self._name}"

    def description(self):
        return f"Tiles {self._name}"

    def linkTitle(self):
        return f"Tiles {self._name}"

    def templatePath(self, context):
        # No templates!
        return ''

    def parameters(self, context):
        return []

    def handleRequest(self, context):
        """
        """
        handler = self._handler(self,context)
        handler.initialize(**self._kwargs)
        handler.execute(self.values(context))


class _ServerApi(QgsServerOgcApi):
    """ Redefine Accept method as to get exact match
    """
    __instances = []

    # See above
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.__instances.append(self)

    def accept(self, url: QUrl) -> bool:
        """ Override the api to actually match the rootpath
        """
        return url.path().startswith( self.rootPath() )


HandlerDefinition = Tuple[str,Type[RequestHandler],Dict]


def register_api_handlers(serverIface, rootpath: str, name: str, handlers: List[HandlerDefinition],
                          descripton: Optional[str]=None,
                          version: Optional[str]=None) -> None:

    api = _ServerApi(serverIface, rootpath, name, descripton, version)
    for path,handler,kwargs in handlers:
        kw = kwargs.copy() # Ensure that kwargs dict is not mutated
        content_types = kw.pop('content_types',[QgsServerOgcApi.JSON,])
        api.registerHandler(RequestHandlerDelegate(path,handler,content_types=content_types,
                                                   kwargs=kw))

    serverIface.serviceRegistry().registerApi(api)

