from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Events
    path('event/<slug:slug>/', views.event_detail, name='event_detail'),
    path('event/<slug:slug>/results/', views.event_results, name='event_results'),
    path('event/<slug:slug>/price/', views.get_vote_price, name='get_vote_price'),
    path('event/<slug:slug>/category/<int:category_id>/', views.category_detail, name='category_detail'),

    # Nominees & voting
    path('event/<slug:slug>/nominee/<int:nominee_id>/', views.nominee_detail, name='nominee_detail'),
    path('event/<slug:slug>/nominee/<int:nominee_id>/vote/', views.initiate_vote, name='initiate_vote'),

    # Payment
    path('vote/callback/<uuid:reference>/', views.payment_callback, name='payment_callback'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),
]
