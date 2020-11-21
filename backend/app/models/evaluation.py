from typing import Optional, Union

from pydantic import conint, confloat, Field

from app.models.core import DateTimeModelMixin, CoreModel
from app.models.user import UserPublic
from app.models.cleaning import CleaningPublic


class EvaluationBase(CoreModel):
    no_show: bool = False
    headline: Optional[str]
    comment: Optional[str]
    professionalism: Optional[conint(ge=0, le=5)]
    completeness: Optional[conint(ge=0, le=5)]
    efficiency: Optional[conint(ge=0, le=5)]
    overall_rating: Optional[conint(ge=0, le=5)]


class EvaluationCreate(EvaluationBase):
    overall_rating: conint(ge=0, le=5)


class EvaluationUpdate(EvaluationBase):
    pass


class EvaluationInDB(DateTimeModelMixin, EvaluationBase):
    cleaner_id: int
    cleaning_id: int


class EvaluationPublic(EvaluationInDB):
    owner: Optional[Union[int, UserPublic]]
    cleaner: Union[int, UserPublic] = Field(..., alias="cleaner_id")
    cleaning: Union[int, CleaningPublic] = Field(..., alias="cleaning_id")

    class Config:
        allow_population_by_field_name = True


class EvaluationAggregate(CoreModel):
    avg_professionalism: confloat(ge=0, le=5)
    avg_completeness: confloat(ge=0, le=5)
    avg_efficiency: confloat(ge=0, le=5)
    avg_overall_rating: confloat(ge=0, le=5)
    max_overall_rating: conint(ge=0, le=5)
    min_overall_rating: conint(ge=0, le=5)
    one_stars: conint(ge=0)
    two_stars: conint(ge=0)
    three_stars: conint(ge=0)
    four_stars: conint(ge=0)
    five_stars: conint(ge=0)
    total_evaluations: conint(ge=0)
    total_no_show: conint(ge=0)
