from pydantic import BaseModel, Field, RootModel
from typing import List, Optional, Union

class NutrientInfo(BaseModel):
    id: int
    number: str
    name: str
    rank: int
    unitName: str

class FoodNutrient(BaseModel):
    nutrient: NutrientInfo
    amount: Optional[float] = None

class FoodCategory(BaseModel):
    description: str
    code: Optional[str] = None
    id: Optional[int] = None

class MeasureUnit(BaseModel):
    id: int
    name: str
    abbreviation: str

class FoodPortion(BaseModel):
    id: int
    amount: Optional[float] = None
    gramWeight: Optional[float] = None
    modifier: Optional[str] = None
    portionDescription: Optional[str] = None
    sequenceNumber: int
    measureUnit: MeasureUnit

class FoodItem(BaseModel):
    fdcId: int = Field(..., description="FoodData Central ID. Custom foods should use negative IDs.")
    description: str
    foodClass: Optional[str] = "Custom"
    foodCategory: Optional[FoodCategory] = None
    foodNutrients: List[FoodNutrient] = []
    foodPortions: List[FoodPortion] = []
    publicationDate: Optional[str] = None
    foodComponents: List[dict] = []
    foodAttributes: List[dict] = []
    tableAbbreviation: Optional[str] = None
    nutrientConversionFactors: List[dict] = []
    isHistoricalReference: Optional[bool] = None
    ndbNumber: Optional[Union[str, int]] = None
    dataType: Optional[str] = None
    inputFoods: List[dict] = []

class FoodItemCreate(FoodItem):
    pass

class FoodList(RootModel[List[FoodItem]]):
    pass 