"""Seeds a 'trial' Plan — the default plan every Organization gets on
creation via apps/billing/signals.py's post_save receiver, until they
subscribe to a paid plan through Paystack/Opay checkout."""
from django.db import migrations


def seed_trial_plan(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.get_or_create(
        code="trial",
        defaults={
            "name": "Trial",
            "seat_limit": 3,
            "project_limit": 2,
            "monthly_price_ngn": 0,
            "is_active": True,
        },
    )


def unseed_trial_plan(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.filter(code="trial").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_alter_entitlement_provider_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_trial_plan, reverse_code=unseed_trial_plan),
    ]
