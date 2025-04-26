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
SQLModel.metadata.create_all(engine)

def get_sess():
    return Session(engine)

@app.post("/students", response_model=Student)
def create_student(s: Student):
    with get_sess() as ses:
        ses.add(s)
        ses.commit()
        ses.refresh(s)
        return s

@app.get("/students")
def list_students():
    with get_sess() as ses:
        return ses.exec(select(Student)).all()

@app.post("/courses", response_model=Course)
def create_course(c: Course):
    with get_sess() as ses:
        ses.add(c); ses.commit(); ses.refresh(c); return c

@app.get("/courses")
def list_courses():
    with get_sess() as ses:
        return ses.exec(select(Course)).all()

@app.post("/enrollments", response_model=Enrollment)
def enroll(e: Enrollment):
    with get_sess() as ses:
        # basic referential check
        if not ses.get(Student, e.student_id) or not ses.get(Course, e.course_id):
            raise HTTPException(status_code=400, detail="Bad ids")
        ses.add(e); ses.commit(); ses.refresh(e); return e

@app.get("/enrollments")
def list_enrollments():
    with get_sess() as ses:
        return ses.exec(select(Enrollment)).all()


