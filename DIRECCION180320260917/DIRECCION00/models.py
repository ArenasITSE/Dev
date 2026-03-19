from sqlalchemy import Column, Integer, String, ForeignKey, Text, Date, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from appdb import Base

class Unidad(Base):
    __tablename__ = "unidades"
    # tus columnas reales aquí

class Puesto(Base):
    __tablename__ = "puestos"
    # tus columnas reales aquí

class Personal(Base):
    __tablename__ = "personal"
    # tus columnas reales aquí