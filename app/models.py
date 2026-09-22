"""Database tables."""

from sqlmodel import Field, SQLModel, UniqueConstraint


class Student(SQLModel, table=True):
    """A student who can be enrolled in courses."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    email: str = Field(max_length=254, unique=True, index=True)


class Course(SQLModel, table=True):
    """A course a student can enrol in."""

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, unique=True, index=True)
    title: str = Field(max_length=200)
    credits: int = Field(default=3)


class Enrollment(SQLModel, table=True):
    """The link between a student and a course, with an optional grade."""

    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),)

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    grade: str | None = Field(default=None, max_length=1)
