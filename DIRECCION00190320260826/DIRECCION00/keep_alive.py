import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def wake_up():
    print("--- Iniciando proceso de activación ---")
    
    # Configuración para que funcione en los servidores de GitHub (sin pantalla)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    try:
        # Instalación automática del driver de Chrome
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # --- REEMPLAZA ESTA URL CON LA DE TU APP DE STREAMLIT ---
        url = "https://itsedirectorio.streamlit.app/?Directorio_Itse=1" 
        
        print(f"Visitando: {url}")
        driver.get(url)
        
        # Esperamos 30 segundos para que Streamlit detecte la sesión y carguen los WebSockets
        time.sleep(30)
        
        print("Página cargada con éxito. App despertada.")
        driver.quit()
        print("--- Proceso finalizado ---")
        
    except Exception as e:
        print(f"ERROR: No se pudo activar la app. Detalle: {e}")

if __name__ == "__main__":
    wake_up()
