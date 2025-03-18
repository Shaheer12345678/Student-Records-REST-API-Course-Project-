from fastapi import FastAPI, HTTPException
from sqlmodel import Field, SQLModel, create_engine, Session, select

app = FastAPI(title="Student Records API")

class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str

class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str
    title: str

class Enrollment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    course_id: int = Field(foreign_key="course.id")

engine = create_engine("sqlite:///db.sqlite", echo=False)
