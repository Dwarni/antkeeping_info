from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("badge/", views.NotificationBadgeView.as_view(), name="badge"),
    path("dropdown/", views.NotificationDropdownView.as_view(), name="dropdown"),
    path("<int:pk>/open/", views.NotificationOpenView.as_view(), name="open"),
    path(
        "<int:pk>/toggle-read/",
        views.NotificationToggleReadView.as_view(),
        name="toggle_read",
    ),
    path(
        "mark-all-read/",
        views.NotificationMarkAllReadView.as_view(),
        name="mark_all_read",
    ),
    path(
        "<int:pk>/delete/",
        views.NotificationDeleteView.as_view(),
        name="delete",
    ),
    path(
        "entry/<int:entry_pk>/toggle-mute/",
        views.NotificationToggleThreadMuteView.as_view(),
        name="toggle_thread_mute",
    ),
    path("settings/", views.NotificationSettingsView.as_view(), name="settings"),
]
