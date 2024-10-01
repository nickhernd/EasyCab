import socket
import re

HOST = 'localhost'
PORT = 8010

my_socket=socket.socket()
my_socket.bind((HOST, PORT))
my_socket.listen(5)

print ("Vroooom Vroooom, estoy escuchando en ", HOST, " ", PORT )
conexion, addr = my_socket.accept()

print ("Ojo! El sensor!")
print (addr)

pet=conexion.recv(4096)
procesar = pet.decode()  
if(pet.decode() == "s"):
    resultado = "semaforo"

if(pet.decode() == "p"):
    resultado = "peaton"

if(pet.decode() == "x"):
    resultado = "pinchazo"


print ("Recibido: ", resultado)
    
conexion.send("Posicion para el nano, cambio y corto".encode('utf-8'))
print ("Aparcao")
conexion.close()
