from django.urls import path

from apps.billing.views import OpayWebhookView, PaystackWebhookView

app_name = "billing"

urlpatterns = [
    path("webhooks/paystack/", PaystackWebhookView.as_view(), name="paystack_webhook"),
    path("webhooks/opay/", OpayWebhookView.as_view(), name="opay_webhook"),
]
