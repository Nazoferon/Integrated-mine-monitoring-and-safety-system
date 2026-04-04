from django.core.cache import cache
from .models import Employee, MinerDevice, InfrastructureDevice

def sidebar_counters(request):
    # Рахуємо тільки якщо користувач авторизований (щоб не було помилок на сторінці логіну)
    if request.user.is_authenticated:
        total_employees = cache.get('total_employees')
        if total_employees is None:
            total_employees = Employee.objects.count()
            cache.set('total_employees', total_employees, 300)
            
        total_devices = cache.get('total_devices')
        if total_devices is None:
            total_devices = MinerDevice.objects.count() + InfrastructureDevice.objects.count()
            cache.set('total_devices', total_devices, 300)
        
        return {
            'global_total_employees': total_employees,
            'global_total_devices': total_devices,
            # Тут можна буде додати ще лічильник активних тривог (Сповіщень)
        }
    return {}