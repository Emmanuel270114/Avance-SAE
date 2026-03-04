from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import pyodbc
from backend.database.connection import get_db


def get_titulados(
    db: Session,
    unidad_academica: str,
    periodo: str,
    nivel: str,
    usuario: str,
    host: str
) -> List[Dict[str, Any]]:

    try:
        # Obtener la conexión pyodbc cruda desde SQLAlchemy
        connection = db.connection().connection

        cursor = connection.cursor()

        cursor.execute("""
            EXEC [dbo].[SP_Consulta_Titulados_Unidad_Academica]
                @UUnidad_Academica = ?,
                @Pperiodo          = ?,
                @NNivel            = ?,
                @UUsuario          = ?,
                @HHost             = ?
        """, (unidad_academica, periodo, nivel, usuario, host))

       
        rows = []
        while True:
            try:
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                if rows:
                    break
            except TypeError:
                
                pass

            if not cursor.nextset():
                break

        cursor.close()
        return rows

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Error al ejecutar SP_Consulta_Titulados_Unidad_Academica: {e}")
    
if __name__ == "__main__":
    with next(get_db()) as db:
        resultado = get_titulados(
            db=db,
            unidad_academica='ENBA',
            periodo='2025-2026/2',
            nivel='Superior',
            usuario='eesquivelo1300',
            host='Test'
        )
        print(resultado)