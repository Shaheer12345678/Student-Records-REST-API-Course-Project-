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
