class _Config:
    """
    :ivar endpoint: url path for docs
    :ivar filename: openapi spec file name
    :ivar openapi_version: openapi spec version
    :ivar title: document title
    :ivar version: service version
    :ivar ui: ui theme, choose 'redoc' or 'swagger'
    :ivar mode: mode for route. **normal** includes undecorated routes and
        routes decorated by this instance. **strict** only includes routes
        decorated by this instance. **greedy** includes all the routes.
    Flaskerk configuration.
    """

    def __init__(self):
        self.name = 'siwadoc'
        self.endpoint = '/docs/'
        self.url_prefix = None
        self.template_folder = None
        self.filename = 'openapi.json'

        self.openapi_veresion = '3.0.2'
        self.title = 'api'
        self.version = 'latest'
        self.ui = 'redoc'
        self._support_ui = {'redoc', 'swagger', 'rapidoc'}
        self._support_mode = {'normal', 'greedy', 'strict'}


config = _Config()
