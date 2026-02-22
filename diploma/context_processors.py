from .models import Employee, MinerDevice, InfrastructureDevice

def sidebar_counters(request):
    # Рахуємо тільки якщо користувач авторизований (щоб не було помилок на сторінці логіну)
    if request.user.is_authenticated:
        total_employees = Employee.objects.count()
        total_devices = MinerDevice.objects.count() + InfrastructureDevice.objects.count()
        
        return {
            'global_total_employees': total_employees,
            'global_total_devices': total_devices,
            # Тут можна буде додати ще лічильник активних тривог (Сповіщень)
        }
    return {}