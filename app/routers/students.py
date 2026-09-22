"""Student resource routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, select

from ..database import get_session
from ..errors import conflict, not_found
from ..models import Enrollment, Student
from ..schemas import EnrollmentRead, StudentCreate, StudentRead, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])


def _get_student_or_404(session: Session, student_id: int) -> Student:
    student = session.get(Student, student_id)
    if student is None:
        raise not_found("Student", student_id)
    return student


def _reject_duplicate_email(session: Session, email: str, exclude_id: int | None = None) -> None:
    statement = select(Student).where(Student.email == email)
    if exclude_id is not None:
        statement = statement.where(Student.id != exclude_id)
    if session.exec(statement).first() is not None:
        raise conflict("duplicate_email", f"A student with email {email} already exists")


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, session: Session = Depends(get_session)) -> Student:
    """Create a student."""
    _reject_duplicate_email(session, payload.email)
    student = Student(**payload.model_dump())
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.get("", response_model=list[StudentRead])
def list_students(
    q: str | None = Query(default=None, max_length=100, description="Case insensitive name or email filter"),
    session: Session = Depends(get_session),
) -> list[Student]:
    """List students, optionally filtered by name or email."""
    statement = select(Student).order_by(Student.id)
    if q:
        pattern = f"%{q.strip().lower()}%"
        statement = statement.where(
            Student.name.ilike(pattern) | Student.email.ilike(pattern)
        )
    return list(session.exec(statement).all())


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: int, session: Session = Depends(get_session)) -> Student:
    """Fetch a single student."""
    return _get_student_or_404(session, student_id)


@router.put("/{student_id}", response_model=StudentRead)
def replace_student(
    student_id: int, payload: StudentUpdate, session: Session = Depends(get_session)
) -> Student:
    """Replace a student's details."""
    student = _get_student_or_404(session, student_id)
    _reject_duplicate_email(session, payload.email, exclude_id=student_id)
    student.name = payload.name
    student.email = payload.email
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, session: Session = Depends(get_session)) -> None:
    """Delete a student and the enrollments that point at them."""
    student = _get_student_or_404(session, student_id)
    enrollments = session.exec(select(Enrollment).where(Enrollment.student_id == student_id)).all()
    for enrollment in enrollments:
        session.delete(enrollment)
    session.delete(student)
    session.commit()


@router.get("/{student_id}/enrollments", response_model=list[EnrollmentRead])
def list_student_enrollments(
    student_id: int, session: Session = Depends(get_session)
) -> list[Enrollment]:
    """List the enrollments belonging to one student."""
    _get_student_or_404(session, student_id)
    statement = select(Enrollment).where(Enrollment.student_id == student_id).order_by(Enrollment.id)
    return list(session.exec(statement).all())
