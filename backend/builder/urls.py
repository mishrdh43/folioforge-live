from django.urls import path
from .views import ParseResumeView, GeneratePDFView, CreateOrderView

urlpatterns = [
    path('parse/', ParseResumeView.as_view(), name='parse_resume'),
    path('generate-pdf/', GeneratePDFView.as_view(), name='generate_pdf'),
    path('create-order/', CreateOrderView.as_view(), name='create_order'),
]
