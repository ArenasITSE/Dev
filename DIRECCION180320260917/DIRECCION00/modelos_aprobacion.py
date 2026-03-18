"""
Modelos SQLAlchemy para el Flujo de Aprobación de Datos (Solicitud de Captura).
Integrar en directorio.py después de las definiciones existentes (antes de create_engine).

Arquitectura: Tabla central SolicitudCaptura con payload JSON.
- No ensucia las tablas públicas.
- Permite comparación fácil: dato actual vs payload.
- Soporta modificar y agregar en todas las secciones.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship

# Usar el Base de directorio.py (importar donde se integre)
# from directorio import Base

def definir_modelos_aprobacion(Base):
    """Define los modelos de aprobación. Pasa el Base existente."""

    class SolicitudCaptura(Base):
        """
        Solicitudes de captura/modificación del empleado, pendientes de aprobación por RH.
        El payload_json guarda los datos solicitados; al aprobar se aplican a la tabla destino.
        """
        __tablename__ = 'solicitudes_captura'

        id = Column(Integer, primary_key=True, index=True)
        personal_id = Column(Integer, ForeignKey('personal.id'), nullable=False, index=True)
        seccion = Column(String(80), nullable=False, index=True)
        # Secciones: datos_personales, estudios, experiencia_laboral, reconocimientos, publicaciones
        accion = Column(String(20), nullable=False)  # modificar | agregar | eliminar
        tabla_destino = Column(String(80), nullable=False)
        # Tablas: personal, producciones, cursos_cap, estudios, experiencia_laboral, reconocimientos
        registro_ref_id = Column(Integer, nullable=True)  # ID del registro que se modifica/elimina (null si es agregar)
        payload_json = Column(Text, nullable=True)  # JSON con los datos solicitados
        estado = Column(String(20), default='pendiente', index=True)  # pendiente | aprobado | rechazado
        motivo_rechazo = Column(String(500), nullable=True)
        fecha_solicitud = Column(DateTime, default=datetime.now)
        solicitante_usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), nullable=True)
        fecha_revision = Column(DateTime, nullable=True)
        revisor_usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), nullable=True)

        # Relaciones (definir en tu Base si tienes Personal y UsuarioSistema)
        # personal = relationship("Personal", backref="solicitudes")
        # solicitante = relationship("UsuarioSistema", foreign_keys=[solicitante_usuario_id])
        # revisor = relationship("UsuarioSistema", foreign_keys=[revisor_usuario_id])

    return SolicitudCaptura


# Para integración directa en directorio.py, copiar esta clase después de CursoCapacitacion:
"""
class SolicitudCaptura(Base):
    __tablename__ = 'solicitudes_captura'
    id = Column(Integer, primary_key=True, index=True)
    personal_id = Column(Integer, ForeignKey('personal.id'), nullable=False, index=True)
    seccion = Column(String(80), nullable=False, index=True)
    accion = Column(String(20), nullable=False)  # modificar | agregar | eliminar
    tabla_destino = Column(String(80), nullable=False)
    registro_ref_id = Column(Integer, nullable=True)
    payload_json = Column(Text, nullable=True)
    estado = Column(String(20), default='pendiente', index=True)
    motivo_rechazo = Column(String(500), nullable=True)
    fecha_solicitud = Column(DateTime, default=datetime.now)
    solicitante_usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), nullable=True)
    fecha_revision = Column(DateTime, nullable=True)
    revisor_usuario_id = Column(Integer, ForeignKey('usuarios_sistema.id'), nullable=True)
"""
