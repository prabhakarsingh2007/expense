from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add/', views.add_expense, name='add_expense'),
    path('report/', views.report, name='report'),
    path('edit/<int:id>/', views.edit_expense, name='edit_expense'),
    path('delete/<int:id>/', views.delete_expense, name='delete_expense'),
       # Existing URLs...
    path('budget/', views.set_budget, name='set_budget'),
    path('search/', views.search_expenses, name='search'),
    path('export/', views.export_csv, name='export_csv'),


    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),
]



