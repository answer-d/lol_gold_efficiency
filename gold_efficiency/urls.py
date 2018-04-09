from django.urls import path
from . import views


app_name = 'gold_efficiency'
urlpatterns = [
    path('', views.index, name='index'),
    path('itemlist/', views.itemlist, name='itemlist'),
    path('item/<int:item_id>/', views.itemdetail, name='itemdetail'),
]
