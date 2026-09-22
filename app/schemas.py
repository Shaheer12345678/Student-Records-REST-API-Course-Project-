"""Request and response bodies.

Table models are never used as request bodies: that would let a client set its own
primary key. Every write goes through one of the payload models below.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Unknown fields are rejected rather than silently dropped, and surrounding
# whitespace is stripped before the length rules are applied.
STRICT_BODY = ConfigDict(extra="forbid", str_strip_whitespace=True)

COURSE_CODE_PATTERN = r"^[A-Za-z]{2,4}[0-9]{3}$"
GRADE_PATTERN = r"^[A-DF]$"


class StudentCreate(BaseModel):
    """Payload for creating a student."""

    model_config = STRICT_BODY

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        """Store emails in one case so uniqueness is not case dependent."""
        return value.lower()


class StudentUpdate(StudentCreate):
    """Payload for replacing a student; same shape as creating one."""


class StudentRead(BaseModel):
    """Student as returned by the API."""

    id: int
    name: str
    email: str


class CourseCreate(BaseModel):
    """Payload for creating a course."""

    model_config = STRICT_BODY

    code: str = Field(pattern=COURSE_CODE_PATTERN)
    title: str = Field(min_length=1, max_length=200)
    credits: int = Field(default=3, ge=1, le=6)

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        """Course codes are canonically uppercase."""
        return value.upper()


class CourseUpdate(CourseCreate):
    """Payload for replacing a course; same shape as creating one."""


class CourseRead(BaseModel):
    """Course as returned by the API."""

    id: int
    code: str
    title: str
    credits: int


class EnrollmentCreate(BaseModel):
    """Payload for enrolling a student in a course."""

    model_config = STRICT_BODY

    student_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    grade: str | None = Field(default=None, pattern=GRADE_PATTERN)


class EnrollmentGradeUpdate(BaseModel):
    """Payload for recording or clearing a grade."""

    model_config = STRICT_BODY

    grade: str | None = Field(pattern=GRADE_PATTERN)


class EnrollmentRead(BaseModel):
    """Enrollment as returned by the API."""

    id: int
    student_id: int
    course_id: int
    grade: str | None
