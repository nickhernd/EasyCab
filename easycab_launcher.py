import tkinter as tk
from tkinter import ttk
import json
import os
import logging

class EasyCabGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("EasyCab Control Panel")
        
        # Pestañas principales
        self.tab_control = ttk.Notebook(self.window)
        
        # Tab Central
        self.central_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.central_tab, text='Central')
        self.setup_central_tab()
        
        # Tab Taxi
        self.taxi_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.taxi_tab, text='Taxi')
        self.setup_taxi_tab()
        
        # Tab Cliente
        self.customer_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.customer_tab, text='Cliente')
        self.setup_customer_tab()
        
        self.tab_control.pack(expand=1, fill="both")
        
        # Área de logs común
        self.log_area = tk.Text(self.window, height=10)
        self.log_area.pack(fill="both", expand=True)
    
    def setup_central_tab(self):
        frame = ttk.LabelFrame(self.central_tab, text="Control Central")
        frame.grid(column=0, row=0, padx=10, pady=10)
        
        ttk.Button(frame, text="Iniciar Central", 
                  command=self.start_central).grid(column=0, row=0, padx=5, pady=5)
        ttk.Button(frame, text="Ver Mapa", 
                  command=self.show_map).grid(column=1, row=0, padx=5, pady=5)
        
        # Controles para taxis
        taxi_frame = ttk.LabelFrame(self.central_tab, text="Control Taxis")
        taxi_frame.grid(column=0, row=1, padx=10, pady=10)
        
        ttk.Label(taxi_frame, text="ID Taxi:").grid(column=0, row=0)
        self.taxi_id = ttk.Entry(taxi_frame, width=10)
        self.taxi_id.grid(column=1, row=0)
        
        ttk.Button(taxi_frame, text="Parar", 
                  command=lambda: self.control_taxi("stop")).grid(column=2, row=0)
        ttk.Button(taxi_frame, text="Reanudar", 
                  command=lambda: self.control_taxi("resume")).grid(column=3, row=0)
        ttk.Button(taxi_frame, text="A Base", 
                  command=lambda: self.control_taxi("base")).grid(column=4, row=0)

    def setup_taxi_tab(self):
        frame = ttk.LabelFrame(self.taxi_tab, text="Nuevo Taxi")
        frame.grid(column=0, row=0, padx=10, pady=10)
        
        ttk.Label(frame, text="ID:").grid(column=0, row=0)
        self.new_taxi_id = ttk.Entry(frame, width=10)
        self.new_taxi_id.grid(column=1, row=0)
        
        ttk.Button(frame, text="Iniciar Taxi", 
                  command=self.start_taxi).grid(column=2, row=0)
        ttk.Button(frame, text="Iniciar Sensor", 
                  command=self.start_sensor).grid(column=3, row=0)

    def setup_customer_tab(self):
        frame = ttk.LabelFrame(self.customer_tab, text="Nuevo Cliente")
        frame.grid(column=0, row=0, padx=10, pady=10)
        
        ttk.Label(frame, text="ID:").grid(column=0, row=0)
        self.customer_id = ttk.Entry(frame, width=10)
        self.customer_id.grid(column=1, row=0)
        
        ttk.Button(frame, text="Iniciar Cliente", 
                  command=self.start_customer).grid(column=2, row=0)

    def start_central(self):
        # Iniciar central
        pass

    def show_map(self):
        # Mostrar mapa actual
        pass

    def control_taxi(self, action):
        # Controlar taxi
        pass

    def start_taxi(self):
        # Iniciar nuevo taxi
        pass

    def start_sensor(self):
        # Iniciar sensor
        pass

    def start_customer(self):
        # Iniciar nuevo cliente
        pass

def main():
    app = EasyCabGUI()
    app.window.mainloop()

if __name__ == "__main__":
    main()