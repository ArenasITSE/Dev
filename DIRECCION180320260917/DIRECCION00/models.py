from sqlalchemy import Column, Integer, String, ForeignKey, Text, Date, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from appdb import Base


class Unidad(Base):
    __tablename__ = "unidades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)

    puestos = relationship("Puesto", back_populates="unidad", cascade="all, delete-orphan")


class Puesto(Base):
    __tablename__ = "puestos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    unidad_id = Column(Integer, ForeignKey("unidades.id"), nullable=True)

    unidad = relationship("Unidad", back_populates="puestos")
    personal = relationship("Personal", back_populates="puesto", cascade="all, delete-orphan")


class Personal(Base):
    __tablename__ = "personal"

    id = Column(Integer, primary_key=True, autoincrement=True)

    numero_empleado = Column(String, nullable=True)
    fotografia = Column(String, nullable=True)

    nombre = Column(String, nullable=True)
    apellido_paterno = Column(String, nullable=True)
    apellido_materno = Column(String, nullable=True)

    fecha_nacimiento = Column(Date, nullable=True)
    genero = Column(String, nullable=True)
    estado_civil = Column(String, nullable=True)
    domicilio = Column(Text, nullable=True)

    curp = Column(String, nullable=True)
    rfc = Column(String, nullable=True)
    nss = Column(String, nullable=True)

    celular_personal = Column(String, nullable=True)
    correo_personal = Column(String, nullable=True)
    telefono_oficina = Column(String, nullable=True)
    extension = Column(String, nullable=True)
    correo_institucional = Column(String, nullable=True)

    puesto_id = Column(Integer, ForeignKey("puestos.id"), nullable=True)

    grado_academico = Column(String, nullable=True)
    cvu = Column(String, nullable=True)

    edificio = Column(String, nullable=True)
    planta = Column(String, nullable=True)
    area_asignada = Column(String, nullable=True)

    titulo_abreviatura = Column(String, nullable=True)
    licenciatura = Column(String, nullable=True)
    maestria = Column(String, nullable=True)
    doctorado = Column(String, nullable=True)

    licenciatura_mencion_honorifica = Column(Boolean, nullable=True)
    maestria_mencion_honorifica = Column(Boolean, nullable=True)
    doctorado_mencion_honorifica = Column(Boolean, nullable=True)

    estado_residencia = Column(String, nullable=True)
    municipio_residencia = Column(String, nullable=True)
    localidad_residencia = Column(String, nullable=True)
    codigo_postal = Column(String, nullable=True)

    telefono_casa = Column(String, nullable=True)
    telefono_otro = Column(String, nullable=True)

    nombre_padre = Column(String, nullable=True)
    nombre_madre = Column(String, nullable=True)
    numero_hijos = Column(Integer, nullable=True)

    talla_camisa = Column(String, nullable=True)
    deporte = Column(String, nullable=True)
    actividad_cultural = Column(String, nullable=True)
    pasatiempo = Column(String, nullable=True)
    alergias = Column(Text, nullable=True)

    puesto = relationship("Puesto", back_populates="personal")