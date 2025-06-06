from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NutrientViewSet, 
    IngredientViewSet, 
    PersonProfileViewSet, 
    MealComponentViewSet, 
    MealPlanViewSet,
    IngredientSearchAPIView,
    FoodPortionViewSet,
    IngredientNutrientLinkViewSet,
    IngredientUsageViewSet,
    DietaryReferenceValueViewSet,
    AIIngredientCreationAPIView,
    validate_ingredient_description,
)

router = DefaultRouter()
router.register(r'nutrients', NutrientViewSet, basename='nutrient')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'personprofiles', PersonProfileViewSet, basename='personprofile')
router.register(r'mealcomponents', MealComponentViewSet, basename='mealcomponent')
router.register(r'mealplans', MealPlanViewSet, basename='mealplan')
router.register(r'foodportions', FoodPortionViewSet)
router.register(r'ingredientnutrientlinks', IngredientNutrientLinkViewSet)
router.register(r'ingredientusages', IngredientUsageViewSet)
router.register(r'dietaryreferencevalues', DietaryReferenceValueViewSet)
# Add other viewsets to the router here

urlpatterns = [
    path('ingredients/search/', IngredientSearchAPIView.as_view(), name='ingredient-search'),
    path('ingredients/ai-create/', AIIngredientCreationAPIView.as_view(), name='ai-ingredient-create'),
    path('ingredients/validate/', validate_ingredient_description, name='validate-ingredient-description'),
    path('', include(router.urls)),
] 