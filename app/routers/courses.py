"""Course resource routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, select

from ..database import get_session
from ..errors import conflict, not_found
from ..models import Course, Enrollment
from ..schemas import CourseCreate, CourseRead, CourseUpdate

router = APIRouter(prefix="/courses", tags=["courses"])


def _get_course_or_404(session: Session, course_id: int) -> Course:
    course = session.get(Course, course_id)
    if course is None:
        raise not_found("Course", course_id)
    return course


def _reject_duplicate_code(session: Session, code: str, exclude_id: int | None = None) -> None:
    statement = select(Course).where(Course.code == code)
    if exclude_id is not None:
        statement = statement.where(Course.id != exclude_id)
    if session.exec(statement).first() is not None:
        raise conflict("duplicate_code", f"A course with code {code} already exists")


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, session: Session = Depends(get_session)) -> Course:
    """Create a course."""
    _reject_duplicate_code(session, payload.code)
    course = Course(**payload.model_dump())
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@router.get("", response_model=list[CourseRead])
def list_courses(
    q: str | None = Query(default=None, max_length=200, description="Case insensitive code or title filter"),
    session: Session = Depends(get_session),
) -> list[Course]:
    """List courses, optionally filtered by code or title."""
    statement = select(Course).order_by(Course.id)
    if q:
        pattern = f"%{q.strip().lower()}%"
        statement = statement.where(Course.code.ilike(pattern) | Course.title.ilike(pattern))
    return list(session.exec(statement).all())


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: int, session: Session = Depends(get_session)) -> Course:
    """Fetch a single course."""
    return _get_course_or_404(session, course_id)


@router.put("/{course_id}", response_model=CourseRead)
def replace_course(
    course_id: int, payload: CourseUpdate, session: Session = Depends(get_session)
) -> Course:
    """Replace a course's details."""
    course = _get_course_or_404(session, course_id)
    _reject_duplicate_code(session, payload.code, exclude_id=course_id)
    course.code = payload.code
    course.title = payload.title
    course.credits = payload.credits
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, session: Session = Depends(get_session)) -> None:
    """Delete a course and the enrollments that point at it."""
    course = _get_course_or_404(session, course_id)
    enrollments = session.exec(select(Enrollment).where(Enrollment.course_id == course_id)).all()
    for enrollment in enrollments:
        session.delete(enrollment)
    session.delete(course)
    session.commit()
