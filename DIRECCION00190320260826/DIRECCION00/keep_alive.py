from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def wake_up():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Sin ventana gráfica
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # REEMPLAZA CON TU URL REAL
    url = "https://itsedirectorio.streamlit.app/?Directorio_Itse=1" 
    
    print(f"Visitando {url}...")
    driver.get(url)
    
    # Esperamos 15 segundos para que carguen los WebSockets
    time.sleep(15) 
    
    print("App activada correctamente.")
    driver.quit()

if __name__ == "__main__":
    wake_up()
