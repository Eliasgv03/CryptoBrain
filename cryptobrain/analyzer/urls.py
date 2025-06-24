from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('market_data/', views.market_data, name='market_data'),
    path('latest_news/', views.latest_news, name='latest_news'),
    path('analysis/', views.analysis, name='analysis'),
    path('price_chart/', views.price_chart, name='price_chart'),
]
