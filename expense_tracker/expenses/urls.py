from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
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
    path('about/', views.about_me, name='about_me'),
    path('recurring/', views.recurring_expenses, name='recurring_expenses'),
    path('recurring/delete/<int:id>/', views.delete_recurring_expense, name='delete_recurring_expense'),


    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),
]



