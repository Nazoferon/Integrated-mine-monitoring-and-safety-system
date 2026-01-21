from django.db import models

class Category(models.Model):
    name = models.CharField("Назва категорії", max_length=100)
    slug = models.SlugField("URL ідентифікатор (напр. 'web')", unique=True)
    icon_class = models.CharField("FontAwesome іконка", max_length=50, default="fas fa-code", help_text="Наприклад: fas fa-mobile-alt")
    order = models.IntegerField("Порядок відображення", default=0)

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"
        ordering = ['order']

    def __str__(self):
        return self.name

class Project(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='projects', verbose_name="Категорія")
    title = models.CharField("Назва проєкту", max_length=200)
    description = models.TextField("Опис", blank=True)
    image = models.ImageField("Зображення (скріншот/рендер)", upload_to='projects/', blank=True, null=True)
    
    tech_stack = models.CharField("Технології (через кому)", max_length=200, help_text="Напр: Python, Django, SQL")
    
    github_link = models.URLField("GitHub Link", blank=True)
    demo_link = models.URLField("Demo/Live Link", blank=True)
    
    is_completed = models.BooleanField("Завершено?", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Проєкт"
        verbose_name_plural = "Проєкти"
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def get_tech_list(self):
        """Перетворює рядок технологій у список для шаблону"""
        if self.tech_stack:
            return [x.strip() for x in self.tech_stack.split(',')]
        return []