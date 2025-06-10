import json
from rest_framework.renderers import BaseRenderer

class MultipartJsonRenderer(BaseRenderer):
    media_type = 'multipart/json'
    format = 'multipartjson'
    charset = 'utf-8'

    def render(self, data, media_type=None, renderer_context=None):
        return json.dumps(data).encode(self.charset)

