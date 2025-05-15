from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NutrientViewSet, 
    IngredientViewSet, 
    PersonProfileViewSet, 
    MealComponentViewSet, 
    MealPlanViewSet,
    IngredientSearchAPIView
)

router = DefaultRouter()
router.register(r'nutrients', NutrientViewSet, basename='nutrient')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'personprofiles', PersonProfileViewSet, basename='personprofile')
router.register(r'mealcomponents', MealComponentViewSet, basename='mealcomponent')
router.register(r'mealplans', MealPlanViewSet, basename='mealplan')
# Add other viewsets to the router here

urlpatterns = [
    path('ingredients/search/', IngredientSearchAPIView.as_view(), name='ingredient-search'),
    path('', include(router.urls)),
] 