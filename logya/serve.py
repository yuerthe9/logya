# -*- coding: utf-8 -*-
import os
import shutil
import logging
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from logya import Logya
from writer import DocWriter

class Serve(Logya):
    """Serve files from deploy directory."""

    def __init__(self, **kwargs):

        host = 'localhost'
        if kwargs.has_key('host') and kwargs['host']:
            host =  kwargs['host']

        port = 8080
        if kwargs.has_key('port') and kwargs['port']:
            port =  kwargs['port']

        super(self.__class__, self).__init__()
        Server(self, host, port).serve()

    def update_file(self, src, dst):
        """Copy source file to destination file if source is newer.

        Creates destination directory and file if they don't exist.
        """

        # make sure destination directory exists
        dir_dst = os.path.dirname(dst)
        if not os.path.exists(dir_dst):
            os.makedirs(dir_dst)

        if not os.path.isfile(dst):
            shutil.copy(src, dir_dst)
            return True

        if os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copyfile(src, dst)
            return True

        return False

    def refresh_resource(self, path):
        """Refresh resource corresponding to given path.

        Static files are updated if necessary, documents are read, parsed and
        written to the corresponding destination in the deploy directory."""

        # has to be done here too to keep track of configuration changes
        self.init_env()

        # if a file relative to static source is requested update it and return
        path_rel = path.lstrip('/')
        file_src = os.path.join(self.dir_static, path_rel)
        if os.path.isfile(file_src):
            file_dst = os.path.join(self.dir_dst, path_rel)
            if self.update_file(file_src, file_dst):
                return "Copied file %s to %s" % (file_src, file_dst)
            return "Source %s is not newer than destination %s" % (file_src, file_dst)

        # build indexes and docs_parsed dict
        self.build_indexes()

        # try to get doc at path, regenerate it and return
        doc = None
        if self.docs_parsed.has_key(path):
            doc = self.docs_parsed[path]
        else:
            # if a path like /index.html is requested also try to find /
            alt_path = os.path.dirname(path)
            if not alt_path.endswith('/'):
                alt_path = '%s/' % alt_path
            if self.docs_parsed.has_key(alt_path):
                doc = self.docs_parsed[alt_path]

        if doc:
            dw = DocWriter(self.dir_dst, self.template)
            dw.write(doc, self.get_doc_template(doc))
            self.write_indexes()
            return "Refreshed doc at URL: %s" % path

        # TODO refresh index if auto-generated index file is requested

class Server(HTTPServer):
    """Logya HTTPServer based class to serve generated site."""

    def __init__(self, logya, address, port):
        """Initialize HTTPServer listening on the specified address and port."""

        self.logya = logya
        self.address = address
        self.port = port

        self.logya.init_env()

        log_file = os.path.join(self.logya.dir_current, 'server.log')
        logging.basicConfig(filename=log_file, level=logging.INFO)

        HTTPServer.__init__(self, (address, port), HTTPRequestHandler)

    def serve(self):
        """Serve static files from logya deploy directory."""

        os.chdir(self.logya.dir_dst)
        print 'Serving on http://%s:%s/' % (self.address, self.port)
        self.serve_forever()

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    """Logya SimpleHTTPRequestHandler based class to return resources."""

    def do_GET(self):
        """Return refreshed resource."""

        logging.info("Requested resource: %s" % self.path)
        logging.info(self.server.logya.refresh_resource(self.path))
        SimpleHTTPRequestHandler.do_GET(self)