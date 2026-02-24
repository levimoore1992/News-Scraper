from django.urls import path
from . import views

urlpatterns = [
    path("referral/", views.update_referral_source, name="update_referral_source"),
]
