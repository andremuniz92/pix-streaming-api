from django.contrib import admin
from .models import PixMessage, StreamSession

admin.site.register(PixMessage)
admin.site.register(StreamSession)

