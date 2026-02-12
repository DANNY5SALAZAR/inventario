# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy import inspect, text

# Configuración de la base de datos SQLite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'inventario.db')}"

# Crear motor de base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Crear todas las tablas en la base de datos y agregar migraciones"""
    Base.metadata.create_all(bind=engine)
    
    # Migración para agregar columnas faltantes
    inspector = inspect(engine)
    
    if 'movimientos' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('movimientos')]
        
        if 'cliente_destino' not in columns:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE movimientos ADD COLUMN cliente_destino VARCHAR'))
                conn.commit()
                print("✅ Columna cliente_destino agregada a movimientos")
        
        # 🆕 AGREGAR ESTAS MIGRACIONES
        if 'pdf_firmado' not in columns:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE movimientos ADD COLUMN pdf_firmado VARCHAR'))
                conn.commit()
                print("✅ Columna pdf_firmado agregada a movimientos")
        
        if 'pdf_nombre' not in columns:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE movimientos ADD COLUMN pdf_nombre VARCHAR'))
                conn.commit()
                print("✅ Columna pdf_nombre agregada a movimientos")
    
    print("✅ Base de datos inicializada correctamente")