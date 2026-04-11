from django.db.models import Count, Max
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from .models import Employee, SecurityAlert, TelemetryLog, OTALog


def dashboard_callback(request, context):
    online_staff_count = Employee.objects.exclude(safety_status='OFF_SHIFT').count()
    active_alerts_count = SecurityAlert.objects.filter(is_resolved=False).count()
    max_gas = TelemetryLog.objects.aggregate(max_gas=Max('gas_level'))['max_gas'] or 0

    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)
    alerts_by_day = list(
        SecurityAlert.objects.filter(created_at__date__gte=seven_days_ago)
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    chart_data = {(seven_days_ago + timedelta(days=i)).strftime("%d.%m"): 0 for i in range(7)}
    for item in alerts_by_day:
        day_str = item['day'].strftime("%d.%m")
        if day_str in chart_data:
            chart_data[day_str] = item['count']

    latest_alerts = SecurityAlert.objects.filter(is_resolved=False).select_related("employee").order_by("-created_at")[:5]
    latest_ota = OTALog.objects.select_related("device").order_by("-timestamp")[:5]

    context.update({
        "online_staff_count": online_staff_count,
        "active_alerts_count": active_alerts_count,
        "max_gas": f"{max_gas:.1f} % LEL",
        "chart_labels": list(chart_data.keys()),
        "chart_values": list(chart_data.values()),
        "latest_alerts": latest_alerts,
        "latest_ota": latest_ota,
    })
    return context