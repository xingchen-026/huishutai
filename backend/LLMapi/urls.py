from django.urls import path

from LLMapi import views

urlpatterns = [
    path("provider-templates/", views.provider_templates, name="llm-provider-templates"),
    path("providers/", views.providers, name="llm-providers"),
    path("providers/<int:provider_id>/", views.provider_detail, name="llm-provider-detail"),
    path("providers/<int:provider_id>/refresh-models/", views.provider_refresh_models, name="llm-provider-refresh-models"),
    path("providers/<int:provider_id>/models/", views.provider_models, name="llm-provider-models"),
    path("models/", views.models, name="llm-models"),
    path("models/<int:model_pk>/", views.model_detail, name="llm-model-detail"),
    path("chat/", views.chat, name="llm-chat"),
    path("embeddings/", views.embeddings, name="llm-embeddings"),
]