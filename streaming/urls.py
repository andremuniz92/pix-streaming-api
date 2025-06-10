from django.urls import path
from .views import GeneratePixMessagesView, PixStreamStartView, PixStreamContinueDeleteView
from django.urls import path

urlpatterns = [
    path('api/util/msgs/<str:ispb>/<str:number>', GeneratePixMessagesView.as_view(), name='generate_pix_messages'),
    path('api/pix/<str:ispb>/stream/start', PixStreamStartView.as_view(), name='pix_stream_start'),
    path('api/pix/<str:ispb>/stream/<str:interaction_id>', PixStreamContinueDeleteView.as_view(), name='pix_stream_continue_delete'),
]
