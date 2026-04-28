import pytest
from src.processing.parser import DataParser 

@pytest.fixture
def parser_instance():
    # Asumiendo que el parser necesita una lista de estaciones permitidas
    estaciones = [{"id": "3195", "nombre": "Madrid-Retiro"}]
    return DataParser(estaciones_permitidas=estaciones)

def test_parser_datos_validos(parser_instance):
    """Prueba que el parser extrae correctamente los datos cuando el JSON es perfecto."""
    raw_data = [{
        "idema": "3195",
        "ta": "22.5",
        "hr": "45",
        "vv": "10.2",
        "fint": "2026-04-27T10:00:00"
    }]
    
    resultado = parser_instance.filtrar_y_limpiar(raw_data)
    
    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Madrid-Retiro"
    # Verifica el tipado que exigía el proyecto
    assert isinstance(resultado[0]["temperatura"], float)
    assert isinstance(resultado[0]["humedad"], int)

def test_parser_datos_corruptos(parser_instance):
    """
    DEMO DE RESILIENCIA: Prueba qué ocurre cuando la API devuelve datos incompletos
    o tipos incorrectos (ej. una letra donde debería ir un número).
    """
    datos_corruptos = [
        {
            "idema": "3195", 
            "ta": "ERROR_SENSOR", # Dato corrupto (string en vez de float)
            "hr": None,           # Dato faltante
            "vv": "10.2",
            "fint": "2026-04-27T10:00:00"
        },
        {
            "idema": "9999",      # Estación no registrada
            "ta": "20.0",
            "vv": "5.0"
        }
    ]
    
    # El parser debería ignorar o manejar el error sin romper la aplicación
    resultado = parser_instance.filtrar_y_limpiar(datos_corruptos)
    
    assert len(resultado) == 0