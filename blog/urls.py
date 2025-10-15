from django.urls import path
from . import views

app_name = 'blog'


urlpatterns = [
    path('', views.blog_list, name='blog'),
    path('<slug:slug>/', views.blog_details, name='blog_details'),

]
