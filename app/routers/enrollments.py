"""Enrollment resource routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, select

from ..database import get_session
from ..errors import bad_request, conflict, not_found
from ..models import Course, Enrollment, Student
from ..schemas import EnrollmentCreate, EnrollmentGradeUpdate, EnrollmentRead

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


def _get_enrollment_or_404(session: Session, enrollment_id: int) -> Enrollment:
    enrollment = session.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise not_found("Enrollment", enrollment_id)
    return enrollment


@router.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
def create_enrollment(
    payload: EnrollmentCreate, session: Session = Depends(get_session)
) -> Enrollment:
    """Enrol a student in a course."""
    # The ids live in the body, not the path, so an unknown id is a bad request
    # about the payload rather than a missing resource at this URL.
    if session.get(Student, payload.student_id) is None:
        raise bad_request("unknown_student", f"Student {payload.student_id} does not exist")
    if session.get(Course, payload.course_id) is None:
        raise bad_request("unknown_course", f"Course {payload.course_id} does not exist")

    existing = session.exec(
        select(Enrollment)
        .where(Enrollment.student_id == payload.student_id)
        .where(Enrollment.course_id == payload.course_id)
    ).first()
    if existing is not None:
        raise conflict(
            "duplicate_enrollment",
            f"Student {payload.student_id} is already enrolled in course {payload.course_id}",
        )

    enrollment = Enrollment(**payload.model_dump())
    session.add(enrollment)
    session.commit()
    session.refresh(enrollment)
    return enrollment


@router.get("", response_model=list[EnrollmentRead])
def list_enrollments(
    student_id: int | None = Query(default=None, gt=0),
    course_id: int | None = Query(default=None, gt=0),
    session: Session = Depends(get_session),
) -> list[Enrollment]:
    """List enrollments, optionally filtered by student or course."""
    statement = select(Enrollment).order_by(Enrollment.id)
    if student_id is not None:
        statement = statement.where(Enrollment.student_id == student_id)
    if course_id is not None:
        statement = statement.where(Enrollment.course_id == course_id)
    return list(session.exec(statement).all())


@router.get("/{enrollment_id}", response_model=EnrollmentRead)
def get_enrollment(enrollment_id: int, session: Session = Depends(get_session)) -> Enrollment:
    """Fetch a single enrollment."""
    return _get_enrollment_or_404(session, enrollment_id)


@router.patch("/{enrollment_id}", response_model=EnrollmentRead)
def update_enrollment_grade(
    enrollment_id: int, payload: EnrollmentGradeUpdate, session: Session = Depends(get_session)
) -> Enrollment:
    """Record or clear the grade on an enrollment."""
    enrollment = _get_enrollment_or_404(session, enrollment_id)
    enrollment.grade = payload.grade
    session.add(enrollment)
    session.commit()
    session.refresh(enrollment)
    return enrollment


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(enrollment_id: int, session: Session = Depends(get_session)) -> None:
    """Delete an enrollment."""
    enrollment = _get_enrollment_or_404(session, enrollment_id)
    session.delete(enrollment)
    session.commit()
