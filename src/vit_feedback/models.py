from typing import Literal
from pydantic import BaseModel, Field

class CourseItem(BaseModel):
    class_nbr: str = ""
    course_code: str
    title: str = ""
    course_type: str = ""
    faculty_name: str = ""
    status: str = "Pending"
    table_type: Literal["class_wise", "course_outcome"] = "class_wise"
    course_id: str = ""
    param_type: str = ""

    @property
    def is_posted(self) -> bool:
        return self.status.strip().lower() == "posted"

    @property
    def is_pending(self) -> bool:
        return not self.is_posted

class RatingPolicy(BaseModel):
    default_rating: int = Field(default=5, ge=1, le=5)
    course_outcome_rating: int | None = Field(default=None, ge=1, le=5)
    course_overrides: dict[str, int] = Field(default_factory=dict)
    custom_suggestions: dict[str, str] = Field(default_factory=dict)
    default_suggestion: str = "The course structure and teaching methodologies were well executed."

    def get_rating_for(self, *identifiers: str) -> int:
        for ident in identifiers:
            if not ident:
                continue
            clean_id = ident.strip().upper()
            if not clean_id:
                continue
            for k, v in self.course_overrides.items():
                target = k.strip().upper()
                if not target:
                    continue
                if target in clean_id or clean_id in target:
                    return v
        return self.default_rating

    def get_co_rating(self, *identifiers: str) -> int:
        for ident in identifiers:
            if not ident:
                continue
            clean_id = ident.strip().upper()
            if not clean_id:
                continue
            for k, v in self.course_overrides.items():
                target = k.strip().upper()
                if not target:
                    continue
                if target in clean_id or clean_id in target:
                    return v
        return self.course_outcome_rating if self.course_outcome_rating is not None else self.default_rating

    def get_suggestions_for(self, *identifiers: str) -> str:
        for ident in identifiers:
            if not ident:
                continue
            clean_id = ident.strip().upper()
            if not clean_id:
                continue
            for k, v in self.custom_suggestions.items():
                target = k.strip().upper()
                if not target:
                    continue
                if target in clean_id or clean_id in target:
                    return v
        return self.default_suggestion

class FeedbackResult(BaseModel):
    status: Literal["success", "partial", "failed"] = "success"
    processed_courses: list[str] = Field(default_factory=list)
    failed_courses: list[str] = Field(default_factory=list)
    message: str = ""

    @property
    def is_success(self) -> bool:
        return self.status == "success" and len(self.failed_courses) == 0
