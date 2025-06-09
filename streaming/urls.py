from django.urls import path
from .views import GeneratePixMessagesView
from django.contrib import admin
from django.urls import path
from streaming.views import PixStreamStartView

urlpatterns = [
    path('api/util/msgs/<str:ispb>/<str:number>', GeneratePixMessagesView.as_view()),
    path('api/pix/<str:ispb>/stream/start', PixStreamStartView.as_view()),
]
