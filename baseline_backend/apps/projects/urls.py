from rest_framework.routers import DefaultRouter

from apps.projects.views import ProjectViewSet, TaskViewSet

app_name = "projects"

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
