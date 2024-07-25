CREATE TABLE ventas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipo VARCHAR(255) NOT NULL,
    color VARCHAR(255) NOT NULL,
    material VARCHAR(255) NOT NULL,
    agregado VARCHAR(255) NOT NULL,
    cantidad INT NOT NULL,
    precioU DECIMAL(10, 2) NOT NULL,
    precioT DECIMAL(10, 2) NOT NULL,
    fecha DATE NOT NULL
);

CREATE TABLE usuario (
    ROL INT PRIMARY KEY,
    TIPO VARCHAR(50)
);

CREATE TABLE persona (
    id INT AUTO_INCREMENT PRIMARY KEY, 
    nombre VARCHAR(100),                
    apellido VARCHAR(100),          
    ci INT,  
    genero VARCHAR(10),
    email VARCHAR(100),               
    telefono VARCHAR(15),               
    direccion VARCHAR(255),            
    fecha_nacimiento DATE,             
    rol INT,                           
    FOREIGN KEY (rol) REFERENCES usuario(ROL) 
);

CREATE TABLE stock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipo VARCHAR(100),
    color VARCHAR(50),
    material VARCHAR(50),
    agregado VARCHAR(100),
    cantidad INT
);
