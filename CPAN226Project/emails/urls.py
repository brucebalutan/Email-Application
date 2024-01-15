from django.contrib import admin
from django.urls import path
from emails import views
from .views import compose_email
from .views import display_inbox
from .views import email_detail
from .views import login
from .views import reply_email
# urlpatterns = [path('compose_email', views.compose_email),
#                path('inbox', views.display_inbox)
# ]

urlpatterns = [path('', login, name='login'),  # This is the root URL pattern
    path('compose_email/', compose_email, name='compose_email'),
    path('inbox/<str:user_email>/<str:app_password>/', display_inbox, name='inbox'),
    path('email/<int:email_id>/', email_detail, name='email_detail'),
    path('reply_email/<int:email_id>/', reply_email, name='reply_email'),

]